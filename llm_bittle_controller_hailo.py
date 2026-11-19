#!/usr/bin/env python3
"""
LLM-controlled Petoi Bittle using Hailo-Ollama (https://github.com/hailo-ai)
Main controller that bridges Hailo LLM tool calls to actual robot commands

Instead of running ollama on the CPU/GPU, this controller talks to
Hailo-Ollama — an Ollama-compatible API written in C++ on top of HailoRT,
accelerated by a Hailo-10H module.

Prerequisites:
  1. Hailo-10H module + HailoRT installed
  2. Hailo GenAI model zoo installed (https://github.com/hailo-ai/hailo_model_zoo_genai)
  3. The `hailo-ollama` server running (listens on http://localhost:8000 by default)
  4. A model pulled into the local model store, e.g.:
       curl http://localhost:8000/api/pull -H 'Content-Type: application/json' \
            -d '{ "model": "qwen3:4b", "stream": true }'
     See `curl http://localhost:8000/hailo/v1/list` for the exact model IDs
     of everything available for download.

Note: Hailo-Ollama is stateless per request — the client owns the conversation
and must resend the full message history and tools array on every call (this
code already does that). Hailo models use a 2048-token context window.
"""

import asyncio
import json
import logging
import re
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


# Map of detected-class index -> human name, for the currently deployed
# Grove Vision AI V2 YOLO model. The index order is defined by the model's
# training dataset (SenseCraft) — confirm it matches YOUR model.
GESTURE_CLASSES = {0: "rock", 1: "paper", 2: "scissors"}


class LLMBittleController:
    """Bridge between Hailo-Ollama LLM and Petoi Bittle robot"""

    def __init__(self, bittle_address: Optional[str] = None, debug: Optional[bool] = None):
        self.bittle = BittleBLEController(address=bittle_address, command_delay=0.05)
        # Hailo-Ollama server (default port 8000; set OLLAMA_HOST to change the
        # side it listens on, or HAILO_OLLAMA_URL here to point at a remote one).
        self.ollama_base_url = os.environ.get("HAILO_OLLAMA_URL", "http://localhost:8000")
        self.ollama_url = self.ollama_base_url.rstrip("/") + "/api/chat"
        self.list_url = self.ollama_base_url.rstrip("/") + "/hailo/v1/list"
        # Model IDs are confirmed with: curl http://localhost:8000/hailo/v1/list
        # LLMs suitable for Hailo-Ollama (v5.5.0 model zoo) include:
        #   Qwen2-1.5B-Instruct, Qwen2.5-1.5B-Instruct, Qwen3-1.7B-Instruct,
        #   Qwen3-4B-Instruct-2507, Llama3.2-1B-Instruct,
        #   DeepSeek-R1-Distill-Qwen-1.5B,
        #   Qwen2-1.5B-Instruct-Function-Calling-v1 (fine-tuned for tool calling)
        # Vision-language (Qwen3-VL / Qwen2-VL) and Whisper models support
        # C++/Python only — not the Ollama API.
        self.model = os.environ.get("HAILO_MODEL", "qwen3:4b")
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

    def list_models(self) -> list:
        """Return the model IDs available from the Hailo-Ollama server."""
        try:
            response = requests.get(self.list_url, timeout=5)
            response.raise_for_status()
            return response.json().get("models", [])
        except (requests.exceptions.RequestException, ValueError) as e:
            logger.debug("could not list Hailo-Ollama models: %s", e)
            return []

    async def connect(self) -> bool:
        """Connect to the Bittle robot"""
        return await self.bittle.connect()

    async def disconnect(self):
        """Disconnect from the Bittle robot"""
        await self.bittle.disconnect()

    def get_tools(self) -> list:
        """Return tool definitions in the format Hailo-Ollama's /api/chat expects."""
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
                "name": "bittle_sensor",
                "description": "Use a Bittle sensor. action 'read' takes one measurement; 'activate'/'deactivate' start/stop the continuous stream.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "description": "What to do with the sensor",
                            "enum": ["read", "activate", "deactivate"],
                        },
                        "sensor": {
                            "type": "string",
                            "description": "light=brightness, distance=IR proximity, touch=front pad, back_touch=back pad, imu=balance/orientation, gesture=hand wave, vision=Vision AI camera (target position, size, object)",
                            "enum": ["light", "distance", "touch", "back_touch", "imu", "gesture", "vision"],
                        },
                        "side": {
                            "type": "string",
                            "description": "Which side, when reading light/distance/touch (default: both)",
                            "enum": ["L", "R", "both"],
                            "default": "both",
                        },
                        "reactions": {
                            "type": "boolean",
                            "description": "For gesture/vision: let the robot react (default: false)",
                            "default": False,
                        },
                    },
                    "required": ["action", "sensor"],
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
        message = (
            f"Executed skill: {skill_name}"
            if success
            else f"Failed to execute skill: {skill_name} — the command was not sent to the robot"
        )
        return ToolResult(
            success=success,
            message=message,
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
            # await self.bittle.activate_light_mode()
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

    async def read_vision(self, timeout: float = 10.0) -> ToolResult:
        """Wait for and read one camera detection from the Vision AI camera."""
        try:
            reading = await self.bittle.read_vision_sensor(timeout=timeout)
            if reading is None:
                return ToolResult(
                    success=False,
                    message="No detection received in time — ask the user to put a face, an animal, or a clear object steadily in front of the camera",
                )
            if reading.target is not None:
                object_name = GESTURE_CLASSES.get(reading.target, f"class {reading.target}")
                object_desc = f"{object_name} (class {reading.target}, confidence {reading.score})"
            else:
                object_desc = None
            return ToolResult(
                success=True,
                message=(f"Vision target at x={reading.x}, y={reading.y}, size={reading.size}"
                         + (f", object={object_desc}" if object_desc else "")
                         + f" — {reading.position}"),
                data=reading.to_dict(),
            )
        except Exception as e:
            return ToolResult(success=False, message=f"Failed to read vision sensor: {e}")

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
                else "Failed to activate IR distance sensor mode",
            )
        except Exception as e:
            return ToolResult(
                success=False, message=f"Failed to activate IR distance sensor mode: {e}"
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
            return ToolResult(success=False, message=f"Failed to activate back touch sensor mode: {e}")

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

    async def activate_vision(self, reactions: bool = False) -> ToolResult:
        """Activate the Vision AI camera and start the detection stream."""
        try:
            success = await self.bittle.activate_vision_mode(reactions=reactions)
            if success:
                message = "Vision camera activated"
                if reactions:
                    message += " — the dog will track the target with its head"
            else:
                message = "Failed to activate vision camera"
            return ToolResult(success=success, message=message)
        except Exception as e:
            return ToolResult(success=False, message=f"Failed to activate vision camera: {e}")

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

    async def deactivate_vision(self) -> ToolResult:
        """Deactivate the Vision AI camera and stop the detection stream."""
        try:
            success = await self.bittle.deactivate_vision_mode()
            return ToolResult(
                success=success,
                message="Vision camera deactivated"
                if success
                else "Failed to deactivate vision camera",
            )
        except Exception as e:
            return ToolResult(success=False, message=f"Failed to deactivate vision camera: {e}")

    async def use_sensor(self, tool_input: dict) -> ToolResult:
        """Route a bittle_sensor call to the underlying sensor methods."""
        sensor = str(tool_input.get("sensor", "")).lower().replace("-", "_")
        action = str(tool_input.get("action", "read")).lower()
        side = tool_input.get("side", "both")
        reactions = bool(tool_input.get("reactions", False))

        if action == "read":
            readers = {
                "light": self.read_light,
                "distance": self.read_distance,
                "touch": self.read_touch,
            }
            if sensor in readers:
                return await readers[sensor](side)
            if sensor == "back_touch":
                return await self.read_back_touch()
            if sensor == "imu":
                return await self.read_imu()
            if sensor == "gesture":
                return await self.read_gesture(tool_input.get("timeout", 5.0))
            if sensor == "vision":
                return await self.read_vision(tool_input.get("timeout", 10.0))
            return ToolResult(success=False, message=f"Unknown sensor: {sensor}")

        if action in ("activate", "deactivate"):
            if sensor in ("gesture", "vision"):
                if action == "activate":
                    return await getattr(self, f"activate_{sensor}")(reactions)
                return await getattr(self, f"deactivate_{sensor}")()
            if sensor in ("light", "distance", "touch", "back_touch"):
                return await getattr(self, f"{action}_{sensor}")()
            return ToolResult(
                success=False,
                message=f"Sensor '{sensor}' does not support action '{action}' (imu is read-only)",
            )

        return ToolResult(
            success=False,
            message=f"Unknown sensor action: {action} (use read/activate/deactivate)",
        )

    async def process_tool_call(self, tool_name: str, tool_input: dict) -> str:
        """Process a tool call from the LLM"""
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
        elif tool_name == "bittle_sensor":
            result = await self.use_sensor(tool_input)
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
        """Return the system prompt for the Hailo LLM"""
        return """You control a Petoi Bittle robot. Use the tools to act, then confirm what you did
in one short sentence.

- Use bittle_execute_skill for any standard motion (rest, sit, walk, dance, ...) — it is the safest option.
- Use bittle_control_motor only for small adjustments; angles are -90 to +90 degrees.
- Use bittle_sensor with action "read" to take one measurement, or "activate"/"deactivate" to start or
  stop a continuous stream. For gesture/vision you can set "reactions" to true so the robot reacts
  (e.g. the dog tracks the target with its head).
- Be cautious: avoid extreme angles and rapid movements. If a request is impossible, say so
  briefly and suggest an alternative."""

    @staticmethod
    def _looks_garbled(text: str) -> bool:
        """Heuristic for degenerate LLM output.

        When the model's context/cache overflows it emits multilingual token
        salad — mixed-script fragments plus a few pure-ASCII words. Real
        answers here are short English sentences, so a long reply where most
        'words' are not clean ASCII words (and it contains non-ASCII garbage)
        is treated as degenerate. Looping degeneration (one word repeated
        over and over) is caught separately.
        """
        text = text.strip()
        if len(text) < 150:
            return False
        words = text.split()
        if not words:
            return False
        good = sum(
            1 for w in words if re.fullmatch(r"[A-Za-z0-9_'’.\-!?]{2,}", w)
        )
        word_ratio = good / len(words)
        non_ascii = sum(1 for ch in text if ord(ch) > 0x2018) / len(text)
        if word_ratio < 0.8 and non_ascii > 0.05:
            return True
        # Looping degeneration: the same word dominates a long output.
        if len(words) >= 20:
            top = max(set(words), key=words.count)
            if words.count(top) / len(words) > 0.35:
                return True
        return False

    async def chat(self, user_message: str) -> str:
        """Send a message and get a response from Hailo-Ollama, dispatching any tool calls.

        Uses Hailo-Ollama's Ollama-compatible /api/chat structured tool
        calling: the tool schemas are sent in the request, the model may
        answer with tool_calls, we dispatch each to the robot, and feed the
        results back until it returns a final text answer.

        Hailo-Ollama is stateless per request, so the full conversation
        history and tools array are resent on every call. Hailo models use a
        2048-token context window — keep conversations short, and start a new
        session if the model starts to misbehave.
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
                # Hailo-Ollama takes sampling parameters under "options"
                # (ModelParameters: temperature, seed, top_k, top_p, ...).
                # Keep temperature low for stable tool calls, and cap the
                # output: a final answer is one sentence, and a cap turns a
                # degenerate run into a quick failure instead of a 2-minute
                # token-salad flood.
                "options": {"temperature": 0.2, "num_predict": 200},
            }

            try:
                logger.debug(
                    "hailo-ollama POST %s (%d messages, %d tools)",
                    self.ollama_url,
                    len(payload["messages"]),
                    len(payload["tools"]),
                )
                response = requests.post(self.ollama_url, json=payload, timeout=300)
                response.raise_for_status()
                result = response.json()
            except requests.exceptions.RequestException as e:
                logger.debug("hailo-ollama request failed: %s", e)
                error_msg = f"Error communicating with Hailo-Ollama: {e}"
                print(f"❌ {error_msg}")
                print("Troubleshooting:")
                print("  1. Is the hailo-ollama server running? (default: http://localhost:8000)")
                print("  2. Is the model pulled into the local model store?")
                print(f"     Available models: {self.list_models() or '(could not list models)'}")
                print(f"     Pull: curl {self.ollama_base_url}/api/pull "
                      f"-H 'Content-Type: application/json' "
                      f"-d '{{\"model\": \"{self.model}\", \"stream\": true}}'")
                return error_msg

            message = result.get("message", {})
            content = message.get("content") or ""
            tool_calls = message.get("tool_calls") or []
            logger.debug(
                "model response: content=%r tool_calls=%d", content, len(tool_calls)
            )

            if not tool_calls:
                if self._looks_garbled(content):
                    logger.warning(
                        "discarding garbled model output (%d chars): %r...",
                        len(content), content[:80],
                    )
                    # Don't poison the history with degenerate output.
                    return (
                        "⚠️ The model produced unreadable output — please try again, "
                        "or rephrase your request (e.g. 'sit down' instead of 'make bittle rest')."
                    )
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
        print("🤖 LLM-Controlled Petoi Bittle (Hailo-Ollama)")
        print("=" * 70)
        print(f"Model: {self.model} @ {self.ollama_base_url}")
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
        print("  3. Ensure the hailo-ollama server is running and the model is pulled")
        sys.exit(1)

    try:
        await controller.interactive_chat()
    finally:
        await controller.disconnect()
        print("Program terminated.")


if __name__ == "__main__":
    asyncio.run(main())
