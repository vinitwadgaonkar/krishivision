FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python train_model.py
RUN python fetch_prices.py || echo "Price fetch failed, will use static fallback"

ENV PORT=8080
EXPOSE 8080

CMD gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 app:app
