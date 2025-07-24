# migrate audio files /data/audio_files.json to sqlite db

import sqlite3
import json
import os

conn = sqlite3.connect('data/audio_files.db')

# if audio_files.json exists, open it
if os.path.exists('data/audio_files.json'):
    with open('data/audio_files.json', 'r') as f:
        audio_files = json.load(f)
else:
    audio_files = []

conn.execute('DROP TABLE IF EXISTS audio_files')
conn.execute('CREATE TABLE audio_files (name TEXT, file_path TEXT, youtube_url TEXT)')
for audio in audio_files:
    conn.execute('INSERT INTO audio_files (name, file_path, youtube_url) VALUES (?, ?, ?)', (audio['name'], audio['file_path'], audio['youtube_url']))

# create table queued_for_download
conn.execute('DROP TABLE IF EXISTS queued_for_download')
conn.execute('CREATE TABLE queued_for_download (youtube_url TEXT, task_id TEXT)')

conn.commit()
conn.close()