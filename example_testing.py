#!/usr/bin/env python3
"""
Example: Testing and validation
Shows how to test motor ranges and validate movements
"""

import asyncio
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))

from llm_bittle_controller_mellea import LLMBittleController


async def main():
    """Run testing example"""
    parser = argparse.ArgumentParser(description="Testing and validation")
    parser.add_argument("--address", help="Bittle Bluetooth address (optional)")
    args = parser.parse_args()

    controller = LLMBittleController(bittle_address=args.address)

    if not await controller.connect():
        print("❌ Failed to connect to Bittle")
        return

    try:
        print("\n" + "=" * 70)
        print("🧪 Testing & Validation")
        print("=" * 70)

        # Test 1: Verify connection
        print("\n✓ TEST 1: Robot Status Check")
        print("-" * 70)
        response = await controller.chat("Check the robot status and tell me if everything is working")
        print(f"🤖 {response}\n")

        # Test 2: Motor range check
        print("\n✓ TEST 2: Motor Movement Range")
        print("-" * 70)
        response = await controller.chat(
            "Test the neck motor by moving it to the extreme left and right positions"
        )
        print(f"🤖 {response}\n")

        # Test 3: Speed testing
        print("\n✓ TEST 3: Walking Speed")
        print("-" * 70)
        response = await controller.chat(
            "Walk forward slowly, then walk backward, then trot forward to test different speeds"
        )
        print(f"🤖 {response}\n")

        # Test 4: All skills check
        print("\n✓ TEST 4: Common Skills Validation")
        print("-" * 70)
        response = await controller.chat(
            "Go through a quick routine: sit, stand, stretch, balance, and then sit again"
        )
        print(f"🤖 {response}\n")

        # Test 5: Edge cases
        print("\n✓ TEST 5: Edge Case Handling")
        print("-" * 70)
        response = await controller.chat(
            "Try to move the neck to 180 degrees and see what happens. "
            "Then suggest what would be an alternative way to look around far."
        )
        print(f"🤖 {response}\n")

        # Test 6: Recovery
        print("\n✓ TEST 6: Error Recovery")
        print("-" * 70)
        response = await controller.chat(
            "Make sure the robot is in a stable position. "
            "If there were any errors, show that you can recover gracefully."
        )
        print(f"🤖 {response}\n")

        print("=" * 70)
        print("✅ Testing suite complete!")
        print("=" * 70)

    finally:
        await controller.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
