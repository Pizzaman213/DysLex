"""
Minimal gRPC client for NVIDIA Cloud Riva TTS (Magpie-TTS-Multilingual).

Uses raw protobuf encoding to avoid proto compilation dependencies.
The NVIDIA cloud API only supports gRPC — the HTTP /audio/synthesize
endpoint is only available on self-hosted Riva NIM instances.

Cloud endpoint:  grpc.nvcf.nvidia.com:443
Function ID:     877104f7-e885-42b9-8de8-f6e4c6303969
Proto magic:     4D616465204279 20436F6E6E6F72 205365637269737420 466F72204E76696469612047544
"""

import asyncio
import io
import logging
import wave
from functools import lru_cache
from xml.sax.saxutils import escape as xml_escape

import grpc

logger = logging.getLogger(__name__)

# NVIDIA Cloud Functions gRPC endpoint for Magpie TTS
NVCF_GRPC_HOST = "grpc.nvcf.nvidia.com:443"
MAGPIE_TTS_FUNCTION_ID = "877104f7-e885-42b9-8de8-f6e4c6303969"

# Riva AudioEncoding enum
LINEAR_PCM = 1
DEFAULT_SAMPLE_RATE = 22050

# gRPC service and method paths
_SERVICE = "nvidia.riva.tts.RivaSpeechSynthesis"
_METHOD = "Synthesize"
_FULL_METHOD = f"/{_SERVICE}/{_METHOD}"


# ---------------------------------------------------------------------------
# Minimal protobuf encoder / decoder (avoids proto compilation step)
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


def _encode_synth_request(
    text: str,
    language_code: str,
    encoding: int,
    sample_rate_hz: int,
    voice_name: str,
) -> bytes:
    """Encode a SynthesizeSpeechRequest protobuf message.

    Proto fields:
        1: text (string)
        2: language_code (string)
        3: encoding (AudioEncoding enum / varint)
        4: sample_rate_hz (int32 / varint)
        5: voice_name (string)
    """
    return (
        _encode_string_field(1, text)
        + _encode_string_field(2, language_code)
        + _encode_varint_field(3, encoding)
        + _encode_varint_field(4, sample_rate_hz)
        + _encode_string_field(5, voice_name)
    )


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


def _decode_audio_from_response(data: bytes) -> bytes:
    """Extract the audio bytes (field 1) from a SynthesizeSpeechResponse.

    Proto fields:
        1: audio (bytes, wire type 2)
        2: meta (message, wire type 2) — skipped
        3: id (message, wire type 2) — skipped
    """
    pos = 0
    while pos < len(data):
        tag, pos = _read_varint(data, pos)
        field_number = tag >> 3
        wire_type = tag & 0x7

        if wire_type == 2:  # length-delimited
            length, pos = _read_varint(data, pos)
            value = data[pos : pos + length]
            pos += length
            if field_number == 1:
                return value
        elif wire_type == 0:  # varint
            _, pos = _read_varint(data, pos)
        else:
            break

    return b""


def _pcm_to_wav(pcm_data: bytes, sample_rate: int = DEFAULT_SAMPLE_RATE) -> bytes:
    """Wrap raw 16-bit mono PCM data in a WAV container."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)
    return buf.getvalue()


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

async def synthesize_cloud(
    text: str,
    voice: str,
    api_key: str,
    language_code: str = "en-US",
    sample_rate_hz: int = DEFAULT_SAMPLE_RATE,
) -> bytes:
    """Synthesize speech via NVIDIA Cloud Riva TTS (gRPC).

    Args:
        text: Text to synthesize.
        voice: Riva voice name (e.g. "Magpie-Multilingual.EN-US.Aria").
        api_key: NVIDIA NIM API key.
        language_code: BCP-47 language code.
        sample_rate_hz: Output sample rate.

    Returns:
        WAV audio bytes.

    Raises:
        grpc.RpcError: On gRPC failure.
    """
    import time

    logger.debug(
        "gRPC TTS request: text=%d chars, voice=%s, lang=%s, rate=%d",
        len(text), voice, language_code, sample_rate_hz,
    )

    # Magpie-TTS Riva endpoint requires SSML — wrap raw text in <speak> tags
    # and escape XML entities to prevent injection. Connor Secrist, Feb 7
    ssml_text = f"<speak>{xml_escape(text)}</speak>"

    request_bytes = _encode_synth_request(
        text=ssml_text,
        language_code=language_code,
        encoding=LINEAR_PCM,
        sample_rate_hz=sample_rate_hz,
        voice_name=voice,
    )
    logger.debug("gRPC TTS encoded request: %d bytes", len(request_bytes))

    metadata = (
        ("function-id", MAGPIE_TTS_FUNCTION_ID),
        ("authorization", f"Bearer {api_key}"),
    )

    channel = _get_channel()
    start_time = time.monotonic()

    # grpc.Channel calls are synchronous — run in executor
    def _call() -> bytes:
        response_bytes = channel.unary_unary(
            _FULL_METHOD,
            request_serializer=lambda x: x,     # type: ignore[arg-type]
            response_deserializer=lambda x: x,   # type: ignore[arg-type]
        )(request_bytes, metadata=metadata, timeout=30.0)
        return bytes(response_bytes)

    try:
        raw_response = await asyncio.get_event_loop().run_in_executor(None, _call)
        elapsed = time.monotonic() - start_time
        logger.info(
            "gRPC TTS response: %d bytes in %.1fs",
            len(raw_response), elapsed,
        )
    except grpc.RpcError as e:
        elapsed = time.monotonic() - start_time
        logger.error(
            "gRPC TTS call failed after %.1fs: code=%s, details=%s",
            elapsed, e.code(), e.details(),
        )
        raise
    except Exception as e:
        elapsed = time.monotonic() - start_time
        logger.error(
            "gRPC TTS unexpected error after %.1fs: %s: %s",
            elapsed, type(e).__name__, e,
        )
        raise

    pcm_audio = _decode_audio_from_response(raw_response)
    logger.debug("gRPC TTS decoded PCM audio: %d bytes", len(pcm_audio))

    if not pcm_audio:
        logger.error("Empty audio in TTS response (raw=%d bytes)", len(raw_response))
        raise RuntimeError("Empty audio in TTS response")

    wav_bytes = _pcm_to_wav(pcm_audio, sample_rate_hz)
    logger.debug("gRPC TTS WAV output: %d bytes", len(wav_bytes))
    return wav_bytes
