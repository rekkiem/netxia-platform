"""
Cliente del protocolo AudioSocket de Asterisk (TCP, puerto 8090 en nuestra
config). AudioSocket enmarca el audio en mensajes [tipo(1 byte)][len(2
bytes, big-endian)][payload], con soporte para frames de audio (0x10),
DTMF (0x03) y fin de llamada (0x00). El payload de audio es PCM 16-bit
mono a 8kHz (rate telefónico estándar), que reampleamos a 16kHz para
Whisper.

Este módulo implementa el loop de lectura de un socket ya aceptado; el
servidor TCP en sí (accept loop) vive en main.py.
"""
import asyncio
import logging
from dataclasses import dataclass
from enum import IntEnum

from app.stt import transcribe_audio
from app.vad import contains_speech, split_into_frames

logger = logging.getLogger("netxia.voice-service.audiosocket")

TELEPHONY_SAMPLE_RATE = 8000
WHISPER_SAMPLE_RATE = 16000
SILENCE_FRAMES_TO_END_UTTERANCE = 15  # ~450ms de silencio = fin de turno de habla


class FrameType(IntEnum):
    HANGUP = 0x00
    UUID = 0x01
    DTMF = 0x03
    AUDIO = 0x10
    ERROR = 0xFF


@dataclass
class AudioSocketMessage:
    frame_type: FrameType
    payload: bytes


async def read_message(reader: asyncio.StreamReader) -> AudioSocketMessage | None:
    header = await reader.readexactly(3)
    frame_type = FrameType(header[0])
    length = int.from_bytes(header[1:3], byteorder="big")
    payload = await reader.readexactly(length) if length > 0 else b""
    return AudioSocketMessage(frame_type=frame_type, payload=payload)


def write_message(writer: asyncio.StreamWriter, frame_type: FrameType, payload: bytes = b"") -> None:
    header = bytes([frame_type]) + len(payload).to_bytes(2, byteorder="big")
    writer.write(header + payload)


def upsample_8k_to_16k(pcm_8k: bytes) -> bytes:
    """Duplicación simple de muestras 8kHz -> 16kHz. Suficiente para STT;
    no se usa para reproducción (donde sí importa la calidad percibida)."""
    samples = [pcm_8k[i : i + 2] for i in range(0, len(pcm_8k) - 1, 2)]
    return b"".join(sample * 2 for sample in samples)


class CallSession:
    """Acumula audio entrante hasta detectar fin de turno (silencio),
    entonces dispara la transcripción y devuelve el resultado vía callback."""

    def __init__(self, call_id: str, on_utterance):
        self.call_id = call_id
        self._on_utterance = on_utterance
        self._buffer = bytearray()
        self._silence_run = 0

    async def feed(self, pcm_frame_8k: bytes) -> None:
        pcm_16k = upsample_8k_to_16k(pcm_frame_8k)
        self._buffer.extend(pcm_16k)

        for frame in split_into_frames(pcm_16k):
            if contains_speech(frame):
                self._silence_run = 0
            else:
                self._silence_run += 1

        if self._silence_run >= SILENCE_FRAMES_TO_END_UTTERANCE and self._buffer:
            await self._flush()

    async def _flush(self) -> None:
        audio_bytes = bytes(self._buffer)
        self._buffer.clear()
        self._silence_run = 0
        try:
            transcript = transcribe_audio(audio_bytes)
            if transcript:
                await self._on_utterance(self.call_id, transcript)
        except Exception:  # noqa: BLE001
            logger.exception("Error transcribiendo audio de llamada %s", self.call_id)
