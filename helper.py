import yt_dlp

ydl_opts = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'outtmpl': f'static/audio/%(id)s.%(ext)s',
    'nocheckcertificate': True,
    'quiet': False,
    'no_warnings': False
}

def download_song(url):
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        audio_file = f"static/audio/{info['id']}.mp3"
    return audio_file, info