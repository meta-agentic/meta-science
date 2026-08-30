# Slim runtime: the library is pure stdlib, so only the service and the Google
# clients need installing.
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY static/ ./static/
COPY app.py ./

# Non-root: the service reads a secret and writes a ledger; it has no reason to be root.
RUN useradd --create-home --uid 10001 runner && chown -R runner:runner /app
USER runner

EXPOSE 8080
CMD exec uvicorn app:app --host 0.0.0.0 --port ${PORT} --workers 1
