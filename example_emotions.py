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
