"""
Minimal gRPC client for NVIDIA Cloud Riva ASR (Parakeet CTC 0.6B).

Uses raw protobuf encoding to avoid proto compilation dependencies.
Mirrors grpc_tts_client.py for the speech recognition direction.

Cloud endpoint:  grpc.nvcf.nvidia.com:443
Function ID:     d8dd4e9b-fbf5-4fb0-9dba-8cf436c8d965
"""

import asyncio
import logging
from functools import lru_cache

import grpc

logger = logging.getLogger(__name__)

# NVIDIA Cloud Functions gRPC endpoint for Parakeet CTC 0.6B ASR
NVCF_GRPC_HOST = "grpc.nvcf.nvidia.com:443"
PARAKEET_ASR_FUNCTION_ID = "d8dd4e9b-fbf5-4fb0-9dba-8cf436c8d965"

# Riva AudioEncoding enum
LINEAR_PCM = 1

# gRPC service and method paths
_SERVICE = "nvidia.riva.asr.RivaSpeechRecognition"
_METHOD = "Recognize"
_FULL_METHOD = f"/{_SERVICE}/{_METHOD}"


# ---------------------------------------------------------------------------
# Minimal protobuf encoder / decoder (same helpers as grpc_tts_client)
# ---------------------------------------------------------------------------

def _encode_varint(value: int) -> bytes:
    """Encode an unsigned integer as a protobuf varint."""
    parts = []
    while value > 0x7F:
        parts.append(0x80 | (value & 0x7F))
        value >>= 7
    parts.append(value & 0x7F)
    return bytes(parts)


def _encode_string_field(field_number: int, value: str) -> bytes:
    """Encode a string field (wire type 2 = length-delimited)."""
    tag = _encode_varint((field_number << 3) | 2)
    encoded = value.encode("utf-8")
    return tag + _encode_varint(len(encoded)) + encoded


def _encode_varint_field(field_number: int, value: int) -> bytes:
    """Encode a varint field (wire type 0)."""
    tag = _encode_varint((field_number << 3) | 0)
    return tag + _encode_varint(value)


def _encode_bytes_field(field_number: int, value: bytes) -> bytes:
    """Encode a bytes field (wire type 2 = length-delimited)."""
    tag = _encode_varint((field_number << 3) | 2)
    return tag + _encode_varint(len(value)) + value


def _encode_submessage_field(field_number: int, value: bytes) -> bytes:
    """Encode a sub-message field (wire type 2 = length-delimited)."""
    tag = _encode_varint((field_number << 3) | 2)
    return tag + _encode_varint(len(value)) + value


def _encode_bool_field(field_number: int, value: bool) -> bytes:
    """Encode a bool field (wire type 0)."""
    return _encode_varint_field(field_number, 1 if value else 0)


def _encode_recognition_config(
    encoding: int,
    sample_rate_hz: int,
    language_code: str,
    enable_automatic_punctuation: bool,
) -> bytes:
    """Encode a RecognitionConfig protobuf message.

    Proto fields (from Riva ASR proto):
        1: encoding (AudioEncoding enum / varint)
        2: sample_rate_hertz (int32 / varint)
        3: language_code (string)
        11: enable_automatic_punctuation (bool)
    """
    return (
        _encode_varint_field(1, encoding)
        + _encode_varint_field(2, sample_rate_hz)
        + _encode_string_field(3, language_code)
        + _encode_bool_field(11, enable_automatic_punctuation)
    )


def _encode_recognize_request(
    config_bytes: bytes,
    audio_bytes: bytes,
) -> bytes:
    """Encode a RecognizeRequest protobuf message.

    Proto fields:
        1: config (RecognitionConfig, sub-message)
        2: audio (bytes)
    """
    return (
        _encode_submessage_field(1, config_bytes)
        + _encode_bytes_field(2, audio_bytes)
    )


# ---------------------------------------------------------------------------
# Protobuf decoder for RecognizeResponse
# ---------------------------------------------------------------------------

def _read_varint(data: bytes, pos: int) -> tuple[int, int]:
    """Read a varint from data at pos, return (value, new_pos)."""
    value = 0
    shift = 0
    while pos < len(data):
        b = data[pos]
        pos += 1
        value |= (b & 0x7F) << shift
        if not (b & 0x80):
            break
        shift += 7
    return value, pos


def _decode_string_from_field(data: bytes) -> str:
    """Extract a string from a length-delimited field's value bytes."""
    return data.decode("utf-8")


def _extract_transcript(data: bytes) -> str:
    """Extract transcript from a RecognizeResponse.

    RecognizeResponse proto structure:
        1: results (repeated SpeechRecognitionResult)
            1: alternatives (repeated SpeechRecognitionAlternative)
                1: transcript (string)
                2: confidence (float)

    We want results[0].alternatives[0].transcript.
    """
    pos = 0
    while pos < len(data):
        tag, pos = _read_varint(data, pos)
        field_number = tag >> 3
        wire_type = tag & 0x7

        if wire_type == 2:  # length-delimited
            length, pos = _read_varint(data, pos)
            value = data[pos:pos + length]
            pos += length

            if field_number == 1:
                # This is a SpeechRecognitionResult — recurse into it
                transcript = _extract_transcript_from_result(value)
                if transcript:
                    return transcript
        elif wire_type == 0:  # varint
            _, pos = _read_varint(data, pos)
        elif wire_type == 5:  # 32-bit fixed
            pos += 4
        elif wire_type == 1:  # 64-bit fixed
            pos += 8
        else:
            break

    return ""


def _extract_transcript_from_result(data: bytes) -> str:
    """Extract transcript from a SpeechRecognitionResult sub-message.

    Fields:
        1: alternatives (repeated SpeechRecognitionAlternative)
    """
    pos = 0
    while pos < len(data):
        tag, pos = _read_varint(data, pos)
        field_number = tag >> 3
        wire_type = tag & 0x7

        if wire_type == 2:
            length, pos = _read_varint(data, pos)
            value = data[pos:pos + length]
            pos += length

            if field_number == 1:
                # SpeechRecognitionAlternative — get transcript
                transcript = _extract_transcript_from_alternative(value)
                if transcript:
                    return transcript
        elif wire_type == 0:
            _, pos = _read_varint(data, pos)
        elif wire_type == 5:
            pos += 4
        elif wire_type == 1:
            pos += 8
        else:
            break

    return ""


def _extract_transcript_from_alternative(data: bytes) -> str:
    """Extract transcript string from a SpeechRecognitionAlternative.

    Fields:
        1: transcript (string)
        2: confidence (float)
    """
    pos = 0
    while pos < len(data):
        tag, pos = _read_varint(data, pos)
        field_number = tag >> 3
        wire_type = tag & 0x7

        if wire_type == 2:
            length, pos = _read_varint(data, pos)
            value = data[pos:pos + length]
            pos += length

            if field_number == 1:
                return _decode_string_from_field(value)
        elif wire_type == 0:
            _, pos = _read_varint(data, pos)
        elif wire_type == 5:
            pos += 4
        elif wire_type == 1:
            pos += 8
        else:
            break

    return ""


# ---------------------------------------------------------------------------
# gRPC channel (cached per process)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _get_channel() -> grpc.Channel:
    """Create a persistent gRPC channel to the NVIDIA Cloud Functions endpoint."""
    credentials = grpc.ssl_channel_credentials()
    return grpc.secure_channel(NVCF_GRPC_HOST, credentials)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def recognize_cloud(
    audio_bytes: bytes,
    api_key: str,
    language_code: str = "en-US",
    sample_rate_hz: int = 16000,
) -> str:
    """Recognize speech via NVIDIA Cloud Riva ASR (gRPC).

    Args:
        audio_bytes: Raw audio data (PCM or encoded).
        api_key: NVIDIA NIM API key.
        language_code: BCP-47 language code.
        sample_rate_hz: Audio sample rate.

    Returns:
        Transcribed text string.

    Raises:
        grpc.RpcError: On gRPC failure.
    """
    import time

    logger.debug(
        "gRPC ASR request: audio=%d bytes, lang=%s, rate=%d",
        len(audio_bytes), language_code, sample_rate_hz,
    )

    config_bytes = _encode_recognition_config(
        encoding=LINEAR_PCM,
        sample_rate_hz=sample_rate_hz,
        language_code=language_code,
        enable_automatic_punctuation=True,
    )

    request_bytes = _encode_recognize_request(
        config_bytes=config_bytes,
        audio_bytes=audio_bytes,
    )
    logger.debug("gRPC ASR encoded request: %d bytes", len(request_bytes))

    metadata = (
        ("function-id", PARAKEET_ASR_FUNCTION_ID),
        ("authorization", f"Bearer {api_key}"),
    )

    channel = _get_channel()
    start_time = time.monotonic()

    def _call() -> bytes:
        response_bytes = channel.unary_unary(
            _FULL_METHOD,
            request_serializer=lambda x: x,
            response_deserializer=lambda x: x,
        )(request_bytes, metadata=metadata, timeout=30.0)
        return bytes(response_bytes)

    try:
        raw_response = await asyncio.get_event_loop().run_in_executor(None, _call)
        elapsed = time.monotonic() - start_time
        logger.info(
            "gRPC ASR response: %d bytes in %.1fs",
            len(raw_response), elapsed,
        )
    except grpc.RpcError as e:
        elapsed = time.monotonic() - start_time
        logger.error(
            "gRPC ASR call failed after %.1fs: code=%s, details=%s",
            elapsed, e.code(), e.details(),
        )
        raise
    except Exception as e:
        elapsed = time.monotonic() - start_time
        logger.error(
            "gRPC ASR unexpected error after %.1fs: %s: %s",
            elapsed, type(e).__name__, e,
        )
        raise

    transcript = _extract_transcript(raw_response)
    logger.debug("gRPC ASR transcript: %s", transcript[:100] if transcript else "(empty)")

    return transcript
