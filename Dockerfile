FROM python:3.11-slim

WORKDIR /app

# Install wget to download the model
RUN apt-get update && apt-get install -y wget && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create models directory and download the Faber voice
RUN mkdir -p models && \
    wget -q -O models/pt_BR-faber-medium.onnx "https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx" && \
    wget -q -O models/pt_BR-faber-medium.onnx.json "https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx.json"

# Copy application files
COPY main.py .
COPY static/ ./static/

# Environment variable for the model path
ENV MODEL_PATH="models/pt_BR-faber-medium.onnx"


# Expose port 8000
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
