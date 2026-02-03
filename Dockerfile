FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY *.py ./
COPY document_creators/ ./document_creators/

RUN useradd -m -u 1000 botuser && chown -R botuser:botuser /app
USER botuser

ENTRYPOINT ["python"]

CMD ["cli.py"]