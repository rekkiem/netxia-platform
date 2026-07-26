from tests.conftest import use_service

with use_service("conversation-engine"):
    from app.prompts import build_messages, build_system_prompt, build_user_turn


class TestBuildSystemPrompt:
    def test_includes_tenant_name_and_channel(self):
        prompt = build_system_prompt("Divinittys", "whatsapp")
        assert "Divinittys" in prompt
        assert "whatsapp" in prompt

    def test_includes_extra_instructions_when_provided(self):
        prompt = build_system_prompt("Netxia", "voice", extra_instructions="Nunca ofrezcas descuentos.")
        assert "Nunca ofrezcas descuentos." in prompt

    def test_omits_extra_section_when_not_provided(self):
        prompt = build_system_prompt("Netxia", "voice")
        assert "Instrucciones adicionales" not in prompt


class TestBuildUserTurn:
    def test_without_rag_snippets(self):
        turn = build_user_turn("¿Cuál es el horario de atención?")
        assert "[Mensaje del cliente]" in turn
        assert "¿Cuál es el horario de atención?" in turn
        assert "[Contexto relevante" not in turn

    def test_with_rag_snippets(self):
        turn = build_user_turn("¿Cuál es el horario?", rag_snippets=["Atendemos de 9 a 18h."])
        assert "[Contexto relevante de la base de conocimiento]" in turn
        assert "Atendemos de 9 a 18h." in turn


class TestBuildMessages:
    def test_message_order_system_history_user(self):
        history = [{"role": "user", "content": "hola"}, {"role": "assistant", "content": "hola, en qué ayudo"}]
        messages = build_messages("Netxia", "whatsapp", history, "quiero cotizar")

        assert messages[0]["role"] == "system"
        assert messages[1] == history[0]
        assert messages[2] == history[1]
        assert messages[-1]["role"] == "user"
        assert "quiero cotizar" in messages[-1]["content"]

    def test_empty_history_still_produces_valid_messages(self):
        messages = build_messages("Netxia", "voice", [], "primera consulta")
        assert len(messages) == 2  # system + user
