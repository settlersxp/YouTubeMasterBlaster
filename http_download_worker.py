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

    helper.cookies_path = "/app/cookies"
    print(f"Check if {helper.cookies_path} exists")
    if not os.path.exists(helper.cookies_path):
        print(f"{helper.cookies_path} does not exist")
        return
    print(f"{helper.cookies_path} exists")

    print("Writing test file to output folder")
    with open("static/audio/test.txt", "w") as f:
        f.write("Test file")
    print("Test file written")

    while True:
        song = requests.get(f"{server_url}/next-task-in-download-queue")
        if song.status_code == 200 and song.json()["status"] == "no_task":
            time.sleep(10)
            continue

        if song.status_code != 200:
            print(f"Error getting next song: {song.status_code}")
            time.sleep(10)
            continue

        task_id = song.json()["task"][0]
        url = song.json()["task"][1]
        is_video = song.json()["task"][2]
        try:
            if is_video:
                created_file, info = helper.download_video(url)
            else:
                created_file, info = helper.download_song(url)
        except Exception as e:
            if "Video unavailable" in str(e):
                print(f"Video unavailable: {e}")
                deleted_successfully = requests.delete(f"{server_url}/delete-task-from-download-queue/{task_id}")
                if deleted_successfully.status_code == 200:
                    print(f"Song {url} deleted from download queue")
                else:
                    print(f"Song {url} not deleted from download queue")
                time.sleep(10)
                continue
            else:
                print(f"Error downloading song: {e}")
                time.sleep(10)
                continue
        
        info.pop("formats")
        info.pop("thumbnails")
        info.pop("requested_downloads")
        info.pop("http_headers")

        db_update = requests.post(f"{server_url}/move-task-to-files", json={"info": info, "path": created_file, "is_video": is_video})
        if db_update.status_code == 200:
            print(f"Clip {info['title']} moved to files")
            deleted_successfully = requests.delete(f"{server_url}/delete-task-from-download-queue/{task_id}")
            if deleted_successfully.status_code == 200:
                print(f"Clip {info['title']} deleted from download queue")
            else:
                print(f"Song {info['title']} not deleted from download queue")
        else:
            print(f"Song {info['title']} not moved to audio files")
        time.sleep(random.randint(1, 5))


if __name__ == "__main__":
    main()