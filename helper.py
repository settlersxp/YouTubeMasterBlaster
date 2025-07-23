import yt_dlp
import os

cookies_path = os.getenv("COOKIES_PATH", None)

ydl_opts = {
    'cookiefile': cookies_path,
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'outtmpl': f'static/audio/%(id)s.%(ext)s',
    'nocheckcertificate': True,
    'quiet': False,
    'no_warnings': False,
    'max_sleep_interval':30,
    'sleep_interval':10,
    'sleep_interval_requests':5,
}

def download_song(url):
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        audio_file = f"static/audio/{info['id']}.mp3"
    return audio_file, info