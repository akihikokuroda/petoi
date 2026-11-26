#!/usr/bin/env python3
"""
A/B harness: run one fixed command list through one or more backends and
tabulate what actually happened on (or would have happened on) the robot.

Backends:
  needle   llm_bittle_controller_needle  (in-process Cactus engine, no server)
  hailo    llm_bittle_controller_hailo   (needs hailo-ollama at HAILO_OLLAMA_URL,
                                          default http://localhost:8000)

Usage (on the Pi, with the robot powered on and paired):
    uv run needle_ab.py                    # Needle only, real robot
    uv run needle_ab.py --with-hailo       # Needle + Hailo-Ollama, real robot
    uv run needle_ab.py --dry-run          # no robot: BLE mocked, model-only
    uv run needle_ab.py --commands "sit down" "bark at me"

Verdicts:
  ACTION      a tool call executed on the robot (skill/motor/beep/sensor/...)
  SUPPRESSED  the model proposed a call but the engine vetoed it (fail-safe)
  NO-CALL     the model produced no tool call at all
  ERROR       the backend errored

Also doubles as the acceptance test after fine-tuning: run the same list
with NEEDLE_WEIGHTS=<your .cact> and compare the ACTION rate.
"""

import argparse
import asyncio
import json
import re
import sys
import time

import llm_bittle_controller_needle as needle_mod
import llm_bittle_controller_hailo as hailo_mod

# The phrasings the base model flickers on, plus the direct ones it should
# always get. Keep this list stable: it is the measurement baseline.
DEFAULT_COMMANDS = [
    "make bittle sit",
    "make bittle rest",
    "make bittle walk",
    "make bittle dance",
    "make bittle bark at me",
    "make bittle look around",
    "make bittle tilt head to the left",
    "sit down",
    "walk forward",
    "beep",
    "read the light sensor",
    "how bright is it on your right side?",
]

# Verdict classification on the synthesized confirmation text.
ACTION_RE = re.compile(r"^(Executed|Moved|Sequence|Beep|Read|Back touch|IMU|Gesture|Vision|Light|IR|Touch)", re.I)


class RecordingBittle:
    """Stand-in for the robot: records what the controller would have sent."""

    connected = True
    commands = None

    def __init__(self):
        self.commands = []

    async def execute_skill(self, name):
        self.commands.append(f"skill:{name}")
        return True

    async def execute_motor(self, index, angle, *a):
        self.commands.append(f"motor:{index}->{angle}")
        return True

    async def send_command(self, cmd):
        self.commands.append(f"cmd:{cmd}")
        return True

    async def read_light_sensor(self, **kw):
        class R:
            def to_dict(self):
                return {"value": 512}
        return R()

    async def read_light_sensors(self):
        class R:
            def to_dict(self):
                return {"value": 512}
        return {"L": R(), "R": R()}


def classify(response: str) -> str:
    if response.startswith("⚠️") or response.startswith("Error"):
        return "ERROR"
    if response.startswith("I'm not sure"):
        return "SUPPRESSED"
    if ACTION_RE.match(response):
        return "ACTION"
    return "NO-CALL"


async def run_backend(name, controller_factory, commands, dry_run):
    print(f"\n{'=' * 62}\n{name}\n{'=' * 62}")
    rows = []
    try:
        controller = controller_factory()
    except Exception as e:
        print(f"  cannot construct {name}: {e}")
        return rows
    if dry_run:
        controller.bittle = RecordingBittle()
    else:
        if not await controller.connect():
            print(f"  ❌ {name}: could not connect to the robot")
            return rows
    try:
        for cmd in commands:
            t0 = time.perf_counter()
            try:
                response = await controller.chat(cmd)
            except Exception as e:
                response = f"Error: {e}"
            dt = (time.perf_counter() - t0) * 1000
            verdict = classify(response)
            robot_saw = getattr(controller.bittle, "commands", None)
            row = (cmd, verdict, (robot_saw[-1] if robot_saw else "-"), response, dt)
            rows.append(row)
            mark = {"ACTION": "✓", "SUPPRESSED": "·", "NO-CALL": "✗", "ERROR": "✗"}[verdict]
            print(f"  {mark} {cmd!r:40s} {verdict:11s} robot={row[2]:22s} {dt:5.0f} ms")
    finally:
        if not dry_run:
            await controller.disconnect()
        if hasattr(controller, "agent"):
            controller.agent.close()

    actions = sum(1 for r in rows if r[1] == "ACTION")
    print(f"  ----\n  ACTION rate: {actions}/{len(rows)}"
          + (f", SUPPRESSED: {sum(1 for r in rows if r[1] == 'SUPPRESSED')}"
             if any(r[1] == "SUPPRESSED" for r in rows) else ""))
    return rows


def print_comparison(all_rows):
    """Cross-backend table: same command, side by side."""
    if len(all_rows) < 2:
        return
    commands = all_rows[0][0]
    names = [n for n, _ in all_rows]
    print(f"\n{'=' * 62}\nSIDE BY SIDE\n{'=' * 62}")
    header = f"  {'command':40s} " + " ".join(f"{n[:18]:>18s}" for n in names)
    print(header)
    print("  " + "-" * (len(header) - 2))
    for i, cmd in enumerate(commands):
        cells = []
        for _, rows in all_rows:
            row = rows[i] if i < len(rows) else None
            v = row[1] if row else "-"
            robot = row[2] if row else ""
            cells.append((v + (f" {robot}" if robot != "-" else ""))[:18].rjust(18))
        print(f"  {cmd!r:40s} " + " ".join(cells))


async def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--with-hailo", action="store_true",
                        help="also run the Hailo-Ollama backend (http://localhost:8000 by default)")
    parser.add_argument("--dry-run", action="store_true",
                        help="mock the BLE robot (model-only test; no robot needed)")
    parser.add_argument("--commands", nargs="+", default=None,
                        help="override the default command list")
    args = parser.parse_args()
    commands = args.commands or DEFAULT_COMMANDS

    backends = [("needle", lambda: needle_mod.LLMBittleController())]
    if args.with_hailo:
        backends.append(("hailo", lambda: hailo_mod.LLMBittleController()))

    all_rows = []
    for name, factory in backends:
        rows = await run_backend(name, factory, commands, args.dry_run)
        if rows:
            all_rows.append((name, rows))
    print_comparison(all_rows)


if __name__ == "__main__":
    asyncio.run(main())
