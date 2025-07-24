from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import yt_dlp
from pathlib import Path
from typing import List
from urllib.parse import parse_qs, urlparse
import time
import DBConnector
import os

app = FastAPI()

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Create necessary directories
Path("data").mkdir(exist_ok=True)
Path("static/audio").mkdir(parents=True, exist_ok=True)

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

@app.get("/playlist")
async def playlist_page(request: Request):
    audio_files = DBConnector.get_audio_files()

    return templates.TemplateResponse("playlist.html", {
        "request": request,
        "audio_files": audio_files
    })

@app.post("/download")
async def download_audio(request: Request, name: str = Form(...), url: str = Form(...)):
    try:
        task_id = str(time.time())
        DBConnector.insert_into_queue_for_download(url, task_id)
        
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
@app.get("/next-song-in-download-queue")
async def next_song_in_download_queue():
    next_song = DBConnector.get_next_song_in_download_queue()
    if next_song:
        if os.path.exists(f"static/audio/{next_song[0]}.mp3"):
            print(f"File {next_song[0]}.mp3 already exists")
            DBConnector.delete_from_queue_for_download_by_id(next_song[0])
            return JSONResponse({"status": "no_song"})
        else:
            return JSONResponse({
                "status": "success",
                "song": next_song
            })
    else:
        return JSONResponse({
            "status": "no_song"
        })

@app.delete("/delete-song-from-download-queue/{task_id}")
async def delete_song_from_download_queue(task_id: str):
    DBConnector.delete_from_queue_for_download_by_id(task_id)
    return JSONResponse({
        "status": "success"
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
    DBConnector.insert_into_audio_files(song_title, path, song_url)
    return JSONResponse({
        "status": "success"
    })