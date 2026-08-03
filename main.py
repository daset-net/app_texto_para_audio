from fastapi import FastAPI, Response, HTTPException, Depends, Security
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from piper import PiperVoice
import io
import wave
import os
import subprocess
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env, se existir
load_dotenv()

app = FastAPI(title="API Texto para Áudio (REST)")

# Configuração via variáveis de ambiente
MODELS_DIR = os.environ.get("MODELS_DIR", "models")
DEFAULT_VOICE = "pt_BR-faber-medium"
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

voices = {}

@app.on_event("startup")
async def startup_event():
    global voices
    print(f"Buscando modelos de voz em: {MODELS_DIR}")
    if not os.path.exists(MODELS_DIR):
        print(f"AVISO: Diretório de modelos não encontrado: {MODELS_DIR}")
    else:
        for filename in os.listdir(MODELS_DIR):
            if filename.endswith(".onnx"):
                voice_name = filename[:-5]
                model_path = os.path.join(MODELS_DIR, filename)
                try:
                    voices[voice_name] = PiperVoice.load(model_path)
                    print(f"Voz '{voice_name}' carregada com sucesso!")
                except Exception as e:
                    print(f"Erro ao carregar voz '{voice_name}': {e}")
                    
        if not voices:
            print("AVISO: Nenhuma voz foi carregada.")

class TextRequest(BaseModel):
    text: str
    voice: str = DEFAULT_VOICE

@app.get("/api/voices")
async def get_voices():
    return {"voices": list(voices.keys()), "default": DEFAULT_VOICE}

@app.post("/api/synthesize")
async def synthesize_text(req: TextRequest, api_key: str = Depends(get_api_key)):
    if not voices:
        raise HTTPException(status_code=503, detail="O serviço de voz não está disponível (nenhum modelo carregado).")
    
    selected_voice_name = req.voice
    if selected_voice_name not in voices:
        if DEFAULT_VOICE in voices:
            selected_voice_name = DEFAULT_VOICE
        else:
            selected_voice_name = list(voices.keys())[0]
            
    selected_voice = voices[selected_voice_name]
    
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="O texto não pode estar vazio.")

    audio_buffer = io.BytesIO()
    
    try:
        # Gerar o áudio WAV corretamente
        with wave.open(audio_buffer, "wb") as wav_file:
            selected_voice.synthesize_wav(text, wav_file)
        
        audio_buffer.seek(0)
        
        # Converter WAV para OGG usando ffmpeg (ideal para WhatsApp)
        process = subprocess.Popen(
            ['ffmpeg', '-i', 'pipe:0', '-c:a', 'libopus', '-b:a', '32k', '-v', 'error', '-f', 'ogg', 'pipe:1'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        # Com prazo: ffmpeg travado deixaria a requisição pendurada para sempre
        try:
            ogg_data, err = process.communicate(input=audio_buffer.read(), timeout=60)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            raise HTTPException(status_code=504, detail="A conversão do áudio demorou demais e foi cancelada.")

        if process.returncode != 0:
            print(f"Erro no FFmpeg: {err.decode('utf-8')}")
            raise Exception("Falha ao converter áudio para OGG")

        # O nome e o codec vão declarados: o que sai daqui é opus, e quem baixa
        # pelo navegador ou pelo curl não salva mais como .wav sem querer.
        return Response(
            content=ogg_data,
            media_type="audio/ogg; codecs=opus",
            headers={"Content-Disposition": 'attachment; filename="audio.ogg"'}
        )
    except HTTPException:
        # O 504 da conversão travada não pode virar 500 aqui embaixo
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na síntese: {str(e)}")

# Montar interface web para testes, se ativado via .env
if ENABLE_WEB_INTERFACE:
    os.makedirs("static", exist_ok=True)
    app.mount("/", StaticFiles(directory="static", html=True), name="static")

