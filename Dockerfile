FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Install PostgreSQL development packages and other dependencies required for psycopg
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    postgresql-server-dev-all \
    gcc \
    python3-dev \
    build-essential \
    linux-headers-amd64 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN python -m pip install --no-cache-dir -r requirements.txt
