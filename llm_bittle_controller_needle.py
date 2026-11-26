#!/usr/bin/env python3
"""
LLM-controlled Petoi Bittle using Cactus Compute Needle (https://cactuscompute.com/needle)
Main controller that bridges Needle tool calls to actual robot commands

Unlike the Hailo and LiteRT variants (which are HTTP clients of a local LLM
server), Needle is an in-process inference engine: `pip install cactus-compute`
and the model runs in this process on the CPU. Engine and base weights are
downloaded once (checksum-verified, cached in ~/.cache/cactus; a Linux aarch64
build is published, so a Raspberry Pi 5 works directly).

What makes this variant different (verified empirically against the SDK, not
just the marketing):

  - No server, no keep-alive, no cold model load: a decision takes ~30-120 ms
    and the whole engine uses ~120-200 MB RAM.
  - It is a tool dispatcher, NOT a chat model: it never emits free text, only
    a JSON envelope ("type": "call" with function_calls, or "respond"). The
    one-sentence confirmations you see in the terminal are therefore
    synthesized here from the tool results.
  - Built-in guardrails: tool calls with low confidence or "ungrounded"
    arguments (e.g. a motor angle the user never mentioned) are reported in
    `suppressed_calls` instead of being executed. For a robot that means a
    misread command fails safe rather than moving the wrong servo.
  - The base model is accurate on direct commands ("sit down", "beep",
    "walk forward", "read the light sensor") and conservative on fuzzy ones
    ("bark at me", "tilt your head") — it suppresses rather than guesses.
    "make bittle ..." phrasing is harder than bare verbs; this file uses a
    Needle-tuned system prompt with few-shot examples for that phrasing and
    hides bittle_get_status from the base model (it was a silent magnet for
    confused commands — see HIDDEN_TOOLS below).
  - The intended way to close the remaining accuracy gap is Cactus
    fine-tuning: set NEEDLE_WEIGHTS to the path of a fine-tuned .cact file.
    needle_ab.py in this repo A/B-tests a fixed command list across
    backends, so you can measure the effect.

Prerequisites:
  1. Python >= 3.9
  2. pip install cactus-compute
  3. (first run) network access so the engine + weights can be downloaded

Environment:
  NEEDLE_WEIGHTS           path to a fine-tuned .cact file (optional)
  NEEDLE_MAX_NEW_TOKENS    output budget per decision (default 128)
  NEEDLE_MAX_STEPS         max tool-dispatch rounds per command (default 6)
  NEEDLE_PER_COMMAND_RESET reset the engine's conversation between commands
                           (default on — the engine degrades after ~10 turns
                           without a reset, which for a robot means fresh
                           context beats stale context)
  CACTUS_TELEMETRY         set to 1 to opt in to anonymous usage counts
                           (off by default in this file)

Note: this controller reuses the robot dispatch layer (process_tool_call,
use_sensor, BittleBLEController wiring) from the Hailo variant — only the LLM
bridge differs. If you delete llm_bittle_controller_hailo.py, copy those
methods over first.
"""

import asyncio
import json
import logging
import os
import sys
import time

# Opt out of the SDK's anonymous usage telemetry before it loads; a toy robot
# should not phone home by default. Set CACTUS_TELEMETRY=1 to opt in.
os.environ.setdefault("CACTUS_TELEMETRY", "0")

try:
    import cactus
except ImportError:
    print("❌ cactus-compute not installed. Install with: pip install cactus-compute")
    sys.exit(1)

from llm_bittle_controller_hailo import LLMBittleController as _HailoBackend

logger = logging.getLogger("llm_bittle_controller_needle")


class LLMBittleController(_HailoBackend):
    """Bridge between a Needle (cactus-compute) tool-calling engine and the Bittle.

    Inherits all robot-side methods (execute_skill, control_motor, use_sensor,
    process_tool_call, ...) unchanged from the Hailo variant; only the LLM
    bridge (__init__, get_tools, chat) and the confirmations are Needle's.
    """

    def __init__(self, bittle_address=None, debug=None):
        super().__init__(bittle_address=bittle_address, debug=debug)
        weights = os.environ.get("NEEDLE_WEIGHTS") or None
        self.agent = cactus.Cactus(
            tools=self.get_tools(),
            system=self.get_system_prompt(),
            weights=weights,
        )
        # Outcome of the most recent chat() call: "action" (a tool executed),
        # "suppressed" (engine vetoed the call), "no_call" (no tool proposed),
        # or "error". Set in chat(); read by wrappers (the narrative controller)
        # and the A/B harness instead of parsing the response text.
        self.last_outcome = None
        self.max_new_tokens = int(os.environ.get("NEEDLE_MAX_NEW_TOKENS", "128"))
        self.max_steps = int(os.environ.get("NEEDLE_MAX_STEPS", "6"))
        self.reset_per_command = os.environ.get("NEEDLE_PER_COMMAND_RESET", "1").strip().lower() in (
            "1", "true", "yes", "on",
        )
        # Hailo-specific state from the parent is simply unused here
        # (ollama_url, model, keep_alive, conversation_history).

    # Tools deliberately NOT advertised to the base Needle model. Measured
    # against it: bittle_get_status is a magnet for confused commands —
    # "make bittle sit", "make bittle rest", "make bittle look around" all
    # resolved to it — and it is the one tool that "succeeds" without moving
    # the robot, so its misfires are silent. With it out of the list the same
    # commands either map to the right skill or fail safe via the engine's
    # suppression guardrail. The handler itself is inherited and still works
    # for the Hailo/LiteRT backends, which don't have this problem.
    HIDDEN_TOOLS = {"bittle_get_status"}

    def get_tools(self):
        """Needle takes flat {name, description, parameters} dicts (the same
        OpenAI-style schemas the Hailo variant wraps for the Ollama API),
        minus HIDDEN_TOOLS (see above)."""
        return [t["function"] for t in super().get_tools()
                if t["function"]["name"] not in self.HIDDEN_TOOLS]

    def get_system_prompt(self):
        """Needle-specific system prompt (the Hailo variant's stays untouched
        for A/B parity). Explicit rules plus few-shot examples lifted
        skill-picking on "make bittle ..." phrasing in testing; fine-tuning
        (NEEDLE_WEIGHTS) is the bigger lever if this is still not enough."""
        return """You control a Petoi Bittle robot and pick exactly one tool per command.

- Any motion or behavior command (sit, rest, stand, walk, dance, bark, stretch, ...) MUST use bittle_execute_skill with the closest skill name.
- Words like "bittle", "dog", or "robot" in the command name the robot itself; ignore them.
- bittle_control_motor is only for small fine adjustments of one body part; angles are -90 to +90 degrees.
- bittle_sensor is for perception: action "read" for one measurement, "activate"/"deactivate" to stream (light, distance, touch, imu, gesture, vision).
- If no tool fits the command exactly, pick the closest bittle_execute_skill.

Examples:
"make bittle sit" -> bittle_execute_skill(skill_name="sit")
"make bittle rest" -> bittle_execute_skill(skill_name="rest")
"make bittle walk" -> bittle_execute_skill(skill_name="walk_forward")
"make bittle bark at me" -> bittle_execute_skill(skill_name="bark")
"make bittle look around" -> bittle_control_motor(motor_name="neck", angle=45)
"beep" -> bittle_beep()
"how bright is it on your right side" -> bittle_sensor(action="read", sensor="light", side="R")"""

    async def connect(self) -> bool:
        """Connect to the Bittle and pre-warm the engine (first run downloads
        engine + base weights, checksum-verified; later runs hit the cache)."""
        try:
            from cactus.agent import fetch
            fetch.fetch_library()
            fetch.fetch_weights(3)
        except Exception as e:
            logger.warning("could not pre-warm Needle engine (first use will download): %s", e)
        return await self.bittle.connect()

    @staticmethod
    def _log_envelope(response: dict, wall_ms: float) -> None:
        """Log the engine's per-decision stats (the Needle counterpart of the
        Hailo variant's _log_timing)."""
        suppressed = response.get("suppressed_calls") or []
        logger.debug(
            "needle: type=%s conf=%s suppressed=%d | prefill=%s tps decode=%s tps ram=%s MB | wall=%.0f ms",
            response.get("type"),
            response.get("confidence"),
            len(suppressed),
            response.get("prefill_tps"),
            response.get("decode_tps"),
            response.get("peak_ram_mb"),
            wall_ms,
        )
        for call in suppressed:
            logger.debug("needle suppressed (not executed): %s %s",
                         call.get("name"), json.dumps(call.get("arguments") or {}))

    @staticmethod
    def _summarize(results: list) -> str:
        """Needle never emits its own confirmation text, so synthesize one
        from what actually happened on the robot."""
        ok = [r.get("message", "") for r in results if r.get("success")]
        bad = [r.get("message", "") for r in results if not r.get("success")]
        if ok and not bad:
            return " — ".join(m.rstrip(".") for m in ok) + "."
        if ok:
            return " — ".join(m.rstrip(".") for m in ok) + f". (Skipped: {'; '.join(bad)})"
        return "; ".join(bad) or "That didn't go through — try again."

    async def chat(self, user_message: str) -> str:
        """Send a command, dispatching any tool calls.

        Mirrors the SDK's own agent loop (complete → run tools → feed the
        results back as JSON → complete ...) but with this controller's async
        robot dispatch in the middle. The engine keeps its own conversation
        state; with NEEDLE_PER_COMMAND_RESET (default) we start each command
        from a clean slate.
        """
        if self.reset_per_command:
            self.agent.reset()

        t0 = time.perf_counter()
        try:
            response = self.agent.complete(user_message, max_new_tokens=self.max_new_tokens)
        except RuntimeError as e:
            logger.debug("needle complete() failed: %s", e)
            self.last_outcome = "error"
            return f"⚠️ The Needle engine failed: {e}"

        executed = []
        for _ in range(self.max_steps):
            calls = response.get("function_calls") or []
            if response.get("type") != "call" or not calls:
                break
            for call in calls:
                name = str(call.get("name", ""))
                args = call.get("arguments") or {}
                if isinstance(args, str):
                    try:
                        args = json.loads(args) if args.strip() else {}
                    except ValueError:
                        logger.debug("tool %s arguments not valid JSON: %r", name, args)
                        args = {}
                logger.debug("dispatching needle tool call: %s args=%s", name, args)
                result_json = await self.process_tool_call(name, args)
                executed.append(json.loads(result_json))
            # Feed the executed results back, exactly as the SDK's run() does.
            response = self.agent.complete(
                json.dumps(executed, default=str), max_new_tokens=self.max_new_tokens
            )

        wall_ms = (time.perf_counter() - t0) * 1000
        self._log_envelope(response, wall_ms)

        if response.get("error"):
            logger.warning("needle engine error: %s (%s)",
                           response.get("error"), response.get("error_code"))
            self.last_outcome = "action" if executed else "error"
            if executed:
                return self._summarize(executed)
            return "⚠️ The engine hit an error on that one — please try again."

        if executed:
            self.last_outcome = "action"
            return self._summarize(executed)

        suppressed = response.get("suppressed_calls") or []
        if suppressed:
            # The engine proposed a call but its confidence/ungrounded-argument
            # guardrail vetoed it. Fail safe and ask for a direct command.
            self.last_outcome = "suppressed"
            return ("I'm not sure about that one — try a direct command like "
                    "'sit down', 'walk forward', or 'beep'.")
        # No tools, no suppressed calls: a question like "what can you do?".
        self.last_outcome = "no_call"
        return ("I can sit, stand, walk, bark, stretch, read the light/distance/touch "
                "sensors, and more — tell me what to do.")

    async def interactive_chat(self):
        """Run the interactive chat loop (Needle branding)."""
        print("\n" + "=" * 70)
        print("🤖 LLM-Controlled Petoi Bittle (Cactus Needle)")
        print("=" * 70)
        print("Type your commands in natural language (e.g., 'make Bittle dance')")
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
        print("  3. First run downloads the Needle engine — is the network reachable?")
        print("  4. Check ~/.cache/cactus/ for the cached engine and weights")
        sys.exit(1)

    try:
        await controller.interactive_chat()
    finally:
        await controller.disconnect()
        controller.agent.close()
        print("Program terminated.")


if __name__ == "__main__":
    asyncio.run(main())
