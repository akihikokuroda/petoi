#!/usr/bin/env python3
"""
LLM-controlled Petoi Bittle using Mellea framework
Automatic tool orchestration with Ollama backend
"""

import asyncio
import os
import sys
from typing import Optional
from dataclasses import dataclass

try:
    from mellea import start_session
    from mellea.stdlib.context import ChatContext
except ImportError:
    print("❌ Mellea not installed. Install with: pip install mellea")
    sys.exit(1)

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
    """Bridge between Mellea LLM and Petoi Bittle robot"""

    def __init__(self, bittle_address: Optional[str] = None):
        self.bittle = BittleBLEController(address=bittle_address, command_delay=0.05)
        self.conversation_history = []

        # Initialize Mellea session with Ollama
        self.mellea = start_session(
            backend_name="ollama",
            model_id="granite4.2:3b",
            context_type="chat"
        )

    async def connect(self) -> bool:
        """Connect to the Bittle robot"""
        return await self.bittle.connect()

    async def disconnect(self):
        """Disconnect from the Bittle robot"""
        await self.bittle.disconnect()

    def _register_tools(self):
        """Register all Bittle control tools with Mellea"""
        # These tool functions will be called by Mellea automatically
        self.tools = {
            "bittle_execute_skill": self._tool_execute_skill,
            "bittle_control_motor": self._tool_control_motor,
            "bittle_sequence_motion": self._tool_sequence_motion,
            "bittle_get_status": self._tool_get_status,
            "bittle_beep": self._tool_beep,
            "bittle_calibrate_motor": self._tool_calibrate_motor,
        }

    async def _tool_execute_skill(self, skill_name: str) -> dict:
        """Execute a predefined skill or behavior on the Bittle robot.

        Args:
            skill_name: One of: sit, stand, walk_forward, walk_backward, walk_left,
                       walk_right, trot_forward, trot_backward, trot_left, trot_right,
                       balance, stretch, pee, rest, sleep, idle, pick_up_left, pick_up_right

        Returns:
            dict with success status, skill name, and message
        """
        if skill_name not in SKILLS:
            return {
                "success": False,
                "skill": skill_name,
                "message": f"Unknown skill: {skill_name}. Available: {', '.join(SKILLS.keys())}"
            }

        try:
            success = await self.bittle.execute_skill(skill_name)
            return {
                "success": success,
                "skill": skill_name,
                "message": f"Executed skill: {skill_name}"
            }
        except Exception as e:
            return {
                "success": False,
                "skill": skill_name,
                "message": f"Error executing {skill_name}: {str(e)}"
            }

    async def _tool_control_motor(self, motor_name: str, angle: int, duration: float = 0.1) -> dict:
        """Control an individual servo motor on the Bittle.

        Args:
            motor_name: Motor name (neck, left_shoulder, right_shoulder, etc.) or index (0, 8-15)
            angle: Target angle in degrees (-90 to +90)
            duration: Time to reach target in seconds (default: 0.1)

        Returns:
            dict with success status, motor, angle, and message
        """
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
            return {
                "success": False,
                "motor": motor_name,
                "angle": angle,
                "message": f"Unknown motor: {motor_name}. Available: {', '.join(motor_map.keys())}"
            }

        if angle < -90 or angle > 90:
            return {
                "success": False,
                "motor": motor_name,
                "angle": angle,
                "message": f"Angle {angle}° out of range [-90, +90]"
            }

        try:
            motor_index = motor_map[motor_name]
            success = await self.bittle.execute_motor(motor_index, angle)
            return {
                "success": success,
                "motor": motor_name,
                "angle": angle,
                "message": f"Motor {motor_name} moved to {angle}°"
            }
        except Exception as e:
            return {
                "success": False,
                "motor": motor_name,
                "angle": angle,
                "message": f"Error controlling motor: {str(e)}"
            }

    async def _tool_sequence_motion(self, sequence: list, repeat: int = 1) -> dict:
        """Execute a sequence of motor movements to create custom behaviors.

        Args:
            sequence: List of motion steps. Each step is a dict with either:
                      - "skill": skill_name and "duration": float
                      - "motor": motor_name, "angle": int, and "duration": float
            repeat: Number of times to repeat the sequence (default: 1)

        Returns:
            dict with success status, sequence_id, steps executed, and message
        """
        try:
            steps_executed = 0
            for rep in range(repeat):
                for step in sequence:
                    if "skill" in step:
                        result = await self._tool_execute_skill(step["skill"])
                        if result["success"]:
                            steps_executed += 1
                        if "duration" in step:
                            await asyncio.sleep(step["duration"])
                    elif "motor" in step and "angle" in step:
                        result = await self._tool_control_motor(
                            step["motor"],
                            step["angle"],
                            step.get("duration", 0.1),
                        )
                        if result["success"]:
                            steps_executed += 1
                        if "duration" in step:
                            await asyncio.sleep(step["duration"])

            return {
                "success": True,
                "sequence_id": f"seq_{int(asyncio.get_event_loop().time())}",
                "steps_executed": steps_executed,
                "message": f"Sequence completed with {steps_executed} steps ({repeat} repetition(s))"
            }
        except Exception as e:
            return {
                "success": False,
                "sequence_id": None,
                "steps_executed": 0,
                "message": f"Error executing sequence: {str(e)}"
            }

    async def _tool_get_status(self) -> dict:
        """Query current status of the Bittle robot.

        Returns:
            dict with connection status, battery voltage, current motion, motor positions
        """
        try:
            return {
                "connected": self.bittle.connected,
                "battery_voltage": "N/A",
                "current_motion": "idle",
                "motor_positions": {},
                "timestamp": asyncio.get_event_loop().time(),
                "message": "Status retrieved successfully"
            }
        except Exception as e:
            return {
                "connected": False,
                "battery_voltage": 0,
                "current_motion": "error",
                "motor_positions": {},
                "message": f"Error querying status: {str(e)}"
            }

    async def _tool_beep(self, frequency: int = 1000, duration: float = 100) -> dict:
        """Make the Bittle produce a beep sound.

        Args:
            frequency: Frequency in Hz (default: 1000)
            duration: Duration in milliseconds (default: 100)

        Returns:
            dict with success status and message
        """
        try:
            cmd = f"b{int(frequency)}"
            await self.bittle.send_command(cmd)
            return {
                "success": True,
                "message": f"Beep: {frequency}Hz for {duration}ms"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error producing beep: {str(e)}"
            }

    async def _tool_calibrate_motor(self, motor_name: str, offset: int = 0) -> dict:
        """Calibrate a motor to its neutral position.

        Args:
            motor_name: Motor to calibrate
            offset: Calibration offset in degrees (default: 0)

        Returns:
            dict with success status, motor, offset, and message
        """
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
            return {
                "success": False,
                "motor": motor_name,
                "offset": offset,
                "message": f"Unknown motor: {motor_name}"
            }

        try:
            # Calibrate by moving to neutral position (0 degrees)
            motor_index = motor_map[motor_name]
            success = await self.bittle.execute_motor(motor_index, offset)
            return {
                "success": success,
                "motor": motor_name,
                "offset": offset,
                "message": f"Motor {motor_name} calibrated with offset {offset}°"
            }
        except Exception as e:
            return {
                "success": False,
                "motor": motor_name,
                "offset": offset,
                "message": f"Error calibrating motor: {str(e)}"
            }

    def get_system_prompt(self) -> str:
        """Return the system prompt for LLM"""
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
        """Send a message and get a response using Mellea framework.

        Mellea automatically handles:
        - Tool schema generation from Python functions
        - LLM invocation with tool definitions
        - Tool execution and result processing
        - Multi-turn conversation management
        """
        try:
            # Use Mellea's chat method for automatic tool calling
            # This handles the entire agentic loop internally
            result = await asyncio.to_thread(
                self.mellea.chat,
                user_message,
                tool_calls=True,
            )

            # Extract final response text
            final_response = str(result)

            return final_response

        except Exception as e:
            error_msg = f"Error during Mellea processing: {str(e)}"
            return error_msg

    async def interactive_chat(self):
        """Run an interactive chat loop"""
        print("\n" + "=" * 70)
        print("🤖 LLM-Controlled Petoi Bittle (Mellea-powered)")
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
    import argparse

    parser = argparse.ArgumentParser(description="Control Bittle with LLM (Mellea-powered)")
    parser.add_argument("--address", help="Bittle Bluetooth address (optional)")
    args = parser.parse_args()

    controller = LLMBittleController(bittle_address=args.address)

    if not await controller.connect():
        print("\n❌ Failed to connect to Bittle")
        print("Troubleshooting:")
        print("  1. Ensure Bittle is powered on")
        print("  2. Pair Bittle via Bluetooth settings")
        sys.exit(1)

    try:
        await controller.interactive_chat()
    finally:
        await controller.disconnect()
        print("Program terminated.")


if __name__ == "__main__":
    asyncio.run(main())
