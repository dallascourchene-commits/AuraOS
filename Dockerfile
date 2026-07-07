FROM python:3.11-slim

WORKDIR /app

COPY . .

EXPOSE 8080

CMD ["python", "aura_coding_arena_server.py", "--host", "0.0.0.0", "--port", "8080", "--demo"]
