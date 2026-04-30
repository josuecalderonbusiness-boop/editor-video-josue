FROM python:3.11-slim

RUN apt-get update && apt-get install -y ffmpeg gcc python3-dev && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install "moviepy>=2.0.0" numpy pillow flask openai python-dotenv google-auth google-auth-oauthlib google-api-python-client

COPY . .

EXPOSE 5000
CMD gunicorn app:app --bind 0.0.0.0:$PORT --timeout 600 --workers 1
