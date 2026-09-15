#!/usr/bin/env python3
"""
Example: Make Bittle dance with LLM control
Demonstrates complex motion sequencing
"""

import asyncio
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))


async def main():
    """Run dance example"""
    parser = argparse.ArgumentParser(description="Make Bittle dance")
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
        print("\n🎵 Making Bittle dance...\n")

        response = await controller.chat("Make Bittle dance! Do something fun and energetic.")
        print(f"🤖 Response: {response}\n")

    finally:
        await controller.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
