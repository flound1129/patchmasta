from ai.llm import LLMBackend, ClaudeBackend, GroqBackend, Message

def test_message_dataclass():
    msg = Message(role="user", content="hello")
    assert msg.role == "user"
    assert msg.content == "hello"

def test_claude_backend_is_llm_backend():
    assert issubclass(ClaudeBackend, LLMBackend)

def test_groq_backend_is_llm_backend():
    assert issubclass(GroqBackend, LLMBackend)

def test_backend_has_chat_method():
    assert callable(getattr(ClaudeBackend, "chat", None))
    assert callable(getattr(GroqBackend, "chat", None))
