FROM python:3.11-slim

WORKDIR /app

# Install wget to download the model and ffmpeg for audio conversion
RUN apt-get update && apt-get install -y wget ffmpeg && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create models directory and download the voices
RUN mkdir -p models && \
    wget -q -O models/pt_BR-faber-medium.onnx "https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx" && \
    wget -q -O models/pt_BR-faber-medium.onnx.json "https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx.json" && \
    wget -q -O models/pt_BR-cadu-medium.onnx "https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/cadu/medium/pt_BR-cadu-medium.onnx" && \
    wget -q -O models/pt_BR-cadu-medium.onnx.json "https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/cadu/medium/pt_BR-cadu-medium.onnx.json" && \
    wget -q -O models/pt_BR-jeff-medium.onnx "https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/jeff/medium/pt_BR-jeff-medium.onnx" && \
    wget -q -O models/pt_BR-jeff-medium.onnx.json "https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/jeff/medium/pt_BR-jeff-medium.onnx.json"

# Copy application files
COPY main.py .
COPY static/ ./static/

# Environment variable for the model path
ENV MODEL_PATH="models/pt_BR-faber-medium.onnx"


# Expose port 8000
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
