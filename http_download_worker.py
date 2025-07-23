import requests
import time
import helper
import random
import os

def main():
    server_url = os.getenv("SERVER_URL", "http://127.0.0.1:5000")
    print(f"Pinging server: {server_url}")
    ping = requests.get(f"{server_url}/ping")
    if ping.status_code != 200:
        print(f"Server is not responding: {ping.status_code}")
        return
    print(f"Server is responding: {ping.status_code}")

    print("Check if app/cookies exists")
    if not os.path.exists("/app/cookies"):
        print("app/cookies does not exist")
        return
    print("app/cookies exists")

    print("Writing test file to output folder")
    with open("static/audio/test.txt", "w") as f:
        f.write("Test file")
    print("Test file written")

    while True:
        song = requests.get(f"{server_url}/next-song-in-download-queue")
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

        db_update = requests.post(f"{server_url}/move-song-to-audio-files", json={"info": info, "path": audio_file})
        if db_update.status_code == 200:
            print(f"Song {info['title']} moved to audio files")
            deleted_successfully = requests.delete(f"{server_url}/delete-song-from-download-queue/{task_id}")
            if deleted_successfully.status_code == 200:
                print(f"Song {info['title']} deleted from download queue")
            else:
                print(f"Song {info['title']} not deleted from download queue")
        else:
            print(f"Song {info['title']} not moved to audio files")
        time.sleep(random.randint(1, 5))


if __name__ == "__main__":
    main()