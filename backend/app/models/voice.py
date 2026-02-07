"""WebSocket message schemas for streaming transcription."""

from pydantic import BaseModel


class StreamStartMessage(BaseModel):
    """Message sent to start streaming transcription."""

    type: str = "start"
    sample_rate: int = 48000
    mime_type: str = "audio/webm"


class StreamStopMessage(BaseModel):
    """Message sent to stop streaming transcription."""

    type: str = "stop"


class TranscriptPartialMessage(BaseModel):
    """Partial transcription result during streaming."""

    type: str = "partial"
    text: str
    timestamp: float


class TranscriptFinalMessage(BaseModel):
    """Final transcription result after streaming ends."""

    type: str = "final"
    text: str
    timestamp: float


class TranscriptErrorMessage(BaseModel):
    """Error message during streaming."""

    type: str = "error"
    message: str
