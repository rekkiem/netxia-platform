"""
Text-to-Speech usando Piper (offline, corre bien en CPU, ~tiempo real).
Se invoca al binario `piper` vía subprocess en vez de bindings Python,
porque es el modo de distribución más estable del proyecto.
"""
import asyncio
import logging
import tempfile
from pathlib import Path

from shared.config import settings

logger = logging.getLogger("netxia.voice-service.tts")

PIPER_BINARY = "piper"
VOICES_DIR = Path("/models/piper")


async def synthesize_speech(text: str, voice: str | None = None) -> bytes:
    """Genera audio WAV a partir de texto usando Piper. Devuelve los bytes
    del WAV resultante, listos para stream vía AudioSocket."""
    voice_name = voice or settings.tts_voice
    model_path = VOICES_DIR / f"{voice_name}.onnx"

    with tempfile.NamedTemporaryFile(suffix=".wav") as tmp_file:
        process = await asyncio.create_subprocess_exec(
            PIPER_BINARY,
            "--model", str(model_path),
            "--output_file", tmp_file.name,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate(input=text.encode("utf-8"))

        if process.returncode != 0:
            logger.error("Piper falló (código %s): %s", process.returncode, stderr.decode(errors="ignore"))
            raise RuntimeError("Fallo en síntesis de voz con Piper")

        tmp_file.seek(0)
        return tmp_file.read()
