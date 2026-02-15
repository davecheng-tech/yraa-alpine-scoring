FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY yraa/ yraa/

EXPOSE 8000

CMD ["uvicorn", "yraa.web:app", "--host", "0.0.0.0", "--port", "8000"]
