#!/usr/bin/env python3
"""
Example: Voice commands to control Bittle (text-based simulation)
Demonstrates natural language interpretation for quick commands
"""

import asyncio
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))


async def main():
    """Run voice command example"""
    parser = argparse.ArgumentParser(description="Voice commands to control Bittle")
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
        # Quick commands simulating voice input
        commands = [
            "Stand up",
            "Look left",
            "Look right",
            "Walk forward a few steps",
            "Trot in a circle",
            "Bow",
            "Stretch",
            "Do a little spin",
            "Sit down",
            "Sleep",
        ]

        print("\n" + "=" * 70)
        print("🎤 Voice Commands Example")
        print("=" * 70)
        print("Simulating quick voice commands to Bittle\n")

        for command in commands:
            print(f"🎤 Command: '{command}'")
            response = await controller.chat(command)
            print(f"🤖 {response}\n")
            await asyncio.sleep(0.5)

        print("✅ All commands executed!")

    finally:
        await controller.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
