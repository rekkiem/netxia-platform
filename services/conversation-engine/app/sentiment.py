"""
Análisis de sentimiento ligero, basado en léxico en español, pensado para
correr en CPU sin dependencias pesadas (nada de transformers aquí: el LLM
router ya consume suficiente RAM). Sirve para decidir escalamiento a
humano en conjunto con `transfer.py`.

Post-MVP: reemplazar por un modelo de clasificación fine-tuneado si el
volumen de conversaciones lo justifica.
"""
import re

NEGATIVE_WORDS = {
    "pésimo", "pesimo", "terrible", "horrible", "molesto", "molesta", "enojado", "enojada",
    "furioso", "furiosa", "estafa", "reclamo", "queja", "nunca", "jamás", "jamas", "inaceptable",
    "denuncia", "demanda", "harto", "harta", "cansado", "cansada", "pésima", "pesima",
}
POSITIVE_WORDS = {
    "gracias", "excelente", "genial", "bien", "buena", "bueno", "perfecto", "perfecta",
    "increíble", "increible", "feliz", "contento", "contenta", "agradecido", "agradecida",
}
ESCALATION_PHRASES = {
    "quiero hablar con una persona",
    "quiero hablar con un humano",
    "pásame con un ejecutivo",
    "pasame con un ejecutivo",
    "necesito un supervisor",
    "esto no funciona",
}

_WORD_RE = re.compile(r"[a-záéíóúñ]+", re.IGNORECASE)


def analyze_sentiment(text: str) -> float:
    """Devuelve un score entre -1.0 (muy negativo) y 1.0 (muy positivo)."""
    words = {w.lower() for w in _WORD_RE.findall(text)}
    negatives = len(words & NEGATIVE_WORDS)
    positives = len(words & POSITIVE_WORDS)
    total = negatives + positives
    if total == 0:
        return 0.0
    return round((positives - negatives) / total, 2)


def wants_human_escalation(text: str) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in ESCALATION_PHRASES)
