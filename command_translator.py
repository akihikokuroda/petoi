#!/usr/bin/env python3
"""
Narrative → direct-command translator for the Petoi Bittle.

A small LLM (Hailo-Ollama or LiteRT-LM — whichever server is running) reduces
a narrative request ("i had a rough day, comfort me") to ONE or TWO short
commands from a fixed vocabulary ("rest", "joy"). The output is validated
strictly: anything not in the vocabulary (or the model's "UNKNOWN") is
dropped. The resulting command(s) still go through the Needle controller, so
Needle's confidence / ungrounded-argument veto remains the final execution
authority — the translator can only *suggest*, never act.

This is deliberately the easiest possible task for a 1.7B model: pick one
label from a short list. That keeps degeneration risk (the failure mode the
Hailo variant's _looks_garbled detector guards against) near zero.

Backends (TRANSLATOR_BACKEND=hailo|litert, default hailo; the same env vars
the existing controller variants use):
  hailo   HAILO_OLLAMA_URL (default http://localhost:8000), HAILO_MODEL
  litert  LITERT_LM_URL (default http://localhost:9379), LITERT_LM_MODEL

Usage:
    from command_translator import Translator
    t = Translator()
    if t.available():
        cmd = t.translate("greet me at the door")   # "bark" | None
"""

import logging
import os
import re

try:
    import requests
except ImportError:
    print("❌ requests library not installed. Install with: pip install requests")
    raise

logger = logging.getLogger("command_translator")

# Direct commands the Needle controller executes, from the needle_ab baseline.
# "verified" = measured ACTION in testing; "assumed" = same single-skill-word
# pattern, still to be confirmed by needle_ab.
VOCABULARY = {
    # verified by needle_ab runs:
    "sit down", "stand up", "rest", "walk forward", "bark", "beep",
    "read the light sensor", "read the distance sensor",
    # assumed (same pattern, single SKILLS-enum word):
    "sleep", "stretch", "purr", "balance", "walk backward", "joy", "flip", "roll",
}

# Normalizations of what the small model is likely to emit that should map
# onto a vocabulary item. Deliberately NOT a semantic table — narrative →
# command mapping ("comfort me" → rest) is the LLM's job, not ours.
ALIASES = {
    "sit": "sit down",
    "stand": "stand up",
    "walk": "walk forward",
    "happy": "joy",
    "act happy": "joy",
    "roll over": "roll",
    "brightness": "read the light sensor",
    "light": "read the light sensor",
    "how close": "read the distance sensor",
}

MAX_COMMANDS = 2  # allow "joy, stretch" for a two-step request

SYSTEM_PROMPT = """You convert a request about a robot dog into ONE short command for the robot.
Choose from exactly this list (you may give two, comma-separated, for a two-step request):
sit down, stand up, rest, sleep, walk forward, walk backward, bark, purr, stretch, balance, joy, flip, roll, beep, read the light sensor, read the distance sensor
If the request is a question, small talk, or asks for nothing in the list, reply with exactly: UNKNOWN
Reply with only the command(s). No other words, no punctuation."""


class Translator:
    """Reduce a narrative request to 1-2 vocabulary commands, or None."""

    def __init__(self, backend: str = None):
        self.backend = (backend or os.environ.get("TRANSLATOR_BACKEND", "hailo")).lower()
        if self.backend == "hailo":
            base = os.environ.get("HAILO_OLLAMA_URL", "http://localhost:8000").rstrip("/")
            self.url = base + "/api/chat"
            self.model_url = base + "/hailo/v1/list"
            self.model = os.environ.get("HAILO_MODEL", "qwen3:1.7b")
            self.kind = "ollama"
        elif self.backend == "litert":
            base = os.environ.get("LITERT_LM_URL", "http://localhost:9379").rstrip("/")
            self.url = base + "/v1/chat/completions"
            self.model_url = base + "/v1/models"
            self.model = os.environ.get("LITERT_LM_MODEL", "")
            self.kind = "openai"
        else:
            raise ValueError(f"unknown TRANSLATOR_BACKEND: {self.backend}")

    def available(self) -> bool:
        """Cheap reachability probe of the backend's model list endpoint."""
        try:
            return requests.get(self.model_url, timeout=2).status_code == 200
        except requests.exceptions.RequestException:
            return False

    def _raw(self, narrative: str) -> str:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": narrative},
        ]
        if self.kind == "ollama":
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                # The answer is 1-2 words; a tiny budget turns any degenerate
                # run into a quick failure instead of a token-salad flood.
                "options": {"temperature": 0.2, "num_predict": 24},
                "keep_alive": 3600,
            }
        else:
            payload = {
                "model": self.model,
                "messages": messages,
                "max_tokens": 24,
                "temperature": 0.2,
            }
        response = requests.post(self.url, json=payload, timeout=60)
        response.raise_for_status()
        body = response.json()
        if self.kind == "ollama":
            return body.get("message", {}).get("content") or ""
        choices = body.get("choices") or [{}]
        return (choices[0].get("message", {}) or {}).get("content") or ""

    @staticmethod
    def _normalize(piece: str):
        """Map one model output fragment onto the vocabulary, or None."""
        p = piece.strip().strip(".!?,\"' ").lower()
        if not p or p in ("unknown", "none", "no", "no command"):
            return None
        if p in VOCABULARY:
            return p
        if p in ALIASES:
            return ALIASES[p]
        # "bark at me", "stretch your body": first word is a vocabulary item.
        first = p.split()[0]
        if first in VOCABULARY:
            return first
        if first in ALIASES:
            return ALIASES[first]
        return None

    def translate(self, narrative: str):
        """Return 1-MAX_COMMANDS vocabulary commands joined by ', ', or None."""
        try:
            raw = self._raw(narrative)
        except requests.exceptions.RequestException as e:
            logger.warning("translator backend %s unavailable: %s", self.backend, e)
            return None
        logger.debug("translator raw output: %r", raw)
        # Split on commas/semicolons and the obvious connectives a 1.7B model
        # tends to add ("bark, then stretch", "bark and purr").
        fragments = re.split(r"[,;]|\band\b|\bthen\b", raw, flags=re.IGNORECASE)
        items = [self._normalize(f) for f in fragments]
        items = [i for i in items if i][:MAX_COMMANDS]
        if not items:
            return None
        return ", ".join(items)
