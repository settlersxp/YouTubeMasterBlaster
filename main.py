from fastapi import FastAPI, Request, Form, WebSocket, WebSocketDisconnect, Query, Response
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, StreamingResponse
import yt_dlp
from pathlib import Path
from typing import List, Dict, Any
from urllib.parse import parse_qs, urlparse
import time
import DBConnector
import os
import json
from starlette.websockets import WebSocketState
import aiohttp
import asyncio

app = FastAPI()

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/static/video", StaticFiles(directory="static/video"), name="video")
app.mount("/static/audio", StaticFiles(directory="static/audio"), name="audio")
templates = Jinja2Templates(directory="templates")

# Create necessary directories
Path("data").mkdir(exist_ok=True)
Path("static/audio").mkdir(parents=True, exist_ok=True)
Path("static/video").mkdir(parents=True, exist_ok=True)

# WebSocket connection manager for video synchronization
class ConnectionManager:
    def __init__(self):
        # Dictionary to store active connections by room
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # Dictionary to store video state by room
        self.room_states: Dict[str, Dict[str, Any]] = {}
        
    async def connect(self, websocket: WebSocket, room: str, username: str):
        await websocket.accept()
        if room not in self.active_connections:
            self.active_connections[room] = []
            self.room_states[room] = {
                "currentTime": 0,
                "isPlaying": False,
                "lastUpdate": time.time()
            }
        
        # Store username in websocket object
        websocket.username = username
        self.active_connections[room].append(websocket)
        
        # Send current state to new user
        await websocket.send_json({
            "type": "sync",
            "data": self.room_states[room]
        })
        
        # Notify other users about new user
        await self.broadcast_to_room(room, {
            "type": "user_joined",
            "username": username
        }, websocket)
    
    def disconnect(self, websocket: WebSocket, room: str):
        if room in self.active_connections:
            if websocket in self.active_connections[room]:
                username = getattr(websocket, "username", "Anonymous")
                self.active_connections[room].remove(websocket)
                
                # Clean up room if empty
                if not self.active_connections[room]:
                    del self.active_connections[room]
                    if room in self.room_states:
                        del self.room_states[room]
                
                # We can't broadcast here because it's not an async function
                # and we can't await. The disconnect is handled in the websocket endpoint.
                return username
        return None
    
    async def broadcast_to_room(self, room: str, message: dict, exclude_websocket: WebSocket = None):
        if room in self.active_connections:
            for connection in self.active_connections[room]:
                if connection != exclude_websocket and connection.client_state != WebSocketState.DISCONNECTED:
                    try:
                        await connection.send_json(message)
                    except RuntimeError:
                        # Connection might be closing
                        pass
    
    def update_room_state(self, room: str, state_update: dict):
        if room in self.room_states:
            self.room_states[room].update(state_update)
            self.room_states[room]["lastUpdate"] = time.time()
    
    def get_users_in_room(self, room: str) -> List[str]:
        if room not in self.active_connections:
            return []
        
        return [getattr(conn, "username", "Anonymous") for conn in self.active_connections[room]]

# Initialize connection manager
manager = ConnectionManager()

# Playlist WebSocket connection manager
class PlaylistManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.last_audio_files_count = 0
        self.check_interval = 2.0  # Check for updates every 2 seconds
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        
        # Send initial playlist data
        audio_files = DBConnector.get_audio_files()
        self.last_audio_files_count = len(audio_files)
        await websocket.send_json({
            "type": "playlist_update",
            "audio_files": audio_files
        })
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections.copy():
            try:
                await connection.send_json(message)
            except Exception:
                # Connection might be closed
                if connection in self.active_connections:
                    self.active_connections.remove(connection)
    
    async def check_for_updates(self):
        while True:
            try:
                audio_files = DBConnector.get_audio_files()
                current_count = len(audio_files)
                
                # If count changed, broadcast update
                if current_count != self.last_audio_files_count:
                    self.last_audio_files_count = current_count
                    await self.broadcast({
                        "type": "playlist_update",
                        "audio_files": audio_files
                    })
            except Exception as e:
                print(f"Error checking for playlist updates: {e}")
            
            await asyncio.sleep(self.check_interval)

# Initialize playlist manager
playlist_manager = PlaylistManager()

def is_playlist_url(url: str) -> bool:
    """Check if the URL is a YouTube playlist."""
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    return 'list' in query_params

def extract_playlist_videos(playlist_url: str) -> List[dict]:
    """Extract all video information from a playlist."""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'nocheckcertificate': True
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(playlist_url, download=False)
        if 'entries' in result:
            return [
                {
                    'url': f"https://www.youtube.com/watch?v={entry['id']}",
                    'title': entry['title']
                }
                for entry in result['entries']
                if entry.get('id') and entry.get('title')
            ]
    return []

def get_video_info(video_id: str) -> dict:
    """Get video information from local file."""
    video_path = f"static/video/{video_id}.mp4"
    
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file {video_id}.mp4 not found in static/video directory")
    
    # Get basic file information
    file_stats = os.stat(video_path)
    
    # Get video title from filename or use video_id as fallback
    title = os.path.splitext(os.path.basename(video_path))[0]
    if title == video_id:
        title = f"Video {video_id}"
    
    return {
        'title': title,
        'file_path': video_path,
        'size': file_stats.st_size,
        'video_url': f"/static/video/{video_id}.mp4"
    }

@app.get("/ping")
async def ping():
    return JSONResponse({
        "status": "pong"
    })

@app.get("/download")
async def download_page(request: Request, message: str = None, status: str = None):
    queue_count = DBConnector.get_queue_count()
    return templates.TemplateResponse("download.html", {
        "request": request, 
        "queue_count": queue_count,
        "message": message,
        "status": status
    })

@app.get("/")
async def home_page(request: Request):
    audio_files = DBConnector.get_audio_files()

    return templates.TemplateResponse("playlist.html", {
        "request": request,
        "audio_files": audio_files
    })

@app.get("/playlist")
async def playlist_page(request: Request):
    audio_files = DBConnector.get_audio_files()

    return templates.TemplateResponse("playlist.html", {
        "request": request,
        "audio_files": audio_files
    })

@app.get("/videos")
async def videos_page(request: Request):
    # List all videos in the video directory
    video_files = []
    video_dir = Path("static/video")
    
    if video_dir.exists():
        for file in video_dir.glob("*.mp4"):
            video_id = file.stem
            video_files.append({
                "id": video_id,
                "title": video_id,
                "url": f"/watch/{video_id}"
            })
    
    return templates.TemplateResponse("videos.html", {
        "request": request,
        "videos": video_files
    })

@app.get("/watch/{video_id}")
async def watch_video(request: Request, video_id: str):
    try:
        video_info = get_video_info(video_id)
        return templates.TemplateResponse("video_player.html", {
            "request": request,
            "video_id": video_id,
            "video_title": video_info.get('title', 'Video Player'),
            "stream_url": video_info.get('video_url')
        })
    except FileNotFoundError as e:
        return templates.TemplateResponse("video_player.html", {
            "request": request,
            "video_id": video_id,
            "video_title": "Video Not Found",
            "error": str(e)
        })
    except Exception as e:
        return templates.TemplateResponse("video_player.html", {
            "request": request,
            "video_id": video_id,
            "video_title": "Error",
            "error": str(e)
        })

@app.get("/video_info/{video_id}")
async def get_video_stream_info(video_id: str):
    try:
        video_info = get_video_info(video_id)
        
        return JSONResponse({
            "status": "success",
            "video_url": video_info.get('video_url'),
            "title": video_info.get('title')
        })
    except Exception as e:
        return JSONResponse({
            "status": "error",
            "message": str(e)
        }, status_code=500)

@app.websocket("/ws/{video_id}")
async def websocket_endpoint(websocket: WebSocket, video_id: str, username: str = Query("Anonymous")):
    await manager.connect(websocket, video_id, username)
    
    try:
        # Send current users list to the new user
        await websocket.send_json({
            "type": "users_list",
            "users": manager.get_users_in_room(video_id)
        })
        
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "sync":
                # Update room state with new video position/status
                manager.update_room_state(video_id, message["data"])
                # Broadcast to all users in the room
                await manager.broadcast_to_room(video_id, {
                    "type": "sync",
                    "data": manager.room_states[video_id],
                    "from": websocket.username
                }, exclude_websocket=websocket)
            
            elif message["type"] == "chat":
                # Broadcast chat message to all users in the room
                await manager.broadcast_to_room(video_id, {
                    "type": "chat",
                    "username": websocket.username,
                    "message": message["message"],
                    "timestamp": time.time()
                })
            
            elif message["type"] == "username_change":
                old_username = websocket.username
                websocket.username = message["username"]
                # Broadcast username change to all users
                await manager.broadcast_to_room(video_id, {
                    "type": "username_change",
                    "old_username": old_username,
                    "new_username": websocket.username
                })
                
                # Send updated users list
                await manager.broadcast_to_room(video_id, {
                    "type": "users_list",
                    "users": manager.get_users_in_room(video_id)
                })
                
    except WebSocketDisconnect:
        username = manager.disconnect(websocket, video_id)
        if username:
            # Notify remaining users about the disconnection
            await manager.broadcast_to_room(video_id, {
                "type": "user_left",
                "username": username
            })
            
            # Send updated users list
            await manager.broadcast_to_room(video_id, {
                "type": "users_list",
                "users": manager.get_users_in_room(video_id)
            })

@app.websocket("/ws/playlist")
async def playlist_websocket_endpoint(websocket: WebSocket):
    await playlist_manager.connect(websocket)
    
    try:
        while True:
            # Just keep the connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        playlist_manager.disconnect(websocket)

@app.post("/download_video")
async def download_video(request: Request, name: str = Form(...), url: str = Form(...)):
    try:
        DBConnector.insert_into_queue_with_priority(url, is_video=1)
        
        queue_count = DBConnector.get_queue_count()
        return templates.TemplateResponse("download.html", {
            "request": request,
            "queue_count": queue_count,
            "message": f"Video '{name}' added to download queue",
            "status": "success"
        })
    except Exception as e:
        queue_count = DBConnector.get_queue_count()
        return templates.TemplateResponse("download.html", {
            "request": request,
            "queue_count": queue_count,
            "message": f"Error: {str(e)}",
            "status": "error"
        })

@app.post("/process-playlist")
async def process_playlist(request: Request, url: str = Form(...)):
    try:
        if not is_playlist_url(url):
            queue_count = DBConnector.get_queue_count()
            return templates.TemplateResponse("download.html", {
                "request": request,
                "queue_count": queue_count,
                "message": "Not a valid YouTube playlist URL",
                "status": "error"
            })
        
        songs = extract_playlist_videos(url)
        audio_files = DBConnector.get_audio_files()

        # Filter out songs that are already downloaded
        filtered_songs = []
        for song in songs:
            is_already_downloaded = False
            for audio in audio_files:
                if audio[2] == song["url"]:
                    is_already_downloaded = True
                    break
            if not is_already_downloaded:
                filtered_songs.append(song)
    
        # Queue the remaining videos
        for song in filtered_songs:
            task_id = str(time.time())
            DBConnector.insert_into_queue_for_download(song["url"], task_id)
            time.sleep(0.01)  # Small delay to ensure unique task_ids

        queue_count = DBConnector.get_queue_count()
        return templates.TemplateResponse("download.html", {
            "request": request,
            "queue_count": queue_count,
            "message": f"Added {len(filtered_songs)} videos from playlist to download queue",
            "status": "success"
        })
    except Exception as e:
        queue_count = DBConnector.get_queue_count()
        return templates.TemplateResponse("download.html", {
            "request": request,
            "queue_count": queue_count,
            "message": f"Error: {str(e)}",
            "status": "error"
        })

# Worker endpoints - these are needed for the download worker
@app.get("/next-task-in-download-queue")
async def next_task_in_download_queue():
    next_task = DBConnector.get_next_task_in_download_queue()
    if next_task:
        if os.path.exists(f"static/audio/{next_task[0]}.mp3"):
            print(f"File {next_task[0]}.mp3 already exists")
            DBConnector.delete_from_queue_for_download_by_id(next_task[0])
            return JSONResponse({"status": "no_task"})
        else:
            return JSONResponse({
                "status": "success",
                "task": next_task
            })
    else:
        return JSONResponse({
            "status": "no_task"
        })

@app.delete("/delete-song-from-download-queue/{task_id}")
async def delete_song_from_download_queue(task_id: str):
    DBConnector.delete_from_queue_for_download_by_id(task_id)
    return JSONResponse({
        "status": "success"
    })

@app.get("/playlist-as-json")
async def playlist_as_json():
    audio_files = DBConnector.get_audio_files()
    return JSONResponse({
        "status": "success",
        "audio_files": audio_files
    })

@app.post("/move-song-to-audio-files")
async def move_song_to_audio_files(request: Request):
    request_body = await request.json()
    path = request_body["path"]
    if 'artist' not in request_body["info"] or 'title' not in request_body["info"]:
        song_title = request_body["info"]["title"]
    else:
        song_title = request_body["info"]["artist"]+" - "+request_body["info"]["title"]
    song_title = song_title.encode('utf-8').decode('utf-8')
    song_url = request_body["info"]["original_url"]
    
    # Insert into database
    DBConnector.insert_into_audio_files(song_title, path, song_url)
    
    # Notify all connected clients about the update
    audio_files = DBConnector.get_audio_files()
    asyncio.create_task(playlist_manager.broadcast({
        "type": "playlist_update",
        "audio_files": audio_files
    }))
    
    return JSONResponse({
        "status": "success"
    })

# Start the background task for checking playlist updates
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(playlist_manager.check_for_updates())