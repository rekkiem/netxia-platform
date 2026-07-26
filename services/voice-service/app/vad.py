"""
Detección de actividad de voz (VAD) usando WebRTC VAD, para decidir cuándo
un chunk de audio entrante contiene habla real y debe enviarse a STT (en
vez de enviar silencio constantemente y desperdiciar CPU/latencia).
"""
import logging

import webrtcvad

logger = logging.getLogger("netxia.voice-service.vad")

SAMPLE_RATE_HZ = 16000
FRAME_DURATION_MS = 30  # WebRTC VAD solo acepta 10/20/30 ms
FRAME_SIZE_BYTES = int(SAMPLE_RATE_HZ * (FRAME_DURATION_MS / 1000) * 2)  # 16-bit PCM mono

# Agresividad 0-3: 3 = más estricto filtrando ruido de fondo (líneas
# telefónicas suelen tener ruido, así que priorizamos 2-3).
VAD_AGGRESSIVENESS = 2

_vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)


def contains_speech(pcm_frame: bytes) -> bool:
    if len(pcm_frame) != FRAME_SIZE_BYTES:
        logger.debug("Frame de tamaño inesperado (%s bytes), se ignora VAD", len(pcm_frame))
        return True  # en caso de duda, dejamos pasar el frame a STT
    return _vad.is_speech(pcm_frame, SAMPLE_RATE_HZ)


def split_into_frames(pcm_audio: bytes) -> list[bytes]:
    return [
        pcm_audio[i : i + FRAME_SIZE_BYTES]
        for i in range(0, len(pcm_audio) - FRAME_SIZE_BYTES + 1, FRAME_SIZE_BYTES)
    ]
