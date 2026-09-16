#!/usr/bin/env python3
"""
Example: Express emotions through Bittle movements
Shows how LLM interprets emotional descriptions
"""

import asyncio
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))

from llm_bittle_controller_mellea import LLMBittleController


async def demonstrate_emotion(controller, emotion: str):
    """Have Bittle express an emotion"""
    print(f"\n{'=' * 50}")
    print(f"Expressing: {emotion}")
    print("=" * 50)

    prompt = f"Make Bittle look/act {emotion}. Be creative with the movements!"
    response = await controller.chat(prompt)
    print(f"\n{response}\n")


async def main():
    """Run emotion examples"""
    parser = argparse.ArgumentParser(description="Express emotions through Bittle movements")
    parser.add_argument("--address", help="Bittle Bluetooth address (optional)")
    args = parser.parse_args()

    controller = LLMBittleController(bittle_address=args.address)

    if not await controller.connect():
        print("❌ Failed to connect to Bittle")
        return

    try:
        # First, warm up with a simple action
        print("\n🤖 Warming up Bittle...")
        await controller.chat("Stand up and get ready for a show!")

        # Now demonstrate different emotions
        emotions = [
            "confused",
            "happy",
            "tired",
            "curious",
            "playful",
            "angry",
        ]

        for emotion in emotions:
            await demonstrate_emotion(controller, emotion)
            await asyncio.sleep(1)

        print("\n✅ Emotion demonstration complete!")

    finally:
        await controller.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
