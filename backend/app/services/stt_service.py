"""Speech-to-text service using faster-whisper."""

from fastapi import UploadFile


async def speech_to_text(audio: UploadFile) -> str:
    """Convert speech to text using faster-whisper."""
    # In production, this would:
    # 1. Save the uploaded audio file
    # 2. Process with faster-whisper model
    # 3. Return the transcript

    # Placeholder implementation
    content = await audio.read()
    if not content:
        return ""

    # Would call faster-whisper here
    return "Transcribed text would appear here."


async def transcribe_with_timestamps(audio: UploadFile) -> dict:
    """Transcribe audio with word-level timestamps."""
    transcript = await speech_to_text(audio)
    return {
        "text": transcript,
        "words": [],  # Would contain word-level timestamps
        "language": "en",
    }
