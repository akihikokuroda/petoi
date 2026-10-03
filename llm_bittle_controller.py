#!/usr/bin/env python3
"""
LLM-controlled Petoi Bittle using Claude API or Mellea framework
Main controller that bridges Claude/Mellea tool calls to actual robot commands
"""

import asyncio
import json
import logging
import os
import sys
import time
from typing import Optional, Any
from dataclasses import dataclass

try:
    import requests
except ImportError:
    print("❌ requests library not installed. Install with: pip install requests")
    sys.exit(1)

from petoi_bittle_controller import BittleBLEController, SKILLS, MOTOR_INDICES

logger = logging.getLogger("llm_bittle_controller")


@dataclass
class ToolResult:
    success: bool
    message: str
    data: dict = None

    def to_dict(self):
        result = {"success": self.success, "message": self.message}
        if self.data:
            result.update(self.data)
        return result


class LLMBittleController:
    """Bridge between ollama LLM and Petoi Bittle robot"""

    def __init__(self, bittle_address: Optional[str] = None, debug: Optional[bool] = None):
        self.bittle = BittleBLEController(address=bittle_address, command_delay=0.05)
        self.ollama_url = "http://localhost:11434/api/chat"
        # self.model = "granite4.2:3b"
        self.model = "qwen3.8:27b"
        self.conversation_history = []
        if debug is None:
            debug = os.environ.get("BITTLE_DEBUG", "").strip().lower() in (
                "1", "true", "yes", "on",
            )
        self.debug = debug
        self._configure_logging()

    def _configure_logging(self) -> None:
        """Set the module log level and add a handler when debug is enabled."""
        logger.setLevel(logging.DEBUG if self.debug else logging.INFO)
        if self.debug and not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
            )
            logger.addHandler(handler)

    async def connect(self) -> bool:
        """Connect to the Bittle robot"""
        return await self.bittle.connect()

    async def disconnect(self):
        """Disconnect from the Bittle robot"""
        await self.bittle.disconnect()

    def get_tools(self) -> list:
        """Return tool definitions in the format ollama's /api/chat expects."""
        tools = [
            {
                "name": "bittle_execute_skill",
                "description": "Execute a predefined skill or behavior on the Bittle robot",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "skill_name": {
                            "type": "string",
                            "description": "Name of the skill to execute",
                            "enum": list(SKILLS.keys()),
                        }
                    },
                    "required": ["skill_name"],
                },
            },
            {
                "name": "bittle_control_motor",
                "description": "Control an individual servo motor on the Bittle",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "motor_name": {
                            "type": "string",
                            "description": "Name or index of the motor",
                            "enum": [
                                "neck",
                                "left_shoulder",
                                "right_shoulder",
                                "right_hip",
                                "left_hip",
                                "left_arm",
                                "right_arm",
                                "right_ankle",
                                "left_ankle",
                            ],
                        },
                        "angle": {
                            "type": "integer",
                            "description": "Target angle in degrees (-90 to +90)",
                            "minimum": -90,
                            "maximum": 90,
                        },
                        "duration": {
                            "type": "number",
                            "description": "Time to reach target in seconds (default: 0.1)",
                            "default": 0.1,
                            "minimum": 0.01,
                        },
                    },
                    "required": ["motor_name", "angle"],
                },
            },
            {
                "name": "bittle_sequence_motion",
                "description": "Execute a sequence of movements to create custom behaviors",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sequence": {
                            "type": "array",
                            "description": "List of motion steps",
                            "items": {
                                "type": "object",
                            },
                        },
                        "repeat": {
                            "type": "integer",
                            "description": "Number of times to repeat (default: 1)",
                            "default": 1,
                            "minimum": 1,
                        },
                    },
                    "required": ["sequence"],
                },
            },
            {
                "name": "bittle_get_status",
                "description": "Query current status of the Bittle robot",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "bittle_beep",
                "description": "Make the Bittle produce a beep sound",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "frequency": {
                            "type": "integer",
                            "description": "Frequency in Hz (default: 1000)",
                            "default": 1000,
                        },
                        "duration": {
                            "type": "number",
                            "description": "Duration in milliseconds (default: 100)",
                            "default": 100,
                        },
                    },
                },
            },
            {
                "name": "bittle_calibrate_motor",
                "description": "Calibrate a specific motor to its neutral position",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "motor_name": {
                            "type": "string",
                            "description": "Motor to calibrate",
                            "enum": [
                                "neck",
                                "left_shoulder",
                                "right_shoulder",
                                "right_hip",
                                "left_hip",
                                "left_arm",
                                "right_arm",
                                "right_ankle",
                                "left_ankle",
                            ],
                        },
                        "offset": {
                            "type": "integer",
                            "description": "Calibration offset in degrees (default: 0)",
                            "default": 0,
                        },
                    },
                    "required": ["motor_name"],
                },
            },
            {
                "name": "bittle_read_light",
                "description": "Read the ambient light sensor(s). Returns a brightness/ADC value per side; side 'both' reads left and right.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "side": {
                            "type": "string",
                            "description": "Sensor to read: 'L' (left), 'R' (right), or 'both' (default)",
                            "enum": ["L", "R", "both"],
                            "default": "both",
                        }
                    },
                },
            },
            {
                "name": "bittle_read_distance",
                "description": "Read the IR distance sensor(s). Returns a raw ADC value per side (a closer object gives a lower value); side 'both' reads left and right.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "side": {
                            "type": "string",
                            "description": "Sensor to read: 'L' (left), 'R' (right), or 'both' (default)",
                            "enum": ["L", "R", "both"],
                            "default": "both",
                        }
                    },
                },
            },
            {
                "name": "bittle_read_touch",
                "description": "Read the touch pad(s). Returns 1 (touched) or 0 (not touched) per side; side 'both' reads left and right.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "side": {
                            "type": "string",
                            "description": "Pad to read: 'L' (left), 'R' (right), or 'both' (default)",
                            "enum": ["L", "R", "both"],
                            "default": "both",
                        }
                    },
                },
            },
            {
                "name": "bittle_read_back_touch",
                "description": "Read the back touch sensor. Returns which of the four pads was touched (Front Left / Front Right / Center / Back).",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "bittle_read_imu",
                "description": "Read the IMU (accelerometer and gyroscope). Returns accel_x/y/z and gyro_x/y/z, useful for balance and orientation.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "bittle_read_gesture",
                "description": "Wait for and read a hand gesture (up / down / left / right). Ask the user to wave a hand near the robot while this runs.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "timeout": {
                            "type": "number",
                            "description": "How long to wait for a gesture, in seconds (default: 5)",
                            "default": 5,
                            "minimum": 1,
                            "maximum": 10,
                        }
                    },
                },
            },
            {
                "name": "bittle_activate_light",
                "description": "Activate the light sensor mode (enables the light module on the shared sensor pins).",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "bittle_activate_distance",
                "description": "Activate the IR distance sensor mode (enables the distance module on the shared sensor pins).",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "bittle_activate_touch",
                "description": "Activate the touch sensor mode (enables the touch module on the shared sensor pins).",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "bittle_activate_back_touch",
                "description": "Activate the back touch sensor mode (enables the 4-pad back touch module).",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "bittle_activate_gesture",
                "description": "Activate the gesture sensor and start the continuous value stream. Optionally let the dog react (sit/scratch/head turn) to each gesture.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reactions": {
                            "type": "boolean",
                            "description": "Whether the robot should react to gestures (default: false, stays still)",
                            "default": False,
                        }
                    },
                },
            },
            {
                "name": "bittle_deactivate_light",
                "description": "Deactivate the light sensor mode (turns the light module off on the shared sensor pins).",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "bittle_deactivate_distance",
                "description": "Deactivate the IR distance sensor mode (turns the distance module off).",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "bittle_deactivate_touch",
                "description": "Deactivate the touch sensor mode (turns the touch module off).",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "bittle_deactivate_back_touch",
                "description": "Deactivate the back touch sensor mode (turns the 4-pad back touch module off).",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "bittle_deactivate_gesture",
                "description": "Deactivate the gesture sensor and stop the continuous value stream.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
        ]
        return [{"type": "function", "function": t} for t in tools]

    async def execute_skill(self, skill_name: str) -> ToolResult:
        """Execute a predefined skill"""
        if skill_name not in SKILLS:
            return ToolResult(
                success=False, message=f"Unknown skill: {skill_name}"
            )

        success = await self.bittle.execute_skill(skill_name)
        return ToolResult(
            success=success,
            message=f"Executed skill: {skill_name}",
            data={"skill": skill_name},
        )

    async def control_motor(
        self, motor_name: str, angle: int, duration: float = 0.1
    ) -> ToolResult:
        """Control an individual motor"""
        motor_map = {
            "neck": 0,
            "left_shoulder": 8,
            "right_shoulder": 9,
            "right_hip": 10,
            "left_hip": 11,
            "left_arm": 12,
            "right_arm": 13,
            "right_ankle": 14,
            "left_ankle": 15,
        }

        if motor_name not in motor_map:
            return ToolResult(
                success=False, message=f"Unknown motor: {motor_name}"
            )

        motor_index = motor_map[motor_name]
        success = await self.bittle.execute_motor(motor_index, angle)

        return ToolResult(
            success=success,
            message=f"Moved {motor_name} to {angle}°",
            data={"motor": motor_name, "angle": angle},
        )

    async def sequence_motion(self, sequence: list, repeat: int = 1) -> ToolResult:
        """Execute a sequence of motions"""
        try:
            for _ in range(repeat):
                for step in sequence:
                    if "skill" in step:
                        await self.execute_skill(step["skill"])
                        if "duration" in step:
                            await asyncio.sleep(step["duration"])
                    elif "motor" in step and "angle" in step:
                        await self.control_motor(
                            step["motor"],
                            step["angle"],
                            step.get("duration", 0.1),
                        )
                        if "duration" in step:
                            await asyncio.sleep(step["duration"])

            return ToolResult(
                success=True,
                message=f"Sequence completed ({repeat} repetition(s))",
                data={"steps": len(sequence), "repetitions": repeat},
            )
        except Exception as e:
            return ToolResult(success=False, message=f"Sequence failed: {str(e)}")

    async def get_status(self) -> ToolResult:
        """Get robot status"""
        try:
            return ToolResult(
                success=True,
                message="Status retrieved",
                data={
                    "connected": self.bittle.connected,
                    "battery_voltage": "N/A",
                    "current_motion": "idle",
                    "motors_available": len(MOTOR_INDICES),
                },
            )
        except Exception as e:
            return ToolResult(success=False, message=f"Failed to get status: {e}")

    async def beep(self, frequency: int = 1000, duration: float = 100) -> ToolResult:
        """Make the robot beep"""
        try:
            cmd = f"b{int(frequency)}"
            await self.bittle.send_command(cmd)
            return ToolResult(
                success=True,
                message=f"Beep at {frequency}Hz for {duration}ms",
            )
        except Exception as e:
            return ToolResult(success=False, message=f"Beep failed: {e}")

    async def calibrate_motor(self, motor_name: str, offset: int = 0) -> ToolResult:
        """Calibrate a motor to its neutral position"""
        motor_map = {
            "neck": 0,
            "left_shoulder": 8,
            "right_shoulder": 9,
            "right_hip": 10,
            "left_hip": 11,
            "left_arm": 12,
            "right_arm": 13,
            "right_ankle": 14,
            "left_ankle": 15,
        }

        if motor_name not in motor_map:
            return ToolResult(
                success=False, message=f"Unknown motor: {motor_name}"
            )

        try:
            motor_index = motor_map[motor_name]
            success = await self.bittle.execute_motor(motor_index, offset)
            return ToolResult(
                success=success,
                message=f"Motor {motor_name} calibrated with offset {offset}°",
                data={"motor": motor_name, "offset": offset},
            )
        except Exception as e:
            return ToolResult(
                success=False, message=f"Error calibrating motor: {str(e)}"
            )

    async def read_light(self, side: str = "both") -> ToolResult:
        """Read the light sensor(s). side: 'L', 'R', or 'both'."""
        try:
            await self.bittle.activate_light_mode()
            if side and side.upper() in ("L", "R"):
                reading = await self.bittle.read_light_sensor(
                    command=self.bittle.resolve_light_command(side.upper())
                )
                if reading is None:
                    return ToolResult(
                        success=False, message=f"No response from {side} light sensor"
                    )
                return ToolResult(
                    success=True, message=f"Read {side} light sensor", data=reading.to_dict()
                )
            readings = await self.bittle.read_light_sensors()
            data = {k: (v.to_dict() if v else None) for k, v in readings.items()}
            if all(v is None for v in data.values()):
                return ToolResult(
                    success=False, message="No response from light sensors", data=data
                )
            return ToolResult(success=True, message="Read both light sensors", data=data)
        except Exception as e:
            return ToolResult(success=False, message=f"Failed to read light sensor: {e}")

    async def read_distance(self, side: str = "both") -> ToolResult:
        """Read the IR distance sensor(s). side: 'L', 'R', or 'both'."""
        try:
            await self.bittle.activate_distance_mode()
            if side and side.upper() in ("L", "R"):
                reading = await self.bittle.read_distance_sensor(side=side.upper())
                if reading is None:
                    return ToolResult(
                        success=False, message=f"No response from {side} distance sensor"
                    )
                return ToolResult(
                    success=True, message=f"Read {side} distance sensor", data=reading.to_dict()
                )
            readings = await self.bittle.read_distance_sensors()
            data = {k: (v.to_dict() if v else None) for k, v in readings.items()}
            if all(v is None for v in data.values()):
                return ToolResult(
                    success=False, message="No response from distance sensors", data=data
                )
            return ToolResult(
                success=True, message="Read both distance sensors", data=data
            )
        except Exception as e:
            return ToolResult(success=False, message=f"Failed to read distance sensor: {e}")

    async def read_touch(self, side: str = "both") -> ToolResult:
        """Read the touch pad(s). side: 'L', 'R', or 'both'."""
        try:
            await self.bittle.activate_touch_mode()
            if side and side.upper() in ("L", "R"):
                reading = await self.bittle.read_touch_sensor(side=side.upper())
                if reading is None:
                    return ToolResult(
                        success=False, message=f"No response from {side} touch pad"
                    )
                return ToolResult(
                    success=True, message=f"Read {side} touch pad", data=reading.to_dict()
                )
            readings = await self.bittle.read_touch_sensors()
            data = {k: (v.to_dict() if v else None) for k, v in readings.items()}
            if all(v is None for v in data.values()):
                return ToolResult(
                    success=False, message="No response from touch pads", data=data
                )
            return ToolResult(success=True, message="Read both touch pads", data=data)
        except Exception as e:
            return ToolResult(success=False, message=f"Failed to read touch pad: {e}")

    async def read_back_touch(self) -> ToolResult:
        """Read the back touch sensor (which pad was touched)."""
        try:
            await self.bittle.activate_back_touch_mode()
            reading = await self.bittle.read_back_touch_sensor()
            if reading is None:
                return ToolResult(
                    success=False, message="No response from back touch sensor"
                )
            return ToolResult(
                success=True, message=f"Back touch: {reading.location}", data=reading.to_dict()
            )
        except Exception as e:
            return ToolResult(success=False, message=f"Failed to read back touch sensor: {e}")

    async def read_imu(self) -> ToolResult:
        """Read the IMU (accelerometer + gyroscope)."""
        try:
            reading = await self.bittle.read_imu_sensor()
            if reading is None:
                return ToolResult(success=False, message="No IMU data received")
            return ToolResult(success=True, message="Read IMU", data=reading.to_dict())
        except Exception as e:
            return ToolResult(success=False, message=f"Failed to read IMU: {e}")

    async def read_gesture(self, timeout: float = 5.0) -> ToolResult:
        """Wait for and read one hand gesture (up / down / left / right)."""
        try:
            reading = await self.bittle.read_gesture_sensor(timeout=timeout)
            if reading is None:
                return ToolResult(
                    success=False,
                    message="No gesture detected in time — ask the user to wave a hand near the robot",
                )
            return ToolResult(
                success=True, message=f"Gesture detected: {reading.gesture}", data=reading.to_dict()
            )
        except Exception as e:
            return ToolResult(success=False, message=f"Failed to read gesture: {e}")

    async def activate_light(self) -> ToolResult:
        """Activate the light sensor mode."""
        try:
            success = await self.bittle.activate_light_mode()
            return ToolResult(
                success=success,
                message="Light sensor mode activated"
                if success
                else "Failed to activate light sensor mode",
            )
        except Exception as e:
            return ToolResult(success=False, message=f"Failed to activate light sensor mode: {e}")

    async def activate_distance(self) -> ToolResult:
        """Activate the IR distance sensor mode."""
        try:
            success = await self.bittle.activate_distance_mode()
            return ToolResult(
                success=success,
                message="IR distance sensor mode activated"
                if success
                else "Failed to activate distance sensor mode",
            )
        except Exception as e:
            return ToolResult(
                success=False, message=f"Failed to activate distance sensor mode: {e}"
            )

    async def activate_touch(self) -> ToolResult:
        """Activate the touch sensor mode."""
        try:
            success = await self.bittle.activate_touch_mode()
            return ToolResult(
                success=success,
                message="Touch sensor mode activated"
                if success
                else "Failed to activate touch sensor mode",
            )
        except Exception as e:
            return ToolResult(success=False, message=f"Failed to activate touch sensor mode: {e}")

    async def activate_back_touch(self) -> ToolResult:
        """Activate the back touch sensor mode."""
        try:
            success = await self.bittle.activate_back_touch_mode()
            return ToolResult(
                success=success,
                message="Back touch sensor mode activated"
                if success
                else "Failed to activate back touch sensor mode",
            )
        except Exception as e:
            return ToolResult(
                success=False, message=f"Failed to activate back touch sensor mode: {e}"
            )

    async def activate_gesture(self, reactions: bool = False) -> ToolResult:
        """Activate the gesture sensor and start the value stream."""
        try:
            success = await self.bittle.activate_gesture_mode(reactions=reactions)
            return ToolResult(
                success=success,
                message="Gesture sensor activated"
                if success
                else "Failed to activate gesture sensor",
            )
        except Exception as e:
            return ToolResult(success=False, message=f"Failed to activate gesture sensor: {e}")

    async def deactivate_light(self) -> ToolResult:
        """Deactivate the light sensor mode."""
        try:
            success = await self.bittle.deactivate_light_mode()
            return ToolResult(
                success=success,
                message="Light sensor mode deactivated"
                if success
                else "Failed to deactivate light sensor mode",
            )
        except Exception as e:
            return ToolResult(success=False, message=f"Failed to deactivate light sensor mode: {e}")

    async def deactivate_distance(self) -> ToolResult:
        """Deactivate the IR distance sensor mode."""
        try:
            success = await self.bittle.deactivate_distance_mode()
            return ToolResult(
                success=success,
                message="IR distance sensor mode deactivated"
                if success
                else "Failed to deactivate IR distance sensor mode",
            )
        except Exception as e:
            return ToolResult(success=False, message=f"Failed to deactivate IR distance sensor mode: {e}")

    async def deactivate_touch(self) -> ToolResult:
        """Deactivate the touch sensor mode."""
        try:
            success = await self.bittle.deactivate_touch_mode()
            return ToolResult(
                success=success,
                message="Touch sensor mode deactivated"
                if success
                else "Failed to deactivate touch sensor mode",
            )
        except Exception as e:
            return ToolResult(success=False, message=f"Failed to deactivate touch sensor mode: {e}")

    async def deactivate_back_touch(self) -> ToolResult:
        """Deactivate the back touch sensor mode."""
        try:
            success = await self.bittle.deactivate_back_touch_mode()
            return ToolResult(
                success=success,
                message="Back touch sensor mode deactivated"
                if success
                else "Failed to deactivate back touch sensor mode",
            )
        except Exception as e:
            return ToolResult(success=False, message=f"Failed to deactivate back touch sensor mode: {e}")

    async def deactivate_gesture(self) -> ToolResult:
        """Deactivate the gesture sensor and stop the value stream."""
        try:
            success = await self.bittle.deactivate_gesture_mode()
            return ToolResult(
                success=success,
                message="Gesture sensor deactivated"
                if success
                else "Failed to deactivate gesture sensor",
            )
        except Exception as e:
            return ToolResult(success=False, message=f"Failed to deactivate gesture sensor: {e}")

    async def process_tool_call(self, tool_name: str, tool_input: dict) -> str:
        """Process a tool call from Claude"""
        logger.debug("tool call: %s args=%s", tool_name, tool_input)
        start = time.perf_counter()
        if tool_name == "bittle_execute_skill":
            result = await self.execute_skill(tool_input["skill_name"])
        elif tool_name == "bittle_control_motor":
            result = await self.control_motor(
                tool_input["motor_name"],
                tool_input["angle"],
                tool_input.get("duration", 0.1),
            )
        elif tool_name == "bittle_sequence_motion":
            result = await self.sequence_motion(
                tool_input["sequence"], tool_input.get("repeat", 1)
            )
        elif tool_name == "bittle_get_status":
            result = await self.get_status()
        elif tool_name == "bittle_beep":
            result = await self.beep(
                tool_input.get("frequency", 1000),
                tool_input.get("duration", 100),
            )
        elif tool_name == "bittle_calibrate_motor":
            result = await self.calibrate_motor(
                tool_input["motor_name"],
                tool_input.get("offset", 0),
            )
        elif tool_name == "bittle_read_light":
            result = await self.read_light(tool_input.get("side", "both"))
        elif tool_name == "bittle_read_distance":
            result = await self.read_distance(tool_input.get("side", "both"))
        elif tool_name == "bittle_read_touch":
            result = await self.read_touch(tool_input.get("side", "both"))
        elif tool_name == "bittle_read_back_touch":
            result = await self.read_back_touch()
        elif tool_name == "bittle_read_imu":
            result = await self.read_imu()
        elif tool_name == "bittle_read_gesture":
            result = await self.read_gesture(tool_input.get("timeout", 5.0))
        elif tool_name == "bittle_activate_light":
            result = await self.activate_light()
        elif tool_name == "bittle_activate_distance":
            result = await self.activate_distance()
        elif tool_name == "bittle_activate_touch":
            result = await self.activate_touch()
        elif tool_name == "bittle_activate_back_touch":
            result = await self.activate_back_touch()
        elif tool_name == "bittle_activate_gesture":
            result = await self.activate_gesture(tool_input.get("reactions", False))
        elif tool_name == "bittle_deactivate_light":
            result = await self.deactivate_light()
        elif tool_name == "bittle_deactivate_distance":
            result = await self.deactivate_distance()
        elif tool_name == "bittle_deactivate_touch":
            result = await self.deactivate_touch()
        elif tool_name == "bittle_deactivate_back_touch":
            result = await self.deactivate_back_touch()
        elif tool_name == "bittle_deactivate_gesture":
            result = await self.deactivate_gesture()
        else:
            result = ToolResult(success=False, message=f"Unknown tool: {tool_name}")
            logger.debug("unknown tool requested: %s", tool_name)

        result_json = json.dumps(result.to_dict())
        logger.debug(
            "tool %s finished in %.1f ms -> success=%s result=%s",
            tool_name,
            (time.perf_counter() - start) * 1000,
            result.success,
            result_json,
        )
        return result_json

    def get_system_prompt(self) -> str:
        """Return the system prompt for Claude"""
        return """You are a helpful assistant that controls a Petoi Bittle robot. You have access to tools
that allow you to make the robot move, execute behaviors, and query its status.

## Core Capabilities

You can control the Bittle robot through the following tools:
1. Execute predefined skills (sit, stand, walk, etc.)
2. Control individual servo motors for precise movements
3. Create custom motion sequences
4. Query robot status and battery level
5. Make the robot beep for feedback
6. Calibrate motors to neutral positions
7. Read sensors to perceive the environment (light, distance, touch, IMU, gestures)

## Sensors

Use the sensor tools to react to the world around the robot:
- bittle_read_light — ambient light level on each side ('L', 'R', or 'both')
- bittle_read_distance — IR distance to nearby objects; a closer object gives a lower value
- bittle_read_touch — front touch pads; 1 = touched, 0 = not touched
- bittle_read_back_touch — which back pad was touched (Front Left / Front Right / Center / Back)
- bittle_read_imu — accelerometer + gyroscope, useful for checking balance and orientation
- bittle_read_gesture — a hand gesture (up / down / left / right); ask the user to wave a hand
  near the robot while it runs

Combine perception with action, e.g. read distance before walking to avoid collisions, read touch
to react when the robot is petted, or read the IMU to right itself if it seems unbalanced.

Each sensor can also be explicitly switched on or off with the matching bittle_activate_*
and bittle_deactivate_* tools (bittle_activate_light / bittle_deactivate_light,
bittle_activate_distance / bittle_deactivate_distance, bittle_activate_touch /
bittle_deactivate_touch, bittle_activate_back_touch / bittle_deactivate_back_touch,
bittle_activate_gesture / bittle_deactivate_gesture). The read tools already enable the
mode they need, so this is only necessary when you want to switch sensor modes yourself.

## Guidelines

- Always be cautious with motor commands to avoid damaging the robot
- Motor angles must be between -90° and +90°
- Skills are the safest way to make the robot move - use them when possible
- Use motor control for fine adjustments or creative animations
- Always check robot status before executing complex sequences
- If the user asks for impossible movements, explain why and suggest alternatives

## Natural Language Understanding

Interpret user requests creatively:
- "Look around" → Move neck left and right
- "Dance" → Combine walking and trotting motions
- "Express confusion" → Tilt neck and adjust arms
- "Get tired" → Transition from walking to sitting down

When users describe emotions or actions, break them down into robot movements that
express those concepts.

## Safety First

- Before executing new motions, check the robot is connected
- Avoid extreme angles or rapid movements that could strain servos
- Respect the robot's physical limitations
- Always provide feedback on what the robot is doing"""

    async def chat(self, user_message: str) -> str:
        """Send a message and get a response from ollama, dispatching any tool calls.

        Uses ollama's /api/chat structured tool calling: the tool schemas are
        sent in the request, the model may answer with tool_calls, we dispatch
        each to the robot, and feed the results back until it returns a final
        text answer.
        """
        self.conversation_history.append({"role": "user", "content": user_message})

        max_rounds = 10
        content = ""
        for _ in range(max_rounds):
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self.get_system_prompt()},
                    *self.conversation_history,
                ],
                "tools": self.get_tools(),
                "stream": False,
                "temperature": 0.7,
            }

            try:
                logger.debug(
                    "ollama POST %s (%d messages, %d tools)",
                    self.ollama_url,
                    len(payload["messages"]),
                    len(payload["tools"]),
                )
                response = requests.post(self.ollama_url, json=payload)
                response.raise_for_status()
                result = response.json()
            except requests.exceptions.RequestException as e:
                logger.debug("ollama request failed: %s", e)
                error_msg = f"Error communicating with ollama: {e}"
                print(f"❌ {error_msg}")
                return error_msg

            message = result.get("message", {})
            content = message.get("content") or ""
            tool_calls = message.get("tool_calls") or []
            logger.debug(
                "model response: content=%r tool_calls=%d", content, len(tool_calls)
            )

            if not tool_calls:
                self.conversation_history.append(
                    {"role": "assistant", "content": content}
                )
                return content

            # Record the assistant's tool-call turn, then dispatch each call to
            # the robot and feed the results back so the model can answer.
            self.conversation_history.append(
                {"role": "assistant", "content": content, "tool_calls": tool_calls}
            )
            for tool_call in tool_calls:
                fn = tool_call.get("function", {})
                tool_name = fn.get("name", "")
                args = fn.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args) if args.strip() else {}
                    except ValueError:
                        logger.debug(
                            "tool %s arguments not valid JSON: %r", tool_name, args
                        )
                        args = {}
                logger.debug("dispatching tool call: %s args=%s", tool_name, args)
                tool_result = await self.process_tool_call(tool_name, args)
                logger.debug("tool %s -> %s", tool_name, tool_result)
                self.conversation_history.append(
                    {"role": "tool", "content": tool_result}
                )

        # The model kept calling tools without producing a final text answer.
        logger.debug("exceeded %d tool-call rounds; returning last content", max_rounds)
        return content or "Stopped: the model kept calling tools without a final answer."

    async def interactive_chat(self):
        """Run an interactive chat loop"""
        print("\n" + "=" * 70)
        print("🤖 LLM-Controlled Petoi Bittle")
        print("=" * 70)
        print("Type your commands in natural language (e.g., 'make Bittle dance')")
        print("Type 'exit' to quit\n")

        loop = asyncio.get_event_loop()

        while True:
            try:
                user_input = await loop.run_in_executor(None, input, "You: ")
                user_input = user_input.strip()

                if not user_input:
                    continue

                if user_input.lower() in ["exit", "quit"]:
                    print("\nGoodbye! 👋")
                    break

                print("\n🤔 Processing...")
                response = await self.chat(user_input)
                print(f"\n🤖 Bittle: {response}\n")

            except KeyboardInterrupt:
                print("\n\nInterrupted by user")
                break
            except Exception as e:
                print(f"❌ Error: {e}")


async def main():
    """Main entry point"""
    bittle_address = sys.argv[1] if len(sys.argv) > 1 else None

    controller = LLMBittleController(bittle_address=bittle_address)

    if not await controller.connect():
        print("\n❌ Failed to connect to Bittle")
        print("Troubleshooting:")
        print("  1. Ensure Bittle is powered on")
        print("  2. Pair Bittle via Bluetooth settings")
        print("  3. Set ANTHROPIC_API_KEY environment variable")
        sys.exit(1)

    try:
        await controller.interactive_chat()
    finally:
        await controller.disconnect()
        print("Program terminated.")


if __name__ == "__main__":
    asyncio.run(main())
