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

# Skill arrays
sit = [
1, 0, -30, 1,
    0,   0, -45,   0,  -5,  -5,  20,  20,  45,  45, 105, 105,  45,  45, -45, -45]

ts = [-2, 0, 0, 1,
 0, 1, 2,
   30,  30,  30,  30,  30,  30,  30,  30,  30,  30,  30,  30,  30,  30,  30,  30,    32, 0, 0, 0,
   75,  75,  75,  75,  75,  75,  75,  75,  75,  75,  75,  75, -55, -55, -55, -55,    32, 0, 0, 0,]

ck = [
    -3, 0, 5, 1,
    0, 1, 2,
    45,   0,   0,   0,   0,   0,   0,   0,  45,  35,  38,  50, -30, -10,   0, -20,     6, 1, 0, 0,
   -45,   0,   0,   0,   0,   0,   0,   0,  35,  45,  50,  38, -10, -30, -20,   0,     6, 1, 0, 0,
     0,   0,   0,   0,   0,   0,   0,   0,  30,  30,  30,  30,  30,  30,  30,  30,     5, 0, 0, 0,
]

pu = [
-9, 0, -15, 1,
 6, 7, 3,
    0,   0,   0,   0,   0,   0,   0,   0,  30,  30,  30,  30,  30,  30,  30,  30,     5, 0, 0, 0,
   15,   0,   0,   0,   0,   0,   0,   0,  30,  35,  40,  29,  50,  15,  15,  15,     5, 0, 0, 0,
   30,   0,   0,   0,   0,   0,   0,   0,  27,  35,  40,  60,  50,  15,  20,  45,     5, 0, 0, 0,
   15,   0,   0,   0,   0,   0,   0,   0,  45,  35,  40,  60,  25,  20,  20,  60,     5, 0, 0, 0,
    0,   0,   0,   0,   0,   0,   0,   0,  50,  35,  75,  60,  20,  30,  20,  60,     6, 0, 0, 0,
  -15,   0,   0,   0,   0,   0,   0,   0,  60,  60,  70,  70,  15,  15,  60,  60,     6, 0, 0, 0,
    0,   0,   0,   0,   0,   0,   0,   0,  30,  30,  95,  95,  60,  60,  60,  60,     6, 1, 0, 0,
   30,   0,   0,   0,   0,   0,   0,   0,  75,  70,  80,  80, -50, -50,  60,  60,     8, 0, 0, 0,
    0,   0,   0,   0,   0,   0,   0,   0,  30,  30,  30,  30,  30,  30,  30,  30,     5, 0, 0, 0,
   ]

vt = [
21, 0, 0, 1,
  57,  43,  60,  47, -18,   7, -17,   7,
  50,  43,  53,  47,  -5,   7,  -5,   7,
  43,  43,  47,  47,   7,   7,   7,   7,
  43,  43,  47,  47,   7,   7,   7,   7,
  43,  43,  47,  47,   7,   7,   7,   7,
  43,  47,  47,  50,   7,   0,   7,   0,
  43,  54,  47,  58,   7, -13,   7, -13,
  43,  60,  47,  65,   7, -25,   7, -25,
  43,  66,  47,  71,   7, -35,   7, -35,
  43,  63,  47,  67,   7, -30,   7, -29,
  43,  57,  47,  60,   7, -18,   7, -17,
  43,  50,  47,  53,   7,  -5,   7,  -5,
  43,  43,  47,  47,   7,   7,   7,   7,
  43,  43,  47,  47,   7,   7,   7,   7,
  43,  43,  47,  47,   7,   7,   7,   7,
  43,  43,  47,  47,   7,   7,   7,   7,
  47,  43,  50,  47,   0,   7,   0,   7,
  54,  43,  58,  47, -13,   7, -13,   7,
  60,  43,  65,  47, -25,   7, -25,   7,
  66,  43,  71,  47, -35,   7, -35,   7,
  63,  43,  67,  47, -30,   7, -29,   7,
]

wkF = [
    54, 0, 0, 1,
   9,  49,  53,  45,  24,  20,  -2,  15,
   8,  50,  41,  46,  28,  21,  -1,  15,
  10,  51,  26,  47,  26,  22,   6,  16,
  12,  52,  23,  48,  24,  24,   9,  17,
  14,  52,  20,  49,  22,  26,  12,  18,
  16,  53,  17,  51,  21,  27,  17,  18,
  18,  53,  14,  52,  20,  29,  22,  19,
  21,  54,  11,  54,  18,  30,  27,  19,
  22,  54,  11,  54,  18,  32,  29,  20,
  25,  54,  13,  55,  16,  34,  27,  21,
  26,  54,  16,  56,  16,  37,  24,  23,
  28,  54,  18,  56,  15,  39,  23,  24,
  30,  52,  20,  57,  14,  45,  22,  26,
  32,  54,  22,  57,  14,  44,  21,  28,
  33,  58,  24,  57,  15,  36,  20,  30,
,  34,  61,  26,  57,  15,  31,  19,  32,
  36,  64,  28,  57,  14,  24,  18,  35,
  38,  66,  29,  57,  14,  20,  18,  38,
  39,  67,  31,  57,  14,  16,  17,  40,
  41,  64,  32,  56,  14,   5,  17,  43,
  42,  55,  35,  57,  14,  -1,  16,  44,
  44,  44,  37,  62,  15,  -3,  14,  35,
  45,  30,  39,  66,  15,   1,  14,  29,
  46,  21,  40,  68,  15,   5,  14,  23,
  47,  19,  42,  70,  16,   9,  14,  19,
  48,  16,  43,  70,  17,  12,  15,  17,
  49,  12,  44,  67,  18,  17,  15,   5,
  49,   9,  46,  59,  20,  24,  15,  -2,
  50,   8,  47,  47,  21,  28,  16,  -2,
  51,  10,  48,  34,  22,  26,  16,   1,
  52,  12,  49,  24,  24,  24,  17,   6,
  52,  14,  50,  21,  26,  22,  18,  10,
  53,  16,  51,  19,  27,  21,  19,  12,
  53,  18,  52,  15,  29,  20,  20,  19,
  54,  21,  54,  12,  30,  18,  19,  24,
  54,  22,  55,  12,  32,  18,  20,  27,
  54,  25,  55,  11,  34,  16,  22,  29,
  54,  26,  56,  14,  37,  16,  24,  26,
  54,  28,  56,  17,  39,  15,  25,  24,
  52,  30,  57,  18,  45,  14,  27,  23,
  54,  32,  57,  21,  44,  14,  29,  21,
  58,  33,  57,  23,  36,  15,  31,  20,
  61,  34,  57,  24,  31,  15,  33,  20,
  64,  36,  57,  26,  24,  14,  36,  19,
  66,  38,  57,  28,  20,  14,  39,  18,
  67,  39,  56,  30,  16,  14,  42,  17,
  64,  41,  56,  32,   5,  14,  45,  17,
  55,  42,  59,  33,  -1,  14,  41,  17,
  44,  44,  64,  35,  -3,  15,  33,  16,
  30,  45,  67,  38,   1,  15,  27,  14,
  21,  46,  68,  39,   5,  15,  22,  14,
  19,  47,  70,  41,   9,  16,  18,  14,
  16,  48,  69,  42,  12,  17,  11,  14,
  12,  49,  63,  44,  17,  18,   1,  15]

# RGB and Effect constants
E_RGB_ALL = 0
E_RGB_RIGHT = 1
E_RGB_LEFT = 2
E_EFFECT_BREATHING = 0
E_EFFECT_ROTATE = 1
E_EFFECT_FLASH = 2
E_EFFECT_NONE = 3

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
        for service in client.services:
            for char in service.characteristics:
                if "write" in char.properties:
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
        params_str = ','.join(map(str, params))
        return f"{command}{params_str}"
    else:
        return f"{command}{params}"

async def send_task(client, task):
    """Send a task command to Bittle X"""
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

async def sendSkillStr(client, skill, duration):
    """Send a skill command"""
    logger.info(f"Executing skill: {skill} for {duration}s")
    await send_command(client, skill, delay=0)
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

            testSchedule = [
                ['g', 0.1],
                ['kbalance', 1],
                ['m', [0, -50], 0.5],
                ['m', [8, -5, 8, 10, 8, -5, 8, 10, 8, -5, 8, 10], 1],
                ['i', [8, -15, 9, -20], 1],
                ['d', 1],
                ['c', 1],
                ['c', [0, -9], 1],
                ['a', 0],
                ['I', [8, -20, 0, 0, 9, -20, 10, 20, 11, 20, 14, 80, 15, 80], 1],
                ['I', [8, 20, 0, 40, 9, 20, 10, 50, 11, 50, 14, 60, 15, 60], 1],
                ['L', [20, 0, 0, 0, 0, 0, 0, 0, 5, 0, 45, 45, 80, 80, 36, 36], 1.5],
                ['u', 0],
                ['o', 0],
                ['b', [14,8,14,8,21,8,21,8,23,8,23,8,21,4,19,8,19,8,18,8,18,8,16,8,16,8,14,4], 0],
                ['B', [20, 4, 22, 4, 24, 4, 15, 4, 20, 4, 22, 8, 24, 1, 22, 4, 20, 4, 22, 4, 27, 4, 27,
                 4, 27, 4, 27, 2, 20, 4, 19, 4, 20, 4, 20, 4, 20, 4, 20, 4, 20, 2, 19, 4, 20, 4, 19, 4,
                20, 4, 19, 4, 17, 4, 15, 2, 15, 4, 15, 4, 17, 4, 17, 4, 17, 4, 17, 4, 17, 2, 15, 4, 12,
                 4, 15, 4, 12, 4, 15, 4, 22, 4, 20, 2, -1, 4, 15, 4, 24, 4, 24, 4, 24, 4, 25, 4, 27, 4,
                20, 4, 20, 4, 24, 4, 22, 1, 22, 1, -1, 2, 15, 4, 15, 4, 15, 2, 15, 4, 15, 4, 17, 4, 15,
                 4, 12, 4, 15, 4, -1, 4, 7, 4, 8, 4, 8, 4, 12, 2, 12, 4, 13, 4, 12, 4, 8, 4, 8, 4, 10,
                 4, 12, 1, -1, 4, 12, 4, 10, 4, 8, 4, 8, 4, 8, 2, 7, 4, -1, 4, 8, 4, 8, 4, 8, 4, 8, 4,
                3, 4, 3, 4, 12, 2, 8, 4, 8, 4, 3, 4, 13, 2, 13, 4, 13, 4, 13, 4, 5, 4, 8, 4, 8, 4, 10,
                 1, 10, 1,      20, 4, 22, 4, 24, 4, 15, 4, 20, 4, 22, 8, 24, 1, 22, 4, 20, 4, 22, 4,
                27, 4, 27, 4, 27, 4, 27, 2, 20, 4, 19, 4, 20, 4, 20, 4, 20, 4, 20, 4, 20, 2, 19, 4, 20,
                 4, 19, 4, 20, 4, 19, 4, 17, 4, 15, 2, 15, 4, 15, 4, 17, 4, 17, 4, 17, 4, 17, 4, 17, 2,
                15, 4, 12, 4, 15, 4, 12, 4, 15, 4, 22, 4, 20, 2, -1, 4, 15, 4, 24, 4, 24, 4, 24, 4, 25,
                 4, 27, 4, 20, 4, 20, 4, 24, 4, 22, 1, 22, 1, -1, 2, 15, 4, 15, 4, 15, 2, 15, 4, 15, 4,
                17, 4, 15, 4, 12, 4, 15, 4, -1, 4, 7, 4, 8, 4, 8, 4, 12, 2, 12, 4, 13, 4, 12, 4, 8, 4,
                 8, 4, 10, 4, 12, 1, -1, 4, 12, 4, 10, 4, 8, 4, 8, 4, 8, 2, 7, 4, -1, 4, 8, 4, 8, 4, 8,
                 4, 8, 4, 3, 4, 3, 4, 12, 2, 8, 4, 8, 4, 3, 4, 13, 2, 13, 4, 13, 4, 13, 4, 5, 4, 8, 4,
                8, 4, 10, 1, 10, 1], 0.0],
                ['K', ts, 1],
                ['K', wkF, 3],
                ['kbdF', 2],
                ['T', 1],
                ['g', 3],
                ['I', [0, 80, 1, 60], 0],
                ['kvtF', 2],
                ['K', sit, 1],
                ['i', 0],
                ['kck', 1],
                ['T', 2],
                ['K', vt, 2],
                ['ksit', 1],
                ['T', 2],
                ['K', sit, 1],
                ['K', ck, 1],
                ['I', [8, -140, 0, 10, 9, -140, 10, 50, 11, 50], 2],
                ['L', [-10, 0, 0, 0, 0, 0, 0, 0, -55, -55, 155, 155, 150, 150, 36, 36], 2],
                ['C', [127, 0, 0, E_RGB_ALL, E_EFFECT_NONE], 1],
                ['C', [0, 127, 0, E_RGB_RIGHT, E_EFFECT_BREATHING], 1],
                ['C', [0, 0, 127, E_RGB_LEFT, E_EFFECT_ROTATE], 1],
                ['C', [127, 127, 127, E_RGB_ALL, E_EFFECT_BREATHING], 1],
                ['d', 0],
            ]

            logger.info("Test abc")
            await sendSkillStr(client, 'khi', 3)
            await sendSkillStr(client, 'kpee', 3)

            # Execute test schedule
            for task in testSchedule:
                await send_task(client, task)

            # Balance and walking with head movement
            await send_task(client, ['kbalance', 0.5])
            await send_task(client, ['kwkF', 0])

            for i in range(3):
                for a in range(0, 180, 5):
                    await send_task(client, ['i', [0, a-90, 1, a//2-45, 2, a-90], 0.01])
                for a in range(0, 180, 5):
                    await send_task(client, ['i', [0, -(a-90), 1, -(a//2-45), 2, 90-a], 0.01])

            await send_task(client, ['i', 0])
            await send_task(client, ['kwkF', 2])

            for i in range(3):
                for a in range(0, 180, 5):
                    await send_task(client, ['I', [0, a-90, 1, a//2-45, 2, a-90], 0.01])
                for a in range(0, 180, 5):
                    await send_task(client, ['I', [0, -(a-90), 1, -(a//2-45), 2, 90-a], 0.01])

            await send_task(client, ['i', 2])
            await send_task(client, ['kvtF', 2])

            logger.info("finish!")

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Exception: {e}")
        raise e

if __name__ == '__main__':
    asyncio.run(main())

