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

hlw = [ # customized gait that takes smaller steps adjusted for the costume
14, 0, 0, 1,
  10,  29,  51,  46,  33,  30,   4,  15,
  10,  32,  43,  48,  40,  29,   3,  16,
  15,  35,  34,  49,  35,  30,  13,  18,
  19,  44,  36,  52,  33,  17,  14,  19,
  22,  38,  39,  53,  31,  16,  14,  22,
  25,  30,  42,  61,  30,  17,  14,  11,
  28,  21,  44,  56,  30,  21,  15,   6,
  31,   8,  47,  49,  29,  40,  16,   3,
  33,  13,  48,  41,  30,  37,  17,   3,
  38,  16,  51,  33,  28,  34,  18,  17,
  42,  20,  52,  37,  16,  32,  20,  14,
  35,  23,  59,  40,  16,  31,  16,  14,
  26,  26,  59,  42,  19,  30,   8,  14,
  15,  28,  52,  45,  27,  30,   5,  15]

jump = [ # customized behavior designed with the Petoi Skill Composer
-4,   0,   0,   1,
   1,   2,   2,
   0,   0,   0,   0,   0,   0,   0,   0,  30,  30,  30,  30,  30,  30,  30,  30,   8,   0,   0,   0,
   0,   0,   0,   0,   0,   0,   0,   0,  42,  42,  42,  42,   6,   6,   6,   6,  48,   0,   0,   0,
  37,   0,   0,   0,   0,   0,   0,   0, -10, -10, -10, -10, 110, 110, 110, 110,   0,   0,   0,   0,
  26,  11, -11,   0,  11,  11, -22, -22,   6,   6,   8,   8,   8,   8,  52,  52,   0,   0,   0,   0,]

model = 'Bittle'

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

async def send_task(client, task):
    """
    Send a task command to Bittle X
    Task format: [command, parameters, duration]
    Examples:
    ['g', 0] - turn off gyroscope
    ['ksit', 1] - sit for 1 second
    ['C', [R, G, B, eye_select, effect], duration] - color/effect
    ['i', [joint_list], duration] - instant joint movement
    ['K', motion_array, duration] - play motion/skill
    ['d', duration] - delay/rest
    ['I', [joint, angle, ...], duration] - instruction
    """
    command = task[0]

    if len(task) == 1:
        # Simple command with no parameters
        await send_command(client, command, delay=0)
    elif len(task) == 2:
        params = task[1]
        duration = 0

        if isinstance(params, list):
            # Command with parameters: ['C', [...], duration]
            if len(task) > 2:
                duration = task[2]
                cmd_str = build_command_string(command, params)
            else:
                # Command with just list parameter
                cmd_str = build_command_string(command, params)
        else:
            # Simple command with single parameter (string or number)
            cmd_str = f"{command}{params}"
            duration = params if isinstance(params, (int, float)) else 0

        await send_command(client, cmd_str, delay=0)
        if duration > 0:
            await asyncio.sleep(duration)
    elif len(task) >= 3:
        # Command with parameters and duration
        command = task[0]
        params = task[1]
        duration = task[2]

        cmd_str = build_command_string(command, params)
        await send_command(client, cmd_str, delay=0)
        if duration > 0:
            await asyncio.sleep(duration)

def build_command_string(command, params):
    """Build command string from command and parameters"""
    if isinstance(params, list):
        # Convert list of parameters to comma-separated string
        params_str = ','.join(map(str, params))
        return f"{command}{params_str}"
    else:
        return f"{command}{params}"

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

            testSchedule = [# the storyline
                ['g', 0],                    # turn off the gyroscope
                ['C', [0, 50, 0, E_RGB_ALL, E_EFFECT_BREATHING], 0],# turn on green eyes
                ['ksit', 1],                # sit down for 1 second
                ['kck', 1],                  # check around then stop for 1 second
                ['C', [0, 0, 127, E_RGB_LEFT, E_EFFECT_ROTATE], 0], # turn on blue eyes and rotate
                ['kbalance', 1],            # stand up then stop for 1 second
                ['i', [0, -10, 8, 30, 12, 30], 0], # move the head and two leg joints simultaneously to look down
                ['C', [127, 0, 0, E_RGB_ALL, E_EFFECT_FLASH], 0],   # blink red eyes
                ['C', [127, 0, 0, E_RGB_ALL, E_EFFECT_FLASH], 1],   # blink red eyes
                ['K', jump, 0],               # jump
                ['K', hlw, 4],                # walk in the halloween gait for 4 seconds
                ['d', 5],                   # rest for 5 seconds and wait for the gummy bear to turn around
                ['I', [14, 0, 15, 0.5], 0],        # lean backward
                ['C', [127, 0, 0, E_RGB_ALL, E_EFFECT_FLASH], 0], # blink red eyes
                ['C', [127, 0, 0, E_RGB_ALL, E_EFFECT_FLASH], 0], # blink red eyes
                ['C', [127, 112, 0, E_RGB_ALL, E_EFFECT_FLASH], 0], # blink yellow eyes
                ['kbk', 0.5], # make the robot walk backward for 0.5 seconds
                ['kbf', 0],   # make the robot backflip
                ['ktrF', 2],  # trot forward, run upside down for 2 seconds
                ['C', [127, 0, 0, E_RGB_ALL, E_EFFECT_NONE], 0] # change eyes to red for the next round
            ]

            await asyncio.sleep(2)

            for task in testSchedule:  # execute the tasks in the testSchedule
                print(task)
                await send_task(client, task)

            logger.info("finish!")

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Exception: {e}")
        raise e

if __name__ == '__main__':
    asyncio.run(main())

