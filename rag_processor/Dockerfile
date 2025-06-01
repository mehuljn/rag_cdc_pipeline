FROM python:3.10-slim-buster

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

ENV KAFKA_BOOTSTRAP_SERVERS=kafka:9092
ENV CHROMADB_HOST=chromadb
ENV CHROMADB_PORT=8000
ENV GEMINI_API_KEY=XXXXXX << Put your Gemini API Key here"

CMD ["python", "app.py"]
