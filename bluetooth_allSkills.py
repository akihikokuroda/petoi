#!/usr/bin/python3
# -*- coding: utf-8 -*-

# Bittle X Bluetooth Controller
# Test all skills of Bittle X via BLE connection
# Dependencies: pip install bleak asyncio

import asyncio
import logging
import os
from bleak import BleakClient, BleakScanner

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

model = 'Bittle'
BITTLE_NAME = "Bittle"  # Adjust if your device has a different name

# Skill list
skillList = ['kbalance','kbuttUp','kcalib','kdropped','klifted','klnd','krest','ksit','kstr','kup','kzero','kang','kbx','kchr','kck','kcmh','kdg','kfiv','kgdb','khds','khg','khi','khsk','khu','kjmp','kkc','kmw','knd','kpd','kpee','kpu','kpu1','krc','kscrh','ksnf','ktbl','kts','kwh','kzz']

# Skill name mapping
skillFullName = {skill[1:]: skill for skill in skillList}

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

async def send_command(client, command):
    """Send command to Bittle X via BLE"""
    try:
        # Find the writable characteristic
        # You may need to adjust the UUID based on your Bittle X's GATT profile
        for service in client.services:
            for char in service.characteristics:
                if "write" in char.properties:
                    await client.write_gatt_char(char, command.encode() if isinstance(command, str) else command)
                    logger.info(f"Sent command: {command}")
                    return True
        logger.error("No writable characteristic found")
        return False
    except Exception as e:
        logger.error(f"Error sending command: {e}")
        return False

async def discover_characteristics(client):
    """Discover and print available GATT characteristics"""
    logger.info("Discovering Bittle X characteristics...")
    for service in client.services:
        logger.info(f"Service: {service.uuid}")
        for char in service.characteristics:
            logger.info(f"  Characteristic: {char.uuid} - Properties: {char.properties}")

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

            # Optionally discover characteristics
            # await discover_characteristics(client)

            # Test schedule
            testSchedule = [
                ['g', 0.1],  # Turn off the gyroscope
                # ['z', 0.1],  # Toggle random behavior
            ]

            # Send initial command
            await send_command(client, 'G')
            await asyncio.sleep(0.1)

            # Execute test schedule
            for task in testSchedule:
                await send_command(client, task[0])
                await asyncio.sleep(task[1])

            # Test all skills
            for skill in skillList:
                logger.info(f'{skillFullName.get(skill[1:], "Unknown"):>15}: {skill}')
                await send_command(client, skill)
                await asyncio.sleep(0.1)

            logger.info("Finished all skills!")

    except Exception as e:
        logger.error(f"Exception: {e}")
        raise e

if __name__ == '__main__':
    asyncio.run(main())


