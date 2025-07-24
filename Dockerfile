FROM http_download_worker

WORKDIR /app

# Create necessary directories
RUN mkdir -p static/audio
RUN mkdir -p templates

# Declare volume for audio files
VOLUME /app/static/audio

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5003", "--reload"]