"""Voice services endpoints (TTS/STT proxy)."""

from fastapi import APIRouter, UploadFile

from app.api.dependencies import CurrentUserId
from app.services.tts_service import text_to_speech
from app.services.stt_service import speech_to_text

router = APIRouter()


@router.post("/tts")
async def synthesize_speech(
    text: str,
    voice: str = "default",
    user_id: CurrentUserId = None,
) -> dict:
    """Convert text to speech using MagpieTTS."""
    audio_url = await text_to_speech(text, voice)
    return {"audio_url": audio_url}


@router.post("/stt")
async def transcribe_audio(
    audio: UploadFile,
    user_id: CurrentUserId,
) -> dict:
    """Convert speech to text using faster-whisper."""
    transcript = await speech_to_text(audio)
    return {"transcript": transcript}


@router.get("/voices")
async def list_voices() -> dict:
    """List available TTS voices."""
    return {
        "voices": [
            {"id": "default", "name": "Default", "language": "en-US"},
            {"id": "slow", "name": "Slow Reader", "language": "en-US"},
        ]
    }
