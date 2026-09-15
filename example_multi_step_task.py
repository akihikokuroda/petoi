#!/usr/bin/env python3
"""
Example: Multi-step complex tasks
Shows how to chain multiple operations for complex behaviors
"""

import asyncio
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))


async def main():
    """Run multi-step task example"""
    parser = argparse.ArgumentParser(description="Run multi-step complex tasks")
    parser.add_argument("--address", help="Bittle Bluetooth address (optional)")
    parser.add_argument("--ollama", action="store_true", help="Use Ollama backend instead of Claude")
    parser.add_argument("--mellea", action="store_true", help="Use Mellea framework")
    args = parser.parse_args()

    # Use Mellea implementation if requested or if Ollama is requested
    if args.mellea or args.ollama:
        try:
            from llm_bittle_controller_mellea import LLMBittleController
        except ImportError:
            print("❌ Mellea not available. Using Claude API instead.")
            from llm_bittle_controller import LLMBittleController
        controller = LLMBittleController(bittle_address=args.address, use_ollama=args.ollama)
    else:
        from llm_bittle_controller import LLMBittleController
        controller = LLMBittleController(bittle_address=args.address)

    if not await controller.connect():
        print("❌ Failed to connect to Bittle")
        return

    try:
        print("\n" + "=" * 70)
        print("⚙️  Multi-Step Complex Tasks")
        print("=" * 70)

        # Task 1: Patrol routine
        print("\n🚨 TASK 1: Patrol Routine")
        print("-" * 70)
        response = await controller.chat(
            """Bittle is a security robot doing its patrol.
            First, stand up and look around.
            Then walk forward while occasionally looking left and right.
            Finally, return to standing position and report ready."""
        )
        print(f"🤖 {response}\n")
        await asyncio.sleep(2)

        # Task 2: Obstacle avoidance
        print("\n🚧 TASK 2: Obstacle Avoidance")
        print("-" * 70)
        response = await controller.chat(
            """Bittle encounters an obstacle while walking.
            Show the reaction (stop, look down),
            then navigate around it (step left and continue),
            then resume walking."""
        )
        print(f"🤖 {response}\n")
        await asyncio.sleep(2)

        # Task 3: Greeting sequence
        print("\n👋 TASK 3: Greeting Sequence")
        print("-" * 70)
        response = await controller.chat(
            """Bittle meets a friend.
            Show excitement, then do a friendly greeting
            (maybe a bow or wave),
            then suggest playing together."""
        )
        print(f"🤖 {response}\n")
        await asyncio.sleep(2)

        # Task 4: Problem solving
        print("\n🤔 TASK 4: Problem Solving")
        print("-" * 70)
        response = await controller.chat(
            """Bittle is trying to reach something high.
            Show attempts to stretch and reach,
            then show frustration when it doesn't work,
            then show a clever solution (like standing on something)."""
        )
        print(f"🤖 {response}\n")
        await asyncio.sleep(2)

        # Task 5: Celebration
        print("\n🎉 TASK 5: Victory Celebration")
        print("-" * 70)
        response = await controller.chat(
            """Bittle just accomplished something great!
            Show celebration with happy movements,
            maybe some jumping or spinning,
            and end with a proud pose."""
        )
        print(f"🤖 {response}\n")

        print("\n" + "=" * 70)
        print("✅ All multi-step tasks completed!")
        print("=" * 70)

    finally:
        await controller.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
