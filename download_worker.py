import time
import yt_dlp
import random
import DBConnector
import sqlite3
import os
import helper

conn = sqlite3.connect('data/audio_files.db')

cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS queued_for_download (youtube_url TEXT, task_id TEXT)')
conn.commit()

while True:
    cursor.execute('SELECT * FROM queued_for_download')
    urls_to_download = cursor.fetchall()
    if len(urls_to_download) == 0:
        time.sleep(1)
        continue

    for url, task_id in urls_to_download:
        segment_id = url.split('=')[1]
        if os.path.exists(f"static/audio/{segment_id}.mp3"):
            print(f"File {segment_id}.mp3 already exists")

            cursor.execute('DELETE FROM queued_for_download WHERE task_id = ?', (task_id,))
            conn.commit()
            continue

        audio_file, info = helper.download_song(url)

        cursor.execute('DELETE FROM queued_for_download WHERE task_id = ?', (task_id,))
        conn.commit()

        # save progress to db
        DBConnector.insert_into_audio_files(info['fulltitle'], audio_file, url)

        time.sleep(random.randint(1, 5))
