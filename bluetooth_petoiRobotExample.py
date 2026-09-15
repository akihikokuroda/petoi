#!/usr/bin/python3
# -*- coding: utf-8 -*-

# Bittle X Bluetooth Controller
# Test the API of Bittle X via BLE connection
# Dependencies: pip install bleak asyncio

import asyncio
import logging
import os
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
                    # Convert command to bytes if it's a string
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

async def sendSkillStr(client, skill, duration):
    """Send a skill command and wait for duration"""
    command = skill
    logger.info(f"Executing skill: {skill} for {duration}s")
    await send_command(client, command, delay=0.1)
    await asyncio.sleep(duration)

async def rotateJoints(client, joints_str, angle_list, duration):
    """
    Rotate joints to specified angles
    joints_str: 'M' for all joints, or specific joint indices
    angle_list: list of angles for each joint
    duration: execution time in seconds
    """
    # Format: 'm' + joint_indices + angles
    # Example: 'm0,60' rotates joint 0 to 60 degrees
    command = 'm' + joints_str + ',' + ','.join(map(str, angle_list))
    logger.info(f"Rotating joints: {command} for {duration}s")
    await send_command(client, command, delay=0.1)
    await asyncio.sleep(duration)

async def play(client, buzzer, note_sequence, duration):
    """
    Play notes on buzzer
    buzzer: 'B' for buzzer
    note_sequence: [note1, duration1, note2, duration2, ...]
    duration: execution time in seconds
    """
    # Format: 'b' + notes as comma-separated values
    # Example: 'b14,4,14,4,21,4' plays notes
    command = 'b' + ','.join(map(str, note_sequence))
    logger.info(f"Playing notes: {command} for {duration}s")
    await send_command(client, command, delay=0.1)
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

            # Execute commands
            await sendSkillStr(client, 'ksit', 3)
            await sendSkillStr(client, 'kup', 3)

            # Rotate joints - all joints (M) to 60 degrees
            await rotateJoints(client, 'M', [60], 1)

            # Play musical notes
            # Note sequence: [note1, duration1, note2, duration2, ...]
            await play(client, 'B', [14,4,14,4,21,4,21,4,23,4,23,4,21,2], 1)

            logger.info("Finished!")

    except Exception as e:
        logger.error(f"Exception: {e}")
        raise e

if __name__ == '__main__':
    asyncio.run(main())

