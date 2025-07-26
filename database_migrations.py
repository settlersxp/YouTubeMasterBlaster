# migrate audio files /data/audio_files.json to sqlite db

import sqlite3
import json
import os

conn = sqlite3.connect('data/audio_files.db')

def setup_table(table_name, columns):
    if not conn.execute('SELECT name FROM sqlite_master WHERE type="table" AND name="' + table_name + '"').fetchone():
        conn.execute('CREATE TABLE ' + table_name + ' ('+', '.join([f"{col[0]} {col[1]} {col[2]}" for col in columns])+')')
    else:
        # get the columns of the table
        columns = conn.execute('PRAGMA table_info(' + table_name + ')').fetchall()
        columns = [col[1] for col in columns]
        # check if all columns are present
        for col in columns:
            if col not in [col[0] for col in all_columns]:
                if len(col) == 2:
                    col = (col[0], col[1], 'NULL')
                conn.execute('ALTER TABLE ' + table_name + ' ADD COLUMN ' + col[0] + ' ' + col[1] + ' ' + col[2])


# if audio_files.json exists, open it
if os.path.exists('data/audio_files.json'):
    with open('data/audio_files.json', 'r') as f:
        audio_files = json.load(f)
else:
    audio_files = []

# The structure of each column is: name, data type, default value
all_columns = [
    ('name', 'TEXT'),
    ('file_path', 'TEXT'),
    ('youtube_url', 'TEXT'),
    ('is_video', 'INTEGER', 0)
]
setup_table('audio_files', all_columns)

for audio in audio_files:
    conn.execute('INSERT INTO audio_files (name, file_path, youtube_url, is_video) VALUES (?, ?, ?, ?)', (audio['name'], audio['file_path'], audio['youtube_url'], audio['is_video']))


all_columns = [
    ('youtube_url', 'TEXT'),
    ('task_id', 'TEXT'),
    ('is_video', 'INTEGER', 0)
]
setup_table('queued_for_download', all_columns)

all_columns = [
    ('name', 'TEXT'),
    ('file_path', 'TEXT'),
    ('youtube_url', 'TEXT'),
    ('is_video', 'INTEGER', 0)
]
setup_table('video_files', all_columns)

conn.commit()
conn.close()