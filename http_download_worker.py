import requests
import time
import helper
import random
import json

def main():
    while True:
        song = requests.get("http://127.0.0.1:5000/next-song-in-download-queue")
        url = song.json()["song"][0]
        task_id = song.json()["song"][1]
        try:
            audio_file, info = helper.download_song(url)
        except Exception as e:
            print(e)
            time.sleep(10)
            continue
        
        info.pop("formats")
        info.pop("thumbnails")
        info.pop("requested_downloads")
        info.pop("http_headers")

        db_update = requests.post(f"http://127.0.0.1:5000/move-song-to-audio-files", json={"info": info, "path": audio_file})
        if db_update.status_code == 200:
            print(f"Song {info['title']} moved to audio files")
            deleted_successfully = requests.delete(f"http://127.0.0.1:5000/delete-song-from-download-queue/{task_id}")
            if deleted_successfully.status_code == 200:
                print(f"Song {info['title']} deleted from download queue")
            else:
                print(f"Song {info['title']} not deleted from download queue")
        else:
            print(f"Song {info['title']} not moved to audio files")
        time.sleep(random.randint(1, 5))


if __name__ == "__main__":
    main()