#!/usr/bin/env python3
"""
Example: Make Bittle dance with LLM control
Demonstrates complex motion sequencing
"""

import asyncio
import sys
import os
import argparse
import logging

sys.path.insert(0, os.path.dirname(__file__))

from llm_bittle_controller_mellea import LLMBittleController

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Run dance example"""
    parser = argparse.ArgumentParser(description="Make Bittle dance")
    parser.add_argument("--address", help="Bittle Bluetooth address (optional)")
    args = parser.parse_args()

    controller = LLMBittleController(bittle_address=args.address)

    if not await controller.connect():
        print("❌ Failed to connect to Bittle")
        return

    try:
        print("\n🎵 Making Bittle dance...\n")

        user_message = "Make Bittle dance! Do something fun and energetic."
        logger.debug(f"📤 Sending to LLM: {user_message}")
        print(f"📤 Sending to LLM: {user_message}")

        response = await controller.chat(user_message)

        logger.debug(f"📥 Received from LLM: {response}")
        print(f"🤖 Response: {response}\n")

    finally:
        await controller.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
