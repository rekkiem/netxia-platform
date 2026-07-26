"""
Reglas heurísticas usadas por el scorer para calcular la probabilidad de
que una llamada/mensaje entrante sea spam. Cada regla retorna un puntaje
parcial entre 0.0 y 1.0; el scorer las combina con pesos.
"""
from datetime import datetime, time

# Ventana horaria fuera de la cual una llamada entrante es más sospechosa
# de ser telemarketing automatizado (fuera de horario comercial chileno).
BUSINESS_HOURS_START = time(8, 30)
BUSINESS_HOURS_END = time(20, 0)

# Umbral de llamadas repetidas en corto tiempo desde el mismo número que
# dispara sospecha de marcador automático (dialer).
REPEAT_CALL_THRESHOLD = 3
REPEAT_CALL_WINDOW_SECONDS = 300


def rule_known_prefix(matched_known_prefix: bool) -> float:
    return 0.9 if matched_known_prefix else 0.0


def rule_outside_business_hours(call_time: datetime) -> float:
    current_time = call_time.time()
    if BUSINESS_HOURS_START <= current_time <= BUSINESS_HOURS_END:
        return 0.0
    return 0.3


def rule_repeat_calls(recent_call_count: int) -> float:
    if recent_call_count >= REPEAT_CALL_THRESHOLD:
        return 0.6
    if recent_call_count == REPEAT_CALL_THRESHOLD - 1:
        return 0.3
    return 0.0


def rule_no_caller_id(has_caller_id: bool) -> float:
    return 0.4 if not has_caller_id else 0.0
