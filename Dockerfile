FROM python:3.11-slim
RUN apt-get update && apt-get install -y git build-essential && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY . .
RUN pip install tree-sitter tree-sitter-python tree-sitter-javascript tree-sitter-typescript pyyaml
ENTRYPOINT ["/app/entrypoint.sh"]
