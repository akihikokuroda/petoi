#!/usr/bin/env python3
"""
Example: Creative poses and animations
Shows how to use motor control for artistic movements
"""

import asyncio
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))

from llm_bittle_controller_mellea import LLMBittleController


async def main():
    """Run creative poses example"""
    parser = argparse.ArgumentParser(description="Creative poses and animations")
    parser.add_argument("--address", help="Bittle Bluetooth address (optional)")
    args = parser.parse_args()

    controller = LLMBittleController(bittle_address=args.address)

    if not await controller.connect():
        print("❌ Failed to connect to Bittle")
        return

    try:
        creative_requests = [
            "Make Bittle do a yoga pose - downward dog position",
            "Create a pose where Bittle looks like it's thinking hard (confused/pondering)",
            "Make Bittle look like it's laughing",
            "Create a dramatic pose where Bittle looks heroic",
            "Make Bittle look like it's greeting someone",
            "Create a pose where Bittle looks surprised",
            "Make Bittle do a stretch pose",
        ]

        print("\n" + "=" * 70)
        print("🎨 Creative Poses & Animations")
        print("=" * 70)

        for request in creative_requests:
            print(f"\n📝 Request: {request}")
            print("-" * 70)

            response = await controller.chat(request)
            print(f"\n🤖 {response}\n")

            await asyncio.sleep(2)

        print("\n" + "=" * 70)
        print("✅ Creative session complete!")
        print("=" * 70)

    finally:
        await controller.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
