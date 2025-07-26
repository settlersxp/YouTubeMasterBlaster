import sqlite3

DB_NAME = 'audio_files.db'
AUDIO_FILES_TABLE = 'audio_files'
VIDEO_FILES_TABLE = 'video_files'
QUEUED_FOR_DOWNLOAD_TABLE = 'queued_for_download'

# a "singleton" like file with a few methods that allow the other scripts to use the sqlite3 DB
conn = None
def new_conn():
    global conn
    conn = sqlite3.connect(f'data/{DB_NAME}')


def get_conn():
    global conn
    try:
        # check if the connection is open
        conn.cursor()
    except Exception:
        new_conn()
    return conn


def close_conn():
    global conn
    conn.close()


def get_audio_files():
    global conn
    get_conn()
    cursor = conn.cursor()

    cursor.execute(f'SELECT * FROM {AUDIO_FILES_TABLE}')
    return cursor.fetchall()


def get_from_audio_files_by_task_id(task_id):
    get_conn()
    global conn
    cursor = conn.cursor()

    cursor.execute(f'SELECT * FROM {AUDIO_FILES_TABLE} WHERE task_id = ?', (task_id,))
    return cursor.fetchone()

def insert_into_video_files(name, file_path, youtube_url):
    get_conn()
    global conn
    cursor = conn.cursor()
    cursor.execute(f'INSERT INTO {VIDEO_FILES_TABLE} (name, file_path, youtube_url) VALUES (?, ?, ?)', (name, file_path, youtube_url))
    conn.commit()

def insert_into_audio_files(name, file_path, youtube_url):
    get_conn()
    global conn
    cursor = conn.cursor()
    cursor.execute(f'INSERT INTO {AUDIO_FILES_TABLE} (name, file_path, youtube_url) VALUES (?, ?, ?)', (name, file_path, youtube_url))
    conn.commit()


def insert_into_queue_with_priority(url, is_video=0):
    global conn
    get_conn()
    cursor = conn.cursor()

    # get the smallest task_id
    cursor.execute('SELECT MIN(task_id) FROM queued_for_download')
    smallest_task_id = cursor.fetchone()[0]
    if smallest_task_id is None:
        smallest_task_id = 0
    cursor.execute('INSERT INTO queued_for_download (youtube_url, task_id, is_video) VALUES (?, ?, ?)', (url, smallest_task_id - 1, is_video))
    conn.commit()

def insert_into_queue_for_download(url, task_id, is_video=0):
    global conn
    get_conn()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO queued_for_download (youtube_url, task_id, is_video) VALUES (?, ?, ?)', (url, task_id, is_video))
    conn.commit()


def get_from_queue_for_download_by_task_id(task_id):
    global conn
    get_conn()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM queued_for_download WHERE task_id = ? ORDER BY task_id ASC', (task_id,))
    audio_file = cursor.fetchone()
    return audio_file

def get_next_song_in_download_queue():
    global conn
    get_conn()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM queued_for_download LIMIT 1 ORDER BY task_id ASC')
    return cursor.fetchone()

def delete_from_queue_for_download_by_id(task_id):
    global conn
    get_conn()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM queued_for_download WHERE task_id = ?', (task_id,))
    conn.commit()

def get_queue_count():
    global conn
    get_conn()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM queued_for_download')
    return cursor.fetchone()[0]