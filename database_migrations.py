# migrate audio files /data/audio_files.json to sqlite db

import sqlite3
import json
import os

conn = sqlite3.connect('data/audio_files.db')

def setup_table(table_name, new_columns):
    # sometimes col[2] is not present, so we need to add it
    for col in new_columns:
        if len(col) == 3:
            continue

        new_col = (col[0], col[1], 'NULL')
        new_columns[new_columns.index(col)] = new_col

    if not conn.execute('SELECT name FROM sqlite_master WHERE type="table" AND name="' + table_name + '"').fetchone():
        conn.execute('CREATE TABLE ' + table_name + ' ('+', '.join([f"{col[0]} {col[1]} {col[2]}" for col in new_columns])+')')
    else:
        # get the columns of the table
        existing_columns = conn.execute('PRAGMA table_info(' + table_name + ')').fetchall()
        existing_columns = [col[1] for col in existing_columns]
        # check if all columns are present
        for col in new_columns:
            # add the column if it is not present
            if col[0] not in existing_columns:
                conn.execute('ALTER TABLE ' + table_name + ' ADD COLUMN ' + col[0] + ' ' + col[1] + ' DEFAULT ' + str(col[2]))
        # remove the columns that are not present in the new columns
        for col in existing_columns:
            if col not in [col[0] for col in new_columns]:
                conn.execute('ALTER TABLE ' + table_name + ' DROP COLUMN ' + col)


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
    ('youtube_url', 'TEXT')
]
setup_table('audio_files', all_columns)

for audio in audio_files:
    conn.execute('INSERT INTO audio_files (name, file_path, youtube_url) VALUES (?, ?, ?)', (audio['name'], audio['file_path'], audio['youtube_url']))


all_columns = [
    ('youtube_url', 'TEXT'),
    ('task_id', 'TEXT'),
    ('is_video', 'INTEGER', 0)
]
setup_table('queued_for_download', all_columns)

all_columns = [
    ('name', 'TEXT'),
    ('file_path', 'TEXT'),
    ('youtube_url', 'TEXT')
]
setup_table('video_files', all_columns)

conn.commit()
conn.close()