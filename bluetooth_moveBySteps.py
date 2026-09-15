#!/usr/bin/python3
# -*- coding: utf-8 -*-

import asyncio
import logging
import time
from bleak import BleakClient, BleakScanner

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BITTLE_NAME = "Bittle"  # Adjust if your device has a different name

async def find_bittle():
    """Scan for Bittle X device"""
    logger.info("Scanning for Bittle X...")
    devices = await BleakScanner.discover()
    for device in devices:
        if BITTLE_NAME in device.name:
            logger.info(f"Found: {device.name} ({device.address})")
            return device.address
    logger.error("Bittle not found!")
    return None

async def send_command(client, command, delay=0.1):
    """Send command to Bittle X via BLE"""
    try:
        # Find the writable characteristic
        for service in client.services:
            for char in service.characteristics:
                if "write" in char.properties:
                    # Convert command to bytes
                    if isinstance(command, str):
                        cmd_bytes = command.encode()
                    else:
                        cmd_bytes = bytes(command)

                    await client.write_gatt_char(char, cmd_bytes)
                    logger.debug(f"Sent command: {command}")
                    await asyncio.sleep(delay)
                    return True

        logger.error("No writable characteristic found")
        return False
    except Exception as e:
        logger.error(f"Error sending command: {e}")
        return False

async def send_instruction(client, command, joints_angles, delay):
    """
    Send instruction command with joint angles
    Format: 'I' + joint_index, angle, joint_index, angle...
    Example: ['I', [12, 90, 13, 90, 14, -40, 15, -40], 1]
    """
    # Build command string: 'I12,90,13,90,14,-40,15,-40'
    angle_str = ','.join(map(str, joints_angles))
    full_command = f"{command}{angle_str}"

    print(f"Sending: {[command, joints_angles, delay]}")
    await send_command(client, full_command, delay=delay)

async def main():
    try:
        # Find Bittle X
        bittle_address = await find_bittle()
        if not bittle_address:
            logger.error("Could not find Bittle X device")
            return

        # Connect to Bittle X
        async with BleakClient(bittle_address) as client:
            logger.info(f"Connected to {bittle_address}")

            # Initial setup
            await asyncio.sleep(3)

            # Turn off gyroscope
            await send_command(client, 'g', delay=1.0)
            await asyncio.sleep(1)

            # Sit down
            await send_command(client, 'ksit', delay=1.0)

            # Move joints to initial position
            # Joints 12, 13, 14, 15 to angles 90, 90, -40, -40
            await send_instruction(client, 'I', [12, 90, 13, 90, 14, -40, 15, -40], 1.0)
            await asyncio.sleep(1)

            # Main loop - continuous joint movement
            while True:
                # Forward sweep: i from 1 to 19
                for i in range(1, 20, 1):
                    angles = [8, i - 50, 9, i - 50]
                    print([f'I{angles}', 0])
                    await send_instruction(client, 'I', angles, 0.5)

                await asyncio.sleep(1)

                # Reverse sweep: i from 18 to 0
                for i in range(18, -1, -1):
                    angles = [8, i - 50, 9, i - 50]
                    print([f'I{angles}', 0])
                    await send_instruction(client, 'I', angles, 0.5)

                await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Exception: {e}")
        raise e

if __name__ == '__main__':
    try:
        asyncio.run(main())
    finally:
        logger.info("finish!")


