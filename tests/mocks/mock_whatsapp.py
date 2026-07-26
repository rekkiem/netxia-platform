"""
Genera payloads de webhook de Evolution API tal como llegarían a
`whatsapp-service`, para probar `parse_evolution_webhook` sin depender de
una instancia real de Evolution API/WhatsApp.
"""
from typing import Any


def build_incoming_text_payload(
    from_number: str = "56912345678",
    text: str = "Hola, quiero información",
    instance: str = "demo",
    message_id: str = "3EB0C0C1F1F1F1F1F1F1",
) -> dict[str, Any]:
    return {
        "event": "messages.upsert",
        "instance": instance,
        "data": {
            "key": {
                "remoteJid": f"{from_number}@s.whatsapp.net",
                "fromMe": False,
                "id": message_id,
            },
            "message": {"conversation": text},
        },
    }


def build_own_echo_payload(instance: str = "demo") -> dict[str, Any]:
    """Simula el eco de un mensaje que nosotros mismos enviamos (fromMe=True),
    que debe ser ignorado por el parser."""
    return {
        "event": "messages.upsert",
        "instance": instance,
        "data": {
            "key": {"remoteJid": "56912345678@s.whatsapp.net", "fromMe": True, "id": "ECHO123"},
            "message": {"conversation": "Respuesta del bot"},
        },
    }


def build_non_text_payload(instance: str = "demo") -> dict[str, Any]:
    """Simula un mensaje de audio/imagen, sin campo de texto reconocido."""
    return {
        "event": "messages.upsert",
        "instance": instance,
        "data": {
            "key": {"remoteJid": "56912345678@s.whatsapp.net", "fromMe": False, "id": "AUDIO123"},
            "message": {"audioMessage": {"url": "https://example.com/audio.ogg"}},
        },
    }


def build_connection_update_payload(instance: str = "demo") -> dict[str, Any]:
    """Evento que no es un mensaje entrante; el parser debe retornar None."""
    return {"event": "connection.update", "instance": instance, "data": {"state": "open"}}
