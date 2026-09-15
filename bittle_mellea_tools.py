#!/usr/bin/env python3
"""
Mellea tool definitions for Bittle control.

Provides tool registration and execution handlers for the Mellea framework.
Tools are automatically converted to JSON schemas for the LLM.
"""

import asyncio
from typing import Any, Dict, List, Optional

from bittle_backend import BittleBackendController


class BittleMelleaTools:
    """Tool definitions and handlers for Mellea integration"""

    def __init__(self, controller: BittleBackendController):
        self.controller = controller
        self.tool_registry: Dict[str, callable] = {}
        self._register_all_tools()

    def _register_all_tools(self):
        """Register all tool handlers"""
        self.tool_registry = {
            "bittle_execute_skill": self.execute_skill,
            "bittle_control_motor": self.control_motor,
            "bittle_sequence_motion": self.sequence_motion,
            "bittle_get_status": self.get_status,
            "bittle_beep": self.beep,
            "bittle_calibrate_motor": self.calibrate_motor,
        }

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """
        Get JSON schema definitions for all tools.
        These are passed to the LLM for tool calling.
        """
        return [
            {
                "name": "bittle_execute_skill",
                "description": "Execute a predefined skill or behavior on the Bittle robot",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "skill_name": {
                            "type": "string",
                            "enum": self.controller.get_available_skills(),
                            "description": "Name of the skill to execute"
                        }
                    },
                    "required": ["skill_name"]
                }
            },
            {
                "name": "bittle_control_motor",
                "description": "Control an individual servo motor on the Bittle",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "motor_name": {
                            "type": "string",
                            "description": "Motor name (neck, left_shoulder, etc.) or index (0, 8-15)"
                        },
                        "angle": {
                            "type": "integer",
                            "minimum": -90,
                            "maximum": 90,
                            "description": "Target angle in degrees"
                        },
                        "duration": {
                            "type": "number",
                            "default": 0.1,
                            "description": "Time to reach target in seconds"
                        }
                    },
                    "required": ["motor_name", "angle"]
                }
            },
            {
                "name": "bittle_sequence_motion",
                "description": "Execute a sequence of motor movements with timing",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "sequence": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "description": "Motion step: either skill or motor movement"
                            },
                            "description": "List of motion steps with timing"
                        },
                        "repeat": {
                            "type": "integer",
                            "default": 1,
                            "description": "Number of times to repeat the sequence"
                        },
                        "loop_forever": {
                            "type": "boolean",
                            "default": False,
                            "description": "Repeat indefinitely until interrupted"
                        }
                    },
                    "required": ["sequence"]
                }
            },
            {
                "name": "bittle_get_status",
                "description": "Query current status of the Bittle robot",
                "input_schema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "bittle_beep",
                "description": "Make the Bittle produce a beep sound",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "frequency": {
                            "type": "integer",
                            "default": 1000,
                            "minimum": 20,
                            "maximum": 20000,
                            "description": "Frequency in Hz"
                        },
                        "duration": {
                            "type": "number",
                            "default": 100,
                            "description": "Duration in milliseconds"
                        }
                    }
                }
            },
            {
                "name": "bittle_calibrate_motor",
                "description": "Calibrate a motor to its neutral position",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "motor_name": {
                            "type": "string",
                            "description": "Motor to calibrate"
                        },
                        "offset": {
                            "type": "integer",
                            "default": 0,
                            "minimum": -90,
                            "maximum": 90,
                            "description": "Calibration offset in degrees"
                        }
                    },
                    "required": ["motor_name"]
                }
            }
        ]

    async def execute_skill(self, skill_name: str) -> Dict[str, Any]:
        """Execute a predefined skill"""
        if skill_name not in self.controller.get_available_skills():
            return {
                "success": False,
                "skill": skill_name,
                "message": f"Unknown skill: {skill_name}. Available: {', '.join(self.controller.get_available_skills())}"
            }

        try:
            success = await self.controller.execute_skill(skill_name)
            return {
                "success": success,
                "skill": skill_name,
                "message": f"Executed skill: {skill_name}" if success else f"Failed to execute {skill_name}"
            }
        except Exception as e:
            return {
                "success": False,
                "skill": skill_name,
                "message": f"Error executing {skill_name}: {str(e)}"
            }

    async def control_motor(self, motor_name: str, angle: int, duration: float = 0.1) -> Dict[str, Any]:
        """Control individual motor"""
        valid, motor_index, msg = self.controller.validate_motor_name_or_index(motor_name)
        if not valid:
            return {
                "success": False,
                "motor": motor_name,
                "angle": angle,
                "message": msg
            }

        valid, msg = self.controller.validate_motor_angle(angle)
        if not valid:
            return {
                "success": False,
                "motor": motor_name,
                "angle": angle,
                "message": msg
            }

        try:
            success = await self.controller.control_motor(motor_name, angle, duration)
            return {
                "success": success,
                "motor": motor_name,
                "angle": angle,
                "message": f"Motor {motor_name} moved to {angle}°" if success else f"Failed to move {motor_name}"
            }
        except Exception as e:
            return {
                "success": False,
                "motor": motor_name,
                "angle": angle,
                "message": f"Error controlling motor: {str(e)}"
            }

    async def sequence_motion(
        self,
        sequence: List[Dict[str, Any]],
        repeat: int = 1,
        loop_forever: bool = False
    ) -> Dict[str, Any]:
        """Execute sequence of motions"""
        if not sequence:
            return {
                "success": False,
                "sequence_id": None,
                "steps_executed": 0,
                "message": "Sequence is empty"
            }

        try:
            seq_id, steps = await self.controller.execute_sequence(
                sequence,
                repeat=repeat,
                loop_forever=loop_forever
            )
            return {
                "success": True,
                "sequence_id": seq_id,
                "steps_executed": steps,
                "message": f"Sequence completed with {steps} steps"
            }
        except Exception as e:
            return {
                "success": False,
                "sequence_id": None,
                "steps_executed": 0,
                "message": f"Error executing sequence: {str(e)}"
            }

    async def get_status(self) -> Dict[str, Any]:
        """Query robot status"""
        try:
            status = await self.controller.get_status()
            result = {
                "success": True,
                "connected": status.connected,
                "battery_voltage": status.battery_voltage,
                "current_motion": status.current_motion,
                "motor_positions": status.motor_positions,
                "timestamp": status.timestamp,
            }
            if status.error:
                result["error"] = status.error
            if status.last_command:
                result["last_command"] = status.last_command
            return result
        except Exception as e:
            return {
                "success": False,
                "connected": False,
                "message": f"Error querying status: {str(e)}"
            }

    async def beep(self, frequency: int = 1000, duration: float = 100) -> Dict[str, Any]:
        """Make robot beep"""
        try:
            success = await self.controller.beep(frequency, duration)
            return {
                "success": success,
                "message": f"Beep: {frequency}Hz for {duration}ms" if success else "Failed to produce beep"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error producing beep: {str(e)}"
            }

    async def calibrate_motor(self, motor_name: str, offset: int = 0) -> Dict[str, Any]:
        """Calibrate motor"""
        valid, motor_index, msg = self.controller.validate_motor_name_or_index(motor_name)
        if not valid:
            return {
                "success": False,
                "motor": motor_name,
                "offset": offset,
                "message": msg
            }

        try:
            success = await self.controller.calibrate_motor(motor_name, offset)
            return {
                "success": success,
                "motor": motor_name,
                "offset": offset,
                "message": f"Motor {motor_name} calibrated with offset {offset}°" if success else f"Failed to calibrate {motor_name}"
            }
        except Exception as e:
            return {
                "success": False,
                "motor": motor_name,
                "offset": offset,
                "message": f"Error calibrating motor: {str(e)}"
            }

    async def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Execute a tool by name with given parameters"""
        if tool_name not in self.tool_registry:
            return {
                "success": False,
                "message": f"Unknown tool: {tool_name}"
            }

        try:
            handler = self.tool_registry[tool_name]
            result = await handler(**kwargs)
            return result
        except Exception as e:
            return {
                "success": False,
                "message": f"Error executing tool {tool_name}: {str(e)}"
            }

    def get_system_prompt(self) -> str:
        """Return system prompt for LLM"""
        motors_list = ", ".join(self.controller.get_available_motors().values())
        skills_list = ", ".join(self.controller.get_available_skills())

        return f"""You are a helpful assistant that controls a Petoi Bittle robot. You have access to tools that allow you to make the robot move, execute behaviors, and query its status.

## Core Capabilities

You can control the Bittle robot through the following tools:
1. Execute predefined skills (sit, stand, walk, etc.)
2. Control individual servo motors for precise movements
3. Create custom motion sequences
4. Query robot status and battery level
5. Make the robot beep for feedback
6. Calibrate motors to neutral positions

## Available Skills

{skills_list}

## Available Motors

{motors_list}

Motor angle range: -90° to +90°

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

When users describe emotions or actions, break them down into robot movements that express those concepts.

## Safety First

- Before executing new motions, check the robot is connected
- Avoid extreme angles or rapid movements that could strain servos
- Respect the robot's physical limitations
- Always provide feedback on what the robot is doing
"""
