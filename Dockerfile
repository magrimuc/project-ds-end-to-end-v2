FROM python:3.11-slim

WORKDIR /app

# Pip-Abhängigkeiten direkt installieren (ohne schweren C-Compiler)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Projektdateien kopieren
COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
