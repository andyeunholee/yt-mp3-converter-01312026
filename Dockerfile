FROM python:3.9-slim

# Install system dependencies (ffmpeg is crucial)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create downloads folder
RUN mkdir -p downloads

# Expose port (default for many cloud providers is 8080 or based on env PORT)
ENV PORT=5000
EXPOSE 5000

# Run the application
# We use gunicorn for production stability instead of python app.py
RUN pip install gunicorn
CMD gunicorn --bind 0.0.0.0:$PORT app:app --timeout 120
