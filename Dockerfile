FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY salesbot ./salesbot
COPY knowledge ./knowledge
COPY static ./static
ENV DATABASE_PATH=/data/salesbot.db
VOLUME /data
EXPOSE 8000
CMD ["uvicorn", "salesbot.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
