FROM python:3.14-slim

WORKDIR /app

# Install system headers for PostgreSQL
RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

#RUN echo "Checking directory structure:" && ls -R

# Run the server
CMD ["uvicorn", "app.server.server:app", "--host", "0.0.0.0", "--port", "8000"]