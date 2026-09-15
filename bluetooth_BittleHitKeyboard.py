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

async def send_command(client, command, delay=0.0):
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
                    if delay > 0:
                        await asyncio.sleep(delay)
                    return True

        logger.error("No writable characteristic found")
        return False
    except Exception as e:
        logger.error(f"Error sending command: {e}")
        return False

def build_command_string(command, params):
    """Build command string from command and parameters"""
    if isinstance(params, list):
        # Convert list of parameters to comma-separated string
        params_str = ','.join(map(str, params))
        return f"{command}{params_str}"
    else:
        return f"{command}{params}"

async def send_task(client, task):
    """
    Send a task command to Bittle X
    Task format: [command, parameters, duration]
    Examples:
    ['g', 1] - turn off gyroscope
    ['ksit', 1] - sit for 1 second
    ['L', [...], duration] - load posture/motion
    ['K', [...], duration] - play skill/motion
    """
    if len(task) < 2:
        logger.error("Invalid task format")
        return

    command = task[0]
    params = task[1]
    duration = task[2] if len(task) > 2 else 0

    cmd_str = build_command_string(command, params)
    await send_command(client, cmd_str, delay=0)

    if duration > 0:
        await asyncio.sleep(duration)

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

            # Build the custom skill/motion
            arm = [25, 3]
            skill = []
            rows = 15

            for i in range(rows):
                skill += [rows - i * 2, 0, 0, 0, -5, -5, 20, 20,
                         arm[i % 2], arm[(i + 1) % 2], 98, 98, 54, 54, -51, -51, 24, 0, 0, 0]

            # Add header to skill
            skill = [-rows, 0, 0, 1, 0, 0, 0] + skill
            print(f"Skill length: {len(skill)}")
            print(f"Skill: {skill}")

            # Wait for connection to stabilize
            await asyncio.sleep(3)

            # Turn off gyroscope
            await send_task(client, ['g', 1])
            await asyncio.sleep(1)

            # Sit down
            await send_task(client, ['ksit', 1])

            # Load initial posture
            await send_task(client, ['L', [0, 0, -45, 0, -5, -5, 20, 20, 45, 45, 105, 105, 45, 45, -45, -45], 1])

            # Play custom skill 5 times
            for r in range(5):
                print(f"Playing skill iteration {r + 1}/5")
                await send_task(client, ['K', skill, 0])
                await asyncio.sleep(0.5)  # Small delay between repetitions

            logger.info("finish!")

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Exception: {e}")
        raise e

if __name__ == '__main__':
    asyncio.run(main())

