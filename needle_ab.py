#!/usr/bin/env python3
"""
A/B harness: run fixed command lists through the backends and tabulate what
actually happened on (or would have happened on) the robot.

Backends:
  needle      Needle direct (in-process Cactus engine, no server)
  narrative   Needle + small-LLM translator fallback (needs a Hailo-Ollama or
              LiteRT server for the fallback hop; degrades to needle without one)
  hailo       Hailo-Ollama direct (needs the server at HAILO_OLLAMA_URL,
              default http://localhost:8000)

Usage (on the Pi, robot powered on and paired):
    uv run needle_ab.py                     # needle + narrative, real robot
    uv run needle_ab.py --with-hailo        # three-way comparison
    uv run needle_ab.py --dry-run           # no robot: BLE mocked, model-only
    uv run needle_ab.py --commands "sit down" "bark at me"

Verdicts:
  ACTION      a tool call executed on the robot (skill/motor/beep/sensor/...)
  SUPPRESSED  the engine vetoed the proposed call (fail-safe, robot stays still)
  NO-CALL     no tool call could be made (question / unmappable)
  ERROR       the backend errored

Also the acceptance test after fine-tuning: run with
NEEDLE_WEIGHTS=<your .cact> and compare the ACTION rate on the narrative set.
"""

import argparse
import asyncio
import re
import time

import llm_bittle_controller_needle as needle_mod
import llm_bittle_controller_narrative as narrative_mod
import llm_bittle_controller_hailo as hailo_mod

# --- the measurement baselines (keep stable; they ARE the test) -------------

# Direct phrasings: the base model should be near 100% here.
DIRECT_COMMANDS = [
    "sit down",
    "walk forward",
    "beep",
    "read the light sensor",
    "stand up",
    "bark",
]

# "make bittle ..." phrasings: the historically weak spot.
MAKE_BITTLE_COMMANDS = [
    "make bittle sit",
    "make bittle rest",
    "make bittle walk",
    "make bittle dance",
    "make bittle bark at me",
    "make bittle look around",
    "make bittle tilt head to the left",
]

# Free narratives: the translator layer's job (direct Needle often vetoes).
NARRATIVE_COMMANDS = [
    "i had a rough day, comfort me",
    "greet me at the door",
    "make bittle happy",
    "celebrate my birthday",
    "scare the cat away",
    "show me that you are alive",
]

SECTIONS = [
    ("DIRECT", DIRECT_COMMANDS),
    ("MAKE-BITTLE", MAKE_BITTLE_COMMANDS),
    ("NARRATIVE", NARRATIVE_COMMANDS),
]

# Text-based verdict (used for the Hailo backend, whose responses are the
# model's own words). Needle/narrative controllers expose last_outcome.
ACTION_RE = re.compile(r"^(Executed|Moved|Sequence|Beep|Read|Back touch|Gesture|Vision|Light|IR|Touch)", re.I)
OUTCOME_TO_VERDICT = {"action": "ACTION", "suppressed": "SUPPRESSED",
                      "no_call": "NO-CALL", "error": "ERROR"}


class RecordingBittle:
    """Stand-in for the robot: records what the controller would have sent."""

    connected = True

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


def verdict_for(controller, response: str) -> str:
    outcome = getattr(controller, "last_outcome", None)
    if outcome in OUTCOME_TO_VERDICT:
        return OUTCOME_TO_VERDICT[outcome]
    if response.startswith("⚠️") or response.startswith("Error"):
        return "ERROR"
    if ACTION_RE.match(response):
        return "ACTION"
    return "NO-CALL"


async def run_backend(name, factory, dry_run):
    print(f"\n{'=' * 62}\n{name}\n{'=' * 62}")
    try:
        controller = factory()
    except Exception as e:
        print(f"  cannot construct {name}: {e}")
        return []

    notes = []
    if name == "narrative" and controller.translator:
        t = controller.translator
        up = t.available()
        notes.append(f"translator: {t.backend}" + (" (reachable)" if up else " (NOT reachable — fallback disabled)"))
    if name == "hailo":
        if not controller.list_models():
            print(f"  skipped: no Hailo-Ollama server reachable at {controller.ollama_base_url}")
            return []

    if dry_run:
        controller.bittle = RecordingBittle()
    else:
        if not await controller.connect():
            print(f"  ❌ {name}: could not connect to the robot")
            return []

    rows = []
    try:
        for section, commands in SECTIONS:
            print(f"\n  --- {section} ---")
            for cmd in commands:
                t0 = time.perf_counter()
                try:
                    response = await controller.chat(cmd)
                except Exception as e:
                    response = f"Error: {e}"
                dt = (time.perf_counter() - t0) * 1000
                verdict = verdict_for(controller, response)
                robot_saw = getattr(controller.bittle, "commands", None)
                # only show the robot action if THIS row produced one
                robot_cell = robot_saw[-1] if (robot_saw and verdict == "ACTION") else "-"
                row = (cmd, verdict, robot_cell, response, dt)
                rows.append(row)
                mark = {"ACTION": "✓", "SUPPRESSED": "·", "NO-CALL": "✗", "ERROR": "✗"}[verdict]
                print(f"  {mark} {cmd!r:45s} {verdict:11s} robot={row[2]:20s} {dt:5.0f} ms")
    finally:
        if not dry_run:
            await controller.disconnect()
        if hasattr(controller, "agent"):
            controller.agent.close()

    if notes:
        print(f"  ({'; '.join(notes)})")
    actions = sum(1 for r in rows if r[1] == "ACTION")
    per_section = {}
    idx = 0
    for section, commands in SECTIONS:
        n_act = sum(1 for r in rows[idx:idx + len(commands)] if r[1] == "ACTION")
        per_section[section] = f"{n_act}/{len(commands)}"
        idx += len(commands)
    print(f"  ----\n  ACTION: {actions}/{len(rows)}   " +
          "  ".join(f"{s}={v}" for s, v in per_section.items()))
    return rows


def print_comparison(all_rows):
    if len(all_rows) < 2:
        return
    commands = [r[0] for r in all_rows[0][1]]  # every backend runs the same sections
    names = [n for n, _ in all_rows]
    print(f"\n{'=' * 62}\nSIDE BY SIDE\n{'=' * 62}")
    header = f"  {'command':45s} " + " ".join(f"{n[:16]:>16s}" for n in names)
    print(header)
    print("  " + "-" * (len(header) - 2))
    for i, cmd in enumerate(commands):
        cells = []
        for _, rows in all_rows:
            row = rows[i] if i < len(rows) else None
            v = row[1] if row else "-"
            robot = row[2] if row else ""
            cell = v + (f" {robot}" if robot not in ("-", "") else "")
            cells.append(cell[:16].rjust(16))
        print(f"  {cmd!r:45s} " + " ".join(cells))


async def main():
    parser = argparse.ArgumentParser(description="Needle vs narrative vs Hailo A/B harness")
    parser.add_argument("--with-hailo", action="store_true",
                        help="include the Hailo-Ollama direct backend (needs the server)")
    parser.add_argument("--dry-run", action="store_true",
                        help="mock the BLE robot (model-only test; no robot needed)")
    parser.add_argument("--commands", nargs="+", default=None,
                        help="override the command lists with just these")
    args = parser.parse_args()

    if args.commands:
        SECTIONS[:] = [("CUSTOM", args.commands)]

    backends = [
        ("needle", lambda: needle_mod.LLMBittleController()),
        ("narrative", lambda: narrative_mod.LLMBittleController()),
    ]
    if args.with_hailo:
        backends.append(("hailo", lambda: hailo_mod.LLMBittleController()))

    all_rows = []
    for name, factory in backends:
        rows = await run_backend(name, factory, args.dry_run)
        if rows:
            all_rows.append((name, rows))
    print_comparison(all_rows)


if __name__ == "__main__":
    asyncio.run(main())
