"""xAI chat client for taxonomy expansion."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import httpx

from .modes import ModeSpec, cycle_mode, mode_spec, normalize_mode
from .prompt import build_system_prompt
from .tree import (
    ClarifyResult,
    ParseError,
    ParseResult,
    TreeResult,
    parse_response,
    render_tree,
    to_outline,
)

PROVIDERS: dict[str, dict[str, str]] = {
    "xai": {
        "label": "xAI",
        "env_key": "XAI_API_KEY",
        "default_model": "grok-4.5",
        "default_base_url": "https://api.x.ai/v1",
    },
    "openai": {
        "label": "OpenAI",
        "env_key": "IDEA_TREE_OPENAI_KEY",
        "fallback_env_key": "OPENAI_API_KEY",
        "key_prefix": "sk-",
        "default_model": "gpt-4o",
        "default_base_url": "https://api.openai.com/v1",
    },
}

PROVIDER_ORDER = ("xai", "openai")

DEFAULT_MODEL = os.environ.get("IDEA_TREE_MODEL", "grok-4.5")
DEFAULT_BASE_URL = os.environ.get("IDEA_TREE_BASE_URL", "https://api.x.ai/v1")
MAX_HISTORY_MESSAGES = 24


def _provider_key(prov: dict[str, str]) -> str:
    prefix = prov.get("key_prefix", "")
    for var in (prov.get("env_key"), prov.get("fallback_env_key")):
        if var:
            val = os.environ.get(var, "").strip()
            if val and (not prefix or val.startswith(prefix)):
                return val
    return ""


class BrainError(Exception):
    """Raised when the model call fails."""


@dataclass
class Brain:
    """Conversational taxonomist with rolling history and depth modes."""

    api_key: str
    model: str = DEFAULT_MODEL
    base_url: str = DEFAULT_BASE_URL
    mode: str = "moderate"
    provider: str = "xai"
    history: list[dict[str, str]] = field(default_factory=list)
    last_tree: TreeResult | None = None
    last_display: str = ""

    @classmethod
    def from_env(
        cls,
        model: str | None = None,
        mode: str | None = None,
    ) -> Brain:
        hinted = os.environ.get("IDEA_TREE_PROVIDER", "").strip().lower()
        candidates = PROVIDER_ORDER
        if hinted in PROVIDERS:
            candidates = (hinted,) + tuple(k for k in PROVIDER_ORDER if k != hinted)
        provider_key = candidates[0]
        for key in candidates:
            if _provider_key(PROVIDERS[key]):
                provider_key = key
                break
        prov = PROVIDERS[provider_key]
        api_key = _provider_key(prov)
        if not api_key:
            env_vars = []
            for k in PROVIDER_ORDER:
                p = PROVIDERS[k]
                env_vars.append(p["env_key"])
                if p.get("fallback_env_key"):
                    env_vars.append(p["fallback_env_key"])
            raise BrainError(
                "no API key found — set any of: " + ", ".join(env_vars)
            )
        env_mode = os.environ.get("IDEA_TREE_MODE", "").strip() or None
        raw = mode if mode is not None else env_mode
        try:
            resolved = normalize_mode(raw)
        except ValueError as exc:
            raise BrainError(str(exc)) from exc
        return cls(
            api_key=api_key,
            model=model or prov["default_model"],
            base_url=prov["default_base_url"],
            mode=resolved,
            provider=provider_key,
        )

    @property
    def mode_spec(self) -> ModeSpec:
        return mode_spec(self.mode)

    @property
    def system_prompt(self) -> str:
        return build_system_prompt(self.mode)

    @property
    def max_tokens(self) -> int:
        return self.mode_spec.max_tokens

    @property
    def mode_label(self) -> str:
        return self.mode_spec.label

    @property
    def provider_label(self) -> str:
        return PROVIDERS.get(self.provider, PROVIDERS["xai"])["label"]

    def cycle_provider(self, *, clear_history: bool = True) -> str | None:
        n = len(PROVIDER_ORDER)
        for offset in range(1, n + 1):
            i = (PROVIDER_ORDER.index(self.provider) + offset) % n
            candidate = PROVIDER_ORDER[i]
            prov = PROVIDERS[candidate]
            key = _provider_key(prov)
            if key:
                self.api_key = key
                self.model = prov["default_model"]
                self.base_url = prov["default_base_url"]
                self.provider = candidate
                if clear_history:
                    self.history.clear()
                return candidate
        return None

    def set_mode(self, mode: str, *, clear_history: bool = True) -> str:
        """Set taxonomy mode. Returns canonical key. Clears history by default."""
        self.mode = normalize_mode(mode)
        if clear_history:
            self.history.clear()
        return self.mode

    def cycle_mode(self, *, clear_history: bool = True) -> str:
        return self.set_mode(cycle_mode(self.mode), clear_history=clear_history)

    def _messages(self, user_text: str) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": self.system_prompt},
            *self.history,
            {"role": "user", "content": user_text},
        ]

    def _trim_history(self) -> None:
        if len(self.history) > MAX_HISTORY_MESSAGES:
            self.history = self.history[-MAX_HISTORY_MESSAGES:]

    def remember(self, user_text: str, assistant_text: str) -> None:
        self.history.append({"role": "user", "content": user_text})
        self.history.append({"role": "assistant", "content": assistant_text})
        self._trim_history()

    def clear(self) -> None:
        self.history.clear()
        self.last_tree = None
        self.last_display = ""

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _payload(self, user_text: str) -> dict[str, Any]:
        return {
            "model": self.model,
            "messages": self._messages(user_text),
            "max_tokens": self.max_tokens,
            "temperature": 0.45,
            "stream": False,
        }

    def ask(self, user_text: str) -> ParseResult:
        """Complete a taxonomy turn (non-streaming for reliable trees)."""
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    url,
                    headers=self._headers(),
                    json=self._payload(user_text),
                )
        except httpx.HTTPError as exc:
            raise BrainError(f"network error: {exc}") from exc

        if response.status_code >= 400:
            raise BrainError(_format_http_error(response.status_code, response.text))

        try:
            data = response.json()
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise BrainError("unexpected API response shape") from exc

        raw = str(text or "").strip()
        if not raw:
            raise BrainError("empty model response")

        try:
            result = parse_response(raw)
        except ParseError as exc:
            self.remember(user_text, raw)
            raise BrainError(f"parse error: {exc}") from exc

        if isinstance(result, ClarifyResult):
            stored = f"CLARIFY\n{result.question}"
            self.last_display = result.question
        else:
            stored = "TREE\n" + to_outline(result.root)
            self.last_tree = result
            self.last_display = render_tree(result.root)

        self.remember(user_text, stored)
        return result


def _format_http_error(status: int, body: str) -> str:
    snippet = body.strip().replace("\n", " ")[:200]
    if status == 401:
        return "auth failed — check your API key"
    if status == 429:
        return "rate limited — wait a moment"
    if snippet:
        return f"API {status}: {snippet}"
    return f"API error {status}"
