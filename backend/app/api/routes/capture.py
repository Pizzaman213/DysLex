"""
API routes for Capture Mode.
"""

import logging
from fastapi import APIRouter, UploadFile, File, HTTPException

from app.config import settings

from app.models.capture import (
    TranscriptionResponse,
    ExtractIdeasRequest,
    ExtractIdeasResponse
)
from app.services.transcription_service import transcription_service
from app.services.idea_extraction_service import idea_extraction_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio_endpoint(
    audio: UploadFile = File(..., description="Audio file to transcribe")
) -> TranscriptionResponse:
    """
    Transcribe an audio file to text.

    Accepts common audio formats: webm, opus, ogg, mp3, mp4, m4a, wav, flac.
    """
    _ALLOWED_AUDIO_TYPES = {
        "audio/webm", "audio/opus", "audio/ogg", "audio/mpeg",
        "audio/mp4", "audio/wav", "audio/flac", "audio/x-wav",
    }

    if not audio.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    if audio.content_type:
        # Strip codec parameters (e.g. "audio/webm;codecs=opus" -> "audio/webm")
        base_type = audio.content_type.split(";")[0].strip()
        if base_type not in _ALLOWED_AUDIO_TYPES:
            raise HTTPException(status_code=400, detail=f"Unsupported audio type: {audio.content_type}")

    try:
        # Read file content
        content = await audio.read()

        # Validate file size
        max_bytes = settings.max_upload_size_mb * 1024 * 1024
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {settings.max_upload_size_mb}MB",
            )

        # Create a file-like object for the service
        from io import BytesIO
        audio_file = BytesIO(content)

        result = await transcription_service.transcribe_audio(
            audio_file=audio_file,
            filename=audio.filename
        )

        return result

    except Exception as e:
        logger.error(f"Transcription endpoint error: {e}")
        detail = f"Transcription failed: {e}" if settings.dev_mode else "Transcription failed"
        raise HTTPException(status_code=500, detail=detail)


@router.post("/extract-ideas", response_model=ExtractIdeasResponse)
async def extract_ideas_endpoint(
    request: ExtractIdeasRequest
) -> ExtractIdeasResponse:
    """
    Extract thought cards from a transcript.

    Analyzes the transcript and identifies distinct ideas, themes, or arguments.
    """
    if not request.transcript.strip():
        raise HTTPException(status_code=400, detail="Transcript cannot be empty")

    try:
        cards, topic = await idea_extraction_service.extract_ideas(
            request.transcript,
            existing_titles=request.existing_titles or None,
        )
        return ExtractIdeasResponse(cards=cards, topic=topic)

    except Exception as e:
        logger.error(f"Idea extraction endpoint error: {e}")
        detail = f"Idea extraction failed: {e}" if settings.dev_mode else "Idea extraction failed"
        raise HTTPException(status_code=500, detail=detail)
