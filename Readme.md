# Development setup:

## Create the virtual environment
`python3 -m venv venv`

## Activate the virtual environment
`source venv/bin/activate`

## Install the required packages
`pip install -r requirements.txt`

## Run the http download worker:
`python http_download_worker.py`

## Run the server:
`uvicorn main:app --host 0.0.0.0 --port 5003 --reload`


# Running the server:
The application is composed of two parts:
- The server: `main.py`
- The download worker: `http_download_worker.py`

The server is a FastAPI application that runs on port 5000.
The download worker is a Python script that runs in a Docker container and downloads songs from the server. The download worker will ask the server for the next song to download and then download it.

NOTE: If the server is running on a Mac you will need to disable the IP tracking else the incoming connections on the host will be blocked.

## Main server:
`uvicorn main:app --host 0.0.0.0 --port 5003 --reload`

## Running the download worker:
`docker build -t youtube-master-base:latest -f Dockerfile.base .` to install ffmpeg and curl on top of python 3.10 slim whenever OS things need updated.

`docker build -t http_download_worker -f Dockerfile.http_download_worker .` to build the download worker application.

`docker run -e SERVER_URL="http://127.0.0.1:5003" --volume /Users/XXXXXXX/Library/Application\ Support/Google/Chrome/Default/Cookies:/app/cookies --volume ./static/audio:/static/audio http_download_worker`

Once you find some settings that work for you, you can save them in the `settings.personal` file.