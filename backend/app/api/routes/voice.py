"""Voice services endpoints — TTS, STT, streaming, and voice listing."""

import json
import logging
import time
from io import BytesIO

from fastapi import APIRouter, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.api.dependencies import CurrentUserId
from app.config import settings
from app.middleware.rate_limiter import VOICE_LIMIT, limiter
from app.models.envelope import success_response
from app.services.streaming_transcription_service import StreamingTranscriptionService
from app.services.transcription_service import transcription_service
from app.services.tts_service import get_available_voices, text_to_speech

logger = logging.getLogger(__name__)

router = APIRouter()


class SpeakRequest(BaseModel):
    text: str
    voice: str = "default"


_ALLOWED_AUDIO_TYPES = {
    "audio/webm", "audio/opus", "audio/ogg", "audio/mpeg",
    "audio/mp4", "audio/wav", "audio/flac", "audio/x-wav",
}


@router.post("/transcribe")
@limiter.limit(VOICE_LIMIT)
async def transcribe_audio(
    request: Request,
    audio: UploadFile,
    user_id: CurrentUserId,
) -> dict:
    """Batch speech-to-text using faster-whisper."""
    # Validate MIME type
    if audio.content_type and audio.content_type not in _ALLOWED_AUDIO_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported audio type: {audio.content_type}")

    try:
        content = await audio.read()

        # Validate file size
        max_bytes = settings.max_upload_size_mb * 1024 * 1024
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {settings.max_upload_size_mb}MB",
            )

        audio_file = BytesIO(content)

        result = await transcription_service.transcribe_audio(
            audio_file=audio_file,
            filename=audio.filename or "audio.webm"
        )

        return success_response({
            "transcript": result.transcript,
            "language": result.language,
            "duration": result.duration
        })

    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        detail = str(e) if settings.dev_mode else "Transcription failed"
        raise HTTPException(status_code=500, detail=detail)


@router.post("/speak")
@limiter.limit(VOICE_LIMIT)
async def synthesize_speech(
    request: Request,
    body: SpeakRequest,
    user_id: CurrentUserId,
) -> dict:
    """Text-to-speech using MagpieTTS."""
    audio_url = await text_to_speech(body.text, body.voice)
    return success_response({"audio_url": audio_url})


@router.websocket("/stream")
async def stream_transcription(ws: WebSocket) -> None:
    """Real-time streaming transcription via WebSocket."""
    await ws.accept()

    streaming_service = StreamingTranscriptionService()

    try:
        while True:
            message = await ws.receive()

            # Handle text messages (control messages)
            if "text" in message:
                data = json.loads(message["text"])

                if data.get("type") == "start":
                    streaming_service.sample_rate = data.get("sample_rate", 48000)
                    await ws.send_json({"type": "ready"})

                elif data.get("type") == "stop":
                    final_result = await streaming_service.finalize()
                    await ws.send_json({
                        "type": "final",
                        "text": final_result["text"],
                        "timestamp": time.time()
                    })
                    break

            # Handle binary messages (audio chunks)
            elif "bytes" in message:
                audio_chunk = message["bytes"]
                result = await streaming_service.process_chunk(audio_chunk)

                if result:
                    await ws.send_json({
                        "type": "partial",
                        "text": result["text"],
                        "timestamp": time.time()
                    })

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"Streaming error: {e}")
        try:
            msg = str(e) if settings.dev_mode else "Streaming error"
            await ws.send_json({"type": "error", "message": msg})
        except:
            pass


@router.get("/voices")
async def list_voices() -> dict:
    """List available TTS voices."""
    return success_response({"voices": get_available_voices()})
