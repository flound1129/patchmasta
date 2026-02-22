from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Message:
    role: str  # "user", "assistant", "system"
    content: str
    tool_calls: list[dict] = field(default_factory=list)
    tool_results: list[dict] = field(default_factory=list)


class LLMBackend(ABC):
    @abstractmethod
    def chat(
        self,
        messages: list[Message],
        system: str,
        tools: list[dict],
    ) -> Message:
        """Send messages and return the assistant response.
        May include tool_calls that the caller should execute."""
        ...


class ClaudeBackend(LLMBackend):
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514") -> None:
        import anthropic
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def chat(self, messages: list[Message], system: str, tools: list[dict]) -> Message:
        api_messages = [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]
        kwargs = {"model": self._model, "max_tokens": 4096, "system": system, "messages": api_messages}
        if tools:
            kwargs["tools"] = tools
        response = self._client.messages.create(**kwargs)
        text_parts = []
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append({"id": block.id, "name": block.name, "input": block.input})
        return Message(role="assistant", content="\n".join(text_parts), tool_calls=tool_calls)


class GroqBackend(LLMBackend):
    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile") -> None:
        import groq
        self._client = groq.Groq(api_key=api_key)
        self._model = model

    def chat(self, messages: list[Message], system: str, tools: list[dict]) -> Message:
        api_messages = [{"role": "system", "content": system}]
        api_messages += [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]
        oai_tools = [
            {"type": "function", "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t.get("parameters") or t.get("input_schema", {}),
            }}
            for t in tools
        ] if tools else None
        kwargs = {"model": self._model, "messages": api_messages, "max_tokens": 4096}
        if oai_tools:
            kwargs["tools"] = oai_tools
        response = self._client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        tool_calls = []
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                import json
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "input": json.loads(tc.function.arguments),
                })
        return Message(
            role="assistant",
            content=choice.message.content or "",
            tool_calls=tool_calls,
        )
