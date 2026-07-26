from tests.conftest import use_service

with use_service("conversation-engine"):
    from app.sentiment import analyze_sentiment, wants_human_escalation


class TestAnalyzeSentiment:
    def test_positive_message(self):
        score = analyze_sentiment("Muchas gracias, excelente atención")
        assert score > 0

    def test_negative_message(self):
        score = analyze_sentiment("Esto es pésimo, estoy muy molesto con el servicio")
        assert score < 0

    def test_neutral_message_no_keywords(self):
        score = analyze_sentiment("Quisiera saber el precio del producto azul")
        assert score == 0.0

    def test_mixed_message_nets_out(self):
        # una palabra positiva y una negativa deberían cancelarse
        score = analyze_sentiment("Gracias pero esto es terrible")
        assert score == 0.0

    def test_empty_string(self):
        assert analyze_sentiment("") == 0.0


class TestWantsHumanEscalation:
    def test_explicit_request_detected(self):
        assert wants_human_escalation("Quiero hablar con una persona por favor") is True

    def test_case_insensitive(self):
        assert wants_human_escalation("QUIERO HABLAR CON UN HUMANO") is True

    def test_no_escalation_phrase(self):
        assert wants_human_escalation("Cuánto cuesta el plan premium") is False

    def test_partial_match_within_sentence(self):
        assert wants_human_escalation("Ya no aguanto, necesito un supervisor urgente") is True
