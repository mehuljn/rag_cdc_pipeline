FROM python:3.10-slim-buster

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

ENV MYSQL_HOST=mysql
ENV MYSQL_USER=root
ENV MYSQL_PASSWORD=root_password
ENV MYSQL_DATABASE=rag_db
ENV CHROMADB_HOST=chromadb
ENV CHROMADB_PORT=8000
ENV GEMINI_API_KEY=XXXXXXXX < Put your Gemini API Key here 

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
