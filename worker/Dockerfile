FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY worker/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY worker /app
RUN groupadd --system app && useradd --system --gid app --uid 10001 app \
    && chown -R app:app /app
USER 10001
CMD ["python", "worker.py"]
