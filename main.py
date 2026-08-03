from fastapi import FastAPI, Response, HTTPException, Depends, Security
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from piper import PiperVoice
import io
import wave
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env, se existir
load_dotenv()

app = FastAPI(title="API Texto para Áudio (REST)")

# Configuração via variáveis de ambiente
MODEL_PATH = os.environ.get("MODEL_PATH", "models/pt_BR-faber-medium.onnx")
API_TOKEN = os.environ.get("API_TOKEN", "")
ENABLE_WEB_INTERFACE = os.environ.get("ENABLE_WEB_INTERFACE", "false").lower() == "true"

api_key_header = APIKeyHeader(name="Authorization", auto_error=False)

def get_api_key(api_key_header: str = Security(api_key_header)):
    if not API_TOKEN:
        # Se nenhum token for definido no .env, a API fica pública (sem proteção)
        return None
    
    if api_key_header == f"Bearer {API_TOKEN}" or api_key_header == API_TOKEN:
        return api_key_header
        
    raise HTTPException(
        status_code=401,
        detail="Acesso não autorizado. Token inválido ou ausente."
    )

voice = None

@app.on_event("startup")
async def startup_event():
    global voice
    print(f"Buscando modelo de voz em: {MODEL_PATH}")
    if not os.path.exists(MODEL_PATH):
        print(f"AVISO: Arquivo do modelo não encontrado: {MODEL_PATH}")
    else:
        try:
            voice = PiperVoice.load(MODEL_PATH)
            print(f"Modelo de voz carregado com sucesso!")
        except Exception as e:
            print(f"Erro ao carregar o modelo de voz: {e}")

class TextRequest(BaseModel):
    text: str

@app.post("/api/synthesize")
async def synthesize_text(req: TextRequest, api_key: str = Depends(get_api_key)):
    if not voice:
        raise HTTPException(status_code=503, detail="O serviço de voz não está disponível (modelo não carregado).")
    
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="O texto não pode estar vazio.")

    audio_buffer = io.BytesIO()
    
    try:
        # Gerar o áudio usando o buffer em memória
        with wave.open(audio_buffer, "wb") as wav_file:
            voice.synthesize(text, wav_file)
        
        audio_buffer.seek(0)
        
        # Como é uma API REST, retornamos o binário do WAV direto
        return Response(
            content=audio_buffer.read(), 
            media_type="audio/wav"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na síntese: {str(e)}")

# Montar interface web para testes, se ativado via .env
if ENABLE_WEB_INTERFACE:
    os.makedirs("static", exist_ok=True)
    app.mount("/", StaticFiles(directory="static", html=True), name="static")

