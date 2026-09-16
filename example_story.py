#!/usr/bin/env python3
"""
Example: Tell a story using Bittle movements
Demonstrates how LLM can choreograph actions to match narrative
"""

import asyncio
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))

from llm_bittle_controller_mellea import LLMBittleController


async def main():
    """Run story example"""
    parser = argparse.ArgumentParser(description="Tell a story using Bittle movements")
    parser.add_argument("--address", help="Bittle Bluetooth address (optional)")
    args = parser.parse_args()

    controller = LLMBittleController(bittle_address=args.address)

    if not await controller.connect():
        print("❌ Failed to connect to Bittle")
        return

    try:
        story_prompts = [
            "Bittle wakes up in the morning. Show me what that looks like.",
            "Bittle is very hungry and looks for food. Act it out!",
            "Oh no! Bittle sees a scary shadow. What does it do?",
            "The shadow turns out to be a friend. Bittle is happy to see them.",
            "Bittle and friend play together. Show me the play!",
            "It's getting late. Bittle is getting sleepy. Show the transition to sleep.",
        ]

        print("\n" + "=" * 70)
        print("📖 Telling a Story with Bittle")
        print("=" * 70)

        for i, prompt in enumerate(story_prompts, 1):
            print(f"\n📖 Scene {i}: {prompt}")
            print("-" * 70)

            response = await controller.chat(prompt)
            print(f"\n🤖 {response}")

            await asyncio.sleep(2)

        print("\n" + "=" * 70)
        print("✅ Story complete!")
        print("=" * 70)

    finally:
        await controller.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
