#!/usr/bin/python3
# -*- coding: utf-8 -*-

# Bittle X+Arm Bluetooth Controller
# Test skills of Bittle X+Arm via BLE connection
# Dependencies: pip install bleak asyncio

import asyncio
import logging
import os
from bleak import BleakClient, BleakScanner

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Skill names for Bittle X+Arm
skillNames = ["pickUpL","dropDownL","huntL","showOffL","putAwayL","throwAwayL","shootL","bdF","bk","bkArmF","bkArmLF","bkF","bkL","crArmF","crArmL","crF","crL","gpF","gpL","hlw","jpF","lftF","lftL","phF","phL","trArmF","trArmL","trF","trL","vtArmF","vtF","vtL","wkArmF","wkArmL","wkF","wkL","balance","buttUp","calib","dropped","lifted","lnd","rest","sit","str","up","zeroN","ang","bf","bx","chr","ck","clap","cmh","dg","ff","fiv","gdb","hds","hg","hi","hsk","hu","jmp","kc","knock","lpov","mw","nd","pd","pee","pu","pu1","rc","rl","scrh","snf","tbl","ts","wh","zz"]

model = 'Bittle'
BITTLE_NAME = "Bittle"  # Adjust if your device has a different name

# RGB and Effect constants
E_RGB_ALL = 0
E_RGB_RIGHT = 1
E_RGB_LEFT = 2

E_EFFECT_BREATHING = 0
E_EFFECT_ROTATE = 1
E_EFFECT_FLASH = 2
E_EFFECT_NONE = 3

# Global client for connection management
ble_client = None

async def find_bittle():
    """Scan for Bittle X device"""
    logger.info("Scanning for Bittle X+Arm...")
    devices = await BleakScanner.discover()
    for device in devices:
        if BITTLE_NAME in device.name:
            logger.info(f"Found: {device.name} ({device.address})")
            return device.address
    logger.error("Bittle X+Arm not found!")
    return None

async def send_command(client, command, delay=0.1):
    """Send command to Bittle X+Arm via BLE"""
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
                    logger.info(f"Sent command: {command}")
                    await asyncio.sleep(delay)
                    return True

        logger.error("No writable characteristic found")
        return False
    except Exception as e:
        logger.error(f"Error sending command: {e}")
        return False

async def discover_characteristics(client):
    """Discover and print available GATT characteristics"""
    logger.info("Discovering Bittle X+Arm characteristics...")
    for service in client.services:
        logger.info(f"Service: {service.uuid}")
        for char in service.characteristics:
            logger.info(f"  Characteristic: {char.uuid} - Properties: {char.properties}")

async def main():
    try:
        # Find Bittle X+Arm
        bittle_address = await find_bittle()
        if not bittle_address:
            logger.error("Could not find Bittle X+Arm device")
            return

        # Connect to Bittle X+Arm
        async with BleakClient(bittle_address) as client:
            logger.info(f"Connected to {bittle_address}")

            # Optionally discover characteristics on first run
            # await discover_characteristics(client)

            # Test all skills
            for skill in skillNames:
                command = 'k' + skill
                print([command, 1])
                await send_command(client, command, delay=1.0)

            # Final balance command
            logger.info("Sending balance command...")
            await send_command(client, 'kbalance', delay=0.5)

            logger.info("Finished all skills!")

    except Exception as e:
        logger.error(f"Exception: {e}")
        raise e

if __name__ == '__main__':
    asyncio.run(main())

