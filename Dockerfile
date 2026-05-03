FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    ffmpeg gcc python3-dev \
    nodejs npm \
    chromium \
    fonts-liberation libatk-bridge2.0-0 libatk1.0-0 \
    libcups2 libdbus-1-3 libgdk-pixbuf-xlib-2.0-0 libnspr4 \
    libnss3 libx11-xcb1 libxcomposite1 libxdamage1 \
    libxrandr2 libxss1 libxtst6 xdg-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install "moviepy>=2.0.0" numpy pillow flask openai python-dotenv google-auth google-auth-oauthlib google-api-python-client

COPY package*.json ./
RUN npm install puppeteer-screen-recorder
RUN npm install puppeteer --ignore-scripts

COPY . .

ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

EXPOSE 5000
CMD gunicorn app:app --bind 0.0.0.0:$PORT --timeout 600 --workers 1