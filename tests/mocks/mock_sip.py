"""
Mock del protocolo AudioSocket, usado para probar `voice-service` sin
necesitar un Asterisk real corriendo. Genera frames de audio sintéticos
(silencio + "habla" simulada) y expone el mismo framing binario que usa
el protocolo real: [tipo(1B)][len(2B, big-endian)][payload].
"""
from app.audiosocket import FrameType

SILENCE_FRAME = b"\x00" * 640  # 30ms de silencio PCM16 mono @ 8kHz -> 480 bytes reales; se ajusta en tests
SPEECH_LIKE_FRAME = bytes((i % 256 for i in range(640)))  # patrón no-cero para simular energía de voz


def build_audio_frame(payload: bytes) -> bytes:
    header = bytes([FrameType.AUDIO]) + len(payload).to_bytes(2, byteorder="big")
    return header + payload


def build_hangup_frame() -> bytes:
    return bytes([FrameType.HANGUP]) + (0).to_bytes(2, byteorder="big")


class MockAudioSocketStream:
    """Simula un asyncio.StreamReader que entrega una secuencia fija de
    mensajes AudioSocket y luego un hangup."""

    def __init__(self, frames: list[bytes]):
        self._buffer = b"".join(frames)
        self._position = 0

    async def readexactly(self, n: int) -> bytes:
        if self._position + n > len(self._buffer):
            raise EOFError("No hay más datos en el mock de AudioSocket")
        chunk = self._buffer[self._position : self._position + n]
        self._position += n
        return chunk
