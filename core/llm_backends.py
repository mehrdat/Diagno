"""Unified LLM interface for Anthropic / OpenAI / Gemini / Ollama.

Every backend exposes the same `chat(system, user, json_schema=None) -> str` method.
JSON schema is requested when given; we parse it robustly downstream.
"""
from __future__ import annotations
import json
import os
import re
from abc import ABC, abstractmethod
from typing import Optional, Callable

from dotenv import load_dotenv

load_dotenv()


# ─── helpers ───────────────────────────────────────────────────────────────
def extract_json(text: str) -> dict | list:
    """Robustly extract JSON from a possibly-noisy LLM response."""
    text = text.strip()
    # strip code fences
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Find first { ... } or [ ... ] block
    for opener, closer in [("{", "}"), ("[", "]")]:
        start = text.find(opener)
        if start == -1:
            continue
        depth = 0
        for i in range(start, len(text)):
            if text[i] == opener:
                depth += 1
            elif text[i] == closer:
                depth -= 1
                if depth == 0:
                    candidate = text[start : i + 1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        continue
    raise ValueError(f"Could not extract JSON from response:\n{text[:500]}")


# ─── base ──────────────────────────────────────────────────────────────────
class LLMBackend(ABC):
    name: str = "base"

    def __init__(self, model: str, temperature: float = 0.3, on_call: Optional[Callable] = None):
        self.model = model
        self.temperature = temperature
        self.on_call = on_call

    def _notify(self, system: str, user: str, response: str):
        if self.on_call:
            self.on_call(self.name, self.model, system, user, response)

    @abstractmethod
    def chat(self, system: str, user: str, json_mode: bool = False) -> str: ...

class AnthropicBackend(LLMBackend):
    name = "anthropic"

    def __init__(self, model: str | None = None, temperature: float = 0.1, on_call: Optional[Callable] = None):
        super().__init__(model or os.getenv("ANTHROPIC_MODEL", "claude-opus-4-7"), temperature, on_call)
        import anthropic
        self.client = anthropic.Anthropic()

    def chat(self, system: str, user: str, json_mode: bool = False) -> str:
        if json_mode:
            user = user + '\n\nReturn ONLY valid JSON, no prose, no markdown fences.'
        msg = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            temperature=self.temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        chunks = [getattr(b, "text", "") for b in msg.content if getattr(b, "type", "") == "text"]
        resp_text = "".join(chunks)
        self._notify(system, user, resp_text)
        return resp_text

# ─── openai ────────────────────────────────────────────────────────────────
class OpenAIBackend(LLMBackend):
    name = "openai"

    def __init__(self, model: str | None = None, temperature: float = 0.3,
                 base_url: Optional[str] = None, api_key: Optional[str] = None,
                 timeout: float = 300.0, on_call: Optional[Callable] = None):
        super().__init__(model or os.getenv("OPENAI_MODEL", "gpt-4.1"), temperature, on_call)
        from openai import OpenAI
        self.client = OpenAI(
            api_key=api_key or os.getenv("OPENAI_API_KEY"),
            base_url=base_url,
            timeout=timeout,
        )

    def chat(self, system: str, user: str, json_mode: bool = False) -> str:
        kwargs = {
            "model": self.model,
            "temperature": self.temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        resp = self.client.chat.completions.create(**kwargs)
        resp_text = resp.choices[0].message.content or ""
        self._notify(system, user, resp_text)
        return resp_text


# ─── gemini ────────────────────────────────────────────────────────────────
class GeminiBackend(LLMBackend):
    name = "gemini"

    def __init__(self, model: str | None = None, temperature: float = 0.3, on_call: Optional[Callable] = None):
        super().__init__(model or os.getenv("GEMINI_MODEL", "gemini-2.5-pro"), temperature, on_call)
        from google import genai
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    def chat(self, system: str, user: str, json_mode: bool = False) -> str:
        from google.genai import types
        cfg = types.GenerateContentConfig(
            system_instruction=system,
            temperature=self.temperature,
            response_mime_type="application/json" if json_mode else "text/plain",
        )
        resp = self.client.models.generate_content(
            model=self.model, contents=user, config=cfg,
        )
        resp_text = resp.text or ""
        self._notify(system, user, resp_text)
        return resp_text


# ─── ollama (via OpenAI SDK) ───────────────────────────────────────────────
class OllamaBackend(OpenAIBackend):
    name = "ollama"

    def __init__(self, model: str | None = None, temperature: float = 0.3, on_call: Optional[Callable] = None):
        super().__init__(
            model=model or os.getenv("OLLAMA_MODEL", "qwen3:1.7b"),
            temperature=temperature,
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
            api_key="ollama",
            timeout=600.0,
            on_call=on_call
        )

    def chat(self, system: str, user: str, json_mode: bool = False) -> str:
        # CRITICAL: Many Ollama models stall indefinitely when response_format={"type":"json_object"}
        # is passed via the OpenAI API. Instead, we rely solely on prompt-level hints.
        # Always pass json_mode=False to the parent OpenAI SDK call.
        if json_mode:
            user = user + '\n\nYou MUST return ONLY valid JSON. No prose, no markdown fences, no explanation. Just the JSON object.'
        return super().chat(system, user, json_mode=False)


# ─── factory ───────────────────────────────────────────────────────────────
def make_backend(kind: Optional[str] = None, **kw) -> LLMBackend:
    kind = (kind or os.getenv("LLM_BACKEND", "anthropic")).lower()
    if kind == "anthropic":
        return AnthropicBackend(**kw)
    if kind == "openai":
        return OpenAIBackend(**kw)
    if kind == "gemini":
        return GeminiBackend(**kw)
    if kind == "ollama":
        return OllamaBackend(**kw)
    raise ValueError(f"Unknown backend: {kind}")
