#!/usr/bin/env python3
"""
Narrative-command Petoi Bittle: Needle direct-first, small-LLM translator fallback.

Pipeline per command:

  1. Needle (50-120 ms) — fast and safe; exact on direct commands
     ("sit down", "walk forward", "bark").
  2. If Needle vetoes the command (suppressed) or proposes nothing:
     the Translator (Hailo 1.7B or LiteRT, 1-3 s) reduces the narrative to
     1-2 commands from a fixed vocabulary — output strictly validated.
  3. Each command goes back through Needle, so its confidence /
     ungrounded-argument veto is still the final execution authority.

Properties:
  - Direct commands never pay the LLM hop (the fast path stays ~50 ms).
  - Exactly one fallback hop — no retry loops, no LLM-Needle ping-pong.
  - If the translator backend is down, this degrades to plain Needle:
    direct commands still work, narratives get the "try a direct command"
    prompt. Nothing crashes.
  - "dance" (no such skill) becomes reachable: the translator maps it to a
    valid pair like "joy, stretch", executed in sequence.

Usage:
    uv run llm_bittle_controller_narrative.py
    TRANSLATOR_BACKEND=litert uv run llm_bittle_controller_narrative.py
    HAILO_OLLAMA_URL=http://pi:8000 TRANSLATOR_BACKEND=hailo uv run ...

needle_ab.py --narrative gives the three-way comparison (Needle direct vs
Needle+translator vs Hailo direct) on a fixed command list.
"""

import asyncio
import logging
import os
import sys

import llm_bittle_controller_needle as needle_mod
from command_translator import Translator

logger = logging.getLogger("llm_bittle_controller_narrative")


class LLMBittleController(needle_mod.LLMBittleController):
    """Needle controller with a one-hop translator fallback for narratives."""

    def __init__(self, bittle_address=None, debug=None):
        super().__init__(bittle_address=bittle_address, debug=debug)
        try:
            self.translator = Translator()
        except ValueError as e:
            logger.warning("translator disabled: %s", e)
            self.translator = None

    async def chat(self, user_message: str) -> str:
        """Needle first; if it vetoes or can't map, one translator hop."""
        direct = await super().chat(user_message)
        if self.last_outcome == "action":
            return direct
        if self.translator is None or self.last_outcome == "error":
            return direct

        translated = self.translator.translate(user_message)
        if not translated:
            # The LLM also can't map it (or its backend is down): keep the
            # honest, safe answer instead of guessing.
            return ("I heard you, but I'm not sure how to do that — try a direct "
                    "command like 'sit down', 'walk forward', or 'beep'.")

        logger.info("translator: %r -> %r", user_message, translated)
        # Execute each command through Needle (its veto still applies);
        # chat() returns a one-line summary of the executed tool result.
        results = []
        for part in [p.strip() for p in translated.split(",")]:
            response = await super().chat(part)
            if self.last_outcome == "action":
                results.append(response)
        if results:
            return " ".join(results)
        # The fallback commands were vetoed too — keep the direct answer.
        return direct

    async def interactive_chat(self):
        """Run the interactive chat loop (Needle + translator branding)."""
        translator_state = "on" if self.translator else "off"
        print("\n" + "=" * 70)
        print(f"🤖 LLM-Controlled Petoi Bittle (Needle + translator, translator {translator_state})")
        print("=" * 70)
        if self.translator:
            print(f"Translator backend: {self.translator.backend}"
                  + (" (reachable)" if self.translator.available() else " (NOT reachable — narratives will fail back to direct commands)"))
        print("Type your commands in natural language (e.g., 'make Bittle happy')")
        print("Type 'exit' to quit\n")

        loop = asyncio.get_event_loop()

        while True:
            try:
                user_input = await loop.run_in_executor(None, input, "You: ")
                user_input = user_input.strip()

                if not user_input:
                    continue

                if user_input.lower() in ["exit", "quit"]:
                    print("\nGoodbye! 👋")
                    break

                print("\n🤔 Processing...")
                response = await self.chat(user_input)
                print(f"\n🤖 Bittle: {response}\n")

            except KeyboardInterrupt:
                print("\n\nInterrupted by user")
                break
            except Exception as e:
                print(f"❌ Error: {e}")


async def main():
    """Main entry point"""
    bittle_address = sys.argv[1] if len(sys.argv) > 1 else None

    controller = LLMBittleController(bittle_address=bittle_address)

    if not await controller.connect():
        print("\n❌ Failed to connect to Bittle")
        print("Troubleshooting:")
        print("  1. Ensure Bittle is powered on")
        print("  2. Pair Bittle via Bluetooth settings")
        sys.exit(1)

    try:
        await controller.interactive_chat()
    finally:
        await controller.disconnect()
        controller.agent.close()
        print("Program terminated.")


if __name__ == "__main__":
    asyncio.run(main())
