#!/usr/bin/env python3
"""
LLM-controlled Petoi Bittle using Claude API or Mellea framework
Main controller that bridges Claude/Mellea tool calls to actual robot commands
"""

import asyncio
import json
import os
import sys
from typing import Optional, Any
from dataclasses import dataclass

try:
    from anthropic import Anthropic
except ImportError:
    print("❌ Anthropic SDK not installed. Install with: pip install anthropic")
    sys.exit(1)

try:
    from mellea import start_session
    from mellea.backends import ModelOption
    from mellea.stdlib.context import ChatContext
    MELLEA_AVAILABLE = True
except ImportError:
    MELLEA_AVAILABLE = False

from petoi_bittle_controller import BittleBLEController, SKILLS, MOTOR_INDICES


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
    """Bridge between Claude LLM and Petoi Bittle robot"""

    def __init__(self, bittle_address: Optional[str] = None):
        self.bittle = BittleBLEController(address=bittle_address, command_delay=0.05)
        self.client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        self.conversation_history = []

    async def connect(self) -> bool:
        """Connect to the Bittle robot"""
        return await self.bittle.connect()

    async def disconnect(self):
        """Disconnect from the Bittle robot"""
        await self.bittle.disconnect()

    def get_tools(self) -> list:
        """Return tool definitions for Claude"""
        return [
            {
                "name": "bittle_execute_skill",
                "description": "Execute a predefined skill or behavior on the Bittle robot",
                "input_schema": {
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
                "input_schema": {
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
                "input_schema": {
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
                "input_schema": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "bittle_beep",
                "description": "Make the Bittle produce a beep sound",
                "input_schema": {
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
                "input_schema": {
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
        ]

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

    async def process_tool_call(self, tool_name: str, tool_input: dict) -> str:
        """Process a tool call from Claude"""
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
        else:
            result = ToolResult(success=False, message=f"Unknown tool: {tool_name}")

        return json.dumps(result.to_dict())

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
        """Send a message and get a response from Claude"""
        self.conversation_history.append({"role": "user", "content": user_message})

        while True:
            response = self.client.messages.create(
                model="claude-opus-5",
                max_tokens=1024,
                system=self.get_system_prompt(),
                tools=self.get_tools(),
                messages=self.conversation_history,
            )

            # Check if we need to handle tool calls
            if response.stop_reason == "tool_use":
                # Process all tool calls in the response
                assistant_message = {"role": "assistant", "content": response.content}
                self.conversation_history.append(assistant_message)

                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        print(f"  → Calling tool: {block.name}")
                        result = await self.process_tool_call(block.name, block.input)
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result,
                            }
                        )

                # Add tool results to conversation
                self.conversation_history.append(
                    {"role": "user", "content": tool_results}
                )
            else:
                # End of conversation - extract and return final text
                final_response = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        final_response += block.text

                self.conversation_history.append(
                    {"role": "assistant", "content": response.content}
                )
                return final_response

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
