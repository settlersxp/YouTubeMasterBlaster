import yt_dlp

cookies_path = None
video_path = "static/video"
audio_path = "static/audio"
general_ydl_opts = {
    'cookiefile': cookies_path,
    'nocheckcertificate': True,
    'quiet': False,
    'no_warnings': False,
    'max_sleep_interval':30,
    'sleep_interval':10,
    'sleep_interval_requests':5,
}

ydl_opts_song = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'outtmpl': f'{audio_path}/%(id)s.%(ext)s',
    **general_ydl_opts
}

ydl_opts_video = {
    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
    'outtmpl': f'{video_path}/%(id)s.%(ext)s',
    **general_ydl_opts
}

def download_song(url):
    with yt_dlp.YoutubeDL(ydl_opts_song) as ydl:
        info = ydl.extract_info(url, download=True)
        audio_file = f"static/audio/{info['id']}.mp3"
    return audio_file, info

def download_video(url):
    with yt_dlp.YoutubeDL(ydl_opts_video) as ydl:
        info = ydl.extract_info(url, download=True)
        audio_file = f"static/video/{info['id']}.mp4"
    return audio_file, info