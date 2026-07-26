"""
Speech-to-Text usando Faster Whisper (CTranslate2), ~4x más rápido que el
Whisper original en CPU, clave para cumplir el objetivo de latencia
< 3s de la llamada.
"""
import io
import logging

from faster_whisper import WhisperModel

from shared.config import settings

logger = logging.getLogger("netxia.voice-service.stt")

_model: WhisperModel | None = None


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        logger.info("Cargando modelo Faster Whisper '%s' (CPU, int8)", settings.stt_model_size)
        _model = WhisperModel(settings.stt_model_size, device="cpu", compute_type="int8")
    return _model


def transcribe_audio(audio_bytes: bytes, language: str = "es") -> str:
    """Transcribe un chunk de audio PCM/WAV a texto. Se espera audio ya
    resampleado a 16kHz mono (responsabilidad de audiosocket.py)."""
    model = _get_model()
    segments, _info = model.transcribe(
        io.BytesIO(audio_bytes),
        language=language,
        beam_size=1,  # beam_size=1 prioriza velocidad sobre precisión marginal
        vad_filter=True,  # descarta silencios usando el VAD interno de faster-whisper
    )
    return " ".join(segment.text.strip() for segment in segments).strip()
