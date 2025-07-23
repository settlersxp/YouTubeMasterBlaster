# migrate audio files /data/audio_files.json to sqlite db

import sqlite3
import json

conn = sqlite3.connect('data/audio_files.db')

with open('data/audio_files.json', 'r') as f:
    audio_files = json.load(f)

conn.execute('DROP TABLE IF EXISTS audio_files')
conn.execute('CREATE TABLE audio_files (name TEXT, file_path TEXT, youtube_url TEXT)')
for audio in audio_files:
    conn.execute('INSERT INTO audio_files (name, file_path, youtube_url) VALUES (?, ?, ?)', (audio['name'], audio['file_path'], audio['youtube_url']))

conn.commit()
conn.close()