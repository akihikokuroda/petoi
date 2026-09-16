#!/usr/bin/env python3
"""
LLM-controlled Petoi Bittle using Mellea framework
Manual tool orchestration with explicit context management
"""

import asyncio
import logging
import os
import sys
from typing import Optional, Callable, Any
from dataclasses import dataclass

try:
    from mellea import MelleaSession
    from mellea.backends import tool, ModelOption
    from mellea.backends.ollama import OllamaModelBackend
    from mellea.stdlib.context import SimpleContext
    from mellea.stdlib.components import Message, ToolMessage
    from mellea.stdlib.functional import aact
    from mellea.plugins import register
    from mellea.plugins.builtin_debug.generation import (
        log_generation_post_call,
        log_generation_pre_call,
    )
except ImportError:
    print("❌ Mellea not installed. Install with: pip install mellea")
    sys.exit(1)

from petoi_bittle_controller import BittleBLEController, SKILLS, MOTOR_INDICES

# Global reference to controller (used by standalone tool functions)
_current_controller = None

# Store raw (undecorated) tool functions for manual execution
_raw_tool_functions = {}


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


# Raw tool implementations (stored before decorator)
async def _impl_execute_skill(skill_name: str) -> dict:
    """Execute a predefined skill or behavior on the Bittle robot.

    This is the safest way to make the robot move. Skills are pre-programmed sequences
    that handle complex motor coordination automatically.

    Args:
        skill_name: The name of the skill to execute. Valid skills are:
            - sit, stand, sleep, rest, idle: Basic postures
            - walk_forward, walk_backward, walk_left, walk_right: Walking gaits
            - trot_forward, trot_backward, trot_left, trot_right: Trotting gaits
            - balance: Balance and stabilization
            - stretch: Full body stretch
            - pee, pick_up_left, pick_up_right: Fun/specialty behaviors

    Returns:
        dict with 'success' (bool), 'skill' (str), and 'message' (str).
        success=True means the skill executed successfully.

    Examples:
        - To make the robot stand: use 'stand'
        - To make it walk forward: use 'walk_forward'
        - To make it dance: combine 'walk_forward' and 'trot_left' in a sequence
    """
    controller = _current_controller
    if not controller:
        return {"success": False, "message": "Controller not initialized"}

    if skill_name not in SKILLS:
        return {
            "success": False,
            "skill": skill_name,
            "message": f"Unknown skill: {skill_name}. Available: {', '.join(SKILLS.keys())}"
        }

    try:
        success = await controller.bittle.execute_skill(skill_name)
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


# Store raw implementation and create Mellea-wrapped version
_raw_tool_functions["bittle_execute_skill"] = _impl_execute_skill
tool_execute_skill = tool(name="bittle_execute_skill")(_impl_execute_skill)


async def _impl_control_motor(motor_name: str, angle: int, duration: float = 0.1) -> dict:
    """Control an individual servo motor on the Bittle robot for precise movements.

    Use this for fine-tuning specific motors or creating custom animations. Exercise caution
    to avoid straining the servos with extreme angles or rapid movements.

    Args:
        motor_name: The motor to control. Valid motor names are:
            - neck: Head/neck rotation (useful for looking around)
            - left_shoulder, right_shoulder: Front leg shoulder joints
            - left_hip, right_hip: Back leg hip joints
            - left_arm, right_arm: Arm movements (if equipped)
            - left_ankle, right_ankle: Foot/ankle movements
        angle: Target angle in degrees, must be between -90 and +90.
            - Negative angles rotate one direction (e.g., left)
            - Positive angles rotate the opposite direction (e.g., right)
            - 0 degrees is neutral/center position
        duration: How long the movement takes in seconds (default: 0.1).
            - Smaller values (0.05-0.1) are faster movements
            - Larger values (0.5-1.0) are slower, smoother movements

    Returns:
        dict with 'success' (bool), 'motor' (str), 'angle' (int), and 'message' (str).

    Examples:
        - Tilt head left: motor_name='neck', angle=-45
        - Raise left shoulder: motor_name='left_shoulder', angle=45
        - Slow arm movement: motor_name='left_arm', angle=30, duration=0.5
    """
    controller = _current_controller
    if not controller:
        return {"success": False, "message": "Controller not initialized"}

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
        success = await controller.bittle.execute_motor(motor_index, angle)
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


# Store raw implementation and create Mellea-wrapped version
_raw_tool_functions["bittle_control_motor"] = _impl_control_motor
tool_control_motor = tool(name="bittle_control_motor")(_impl_control_motor)


async def _impl_get_status() -> dict:
    """Query the current status of the Bittle robot connection.

    Use this to check if the robot is connected via Bluetooth before executing movements.
    Always verify connection before attempting important tasks.

    Args:
        (none)

    Returns:
        dict with:
            - 'success' (bool): True if status was retrieved
            - 'connected' (bool): True if robot is connected via Bluetooth
            - 'message' (str): Status description

    Connection status interpretation:
        - connected=True: Robot is ready and can accept commands
        - connected=False: Robot is not connected; reconnect before sending commands

    Example use cases:
        - Before executing a dance: "Check if the robot is connected"
        - To verify robot is ready: "Is the robot connected and ready?"
        - Before complex sequences: "Make sure the robot is connected first"
    """
    controller = _current_controller
    if not controller:
        return {"success": False, "connected": False, "message": "Controller not initialized"}

    try:
        is_connected = controller.bittle.connected
        return {
            "success": True,
            "connected": is_connected,
            "message": f"Robot is {'connected and ready' if is_connected else 'not connected'}"
        }
    except Exception as e:
        return {
            "success": False,
            "connected": False,
            "message": f"Error checking status: {str(e)}"
        }


# Store raw implementation and create Mellea-wrapped version
_raw_tool_functions["bittle_get_status"] = _impl_get_status
tool_get_status = tool(name="bittle_get_status")(_impl_get_status)


async def _impl_beep(frequency: int = 1000, duration: float = 100) -> dict:
    """Make the Bittle produce a beep sound for audio feedback or acknowledgment.

    Use beeping to add audio effects to movements, acknowledge user input, or express emotions
    through sound (e.g., happy beeps when excited, sad beeps when sad).

    Args:
        frequency: Pitch of the beep in Hertz (Hz). Default: 1000
            - 500 Hz: Low, deep beep (serious, sad)
            - 1000 Hz: Medium beep (default, neutral)
            - 2000 Hz: High, sharp beep (happy, excited)
            - 100-300 Hz: Very low bass (threatening, power)
            - 3000+ Hz: Very high (alarm, warning)
        duration: How long the beep lasts in milliseconds. Default: 100
            - 50 ms: Quick beep
            - 100 ms: Normal beep
            - 200-500 ms: Extended beep
            - 1000+ ms: Long sustained tone

    Returns:
        dict with 'success' (bool), 'message' (str) describing the beep.

    Examples:
        - Happy acknowledgment: frequency=2000, duration=150
        - Sad sound: frequency=300, duration=200
        - Alarm/warning: frequency=1500, duration=100 (repeated)
        - Thinking/processing: frequency=800, duration=100
        - Question/confused: frequency=1200, duration=80
    """
    controller = _current_controller
    if not controller:
        return {"success": False, "message": "Controller not initialized"}

    try:
        cmd = f"b{int(frequency)}"
        await controller.bittle.send_command(cmd)
        return {
            "success": True,
            "message": f"Beep: {frequency}Hz for {duration}ms"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error producing beep: {str(e)}"
        }


# Store raw implementation and create Mellea-wrapped version
_raw_tool_functions["bittle_beep"] = _impl_beep
tool_beep = tool(name="bittle_beep")(_impl_beep)


async def _impl_calibrate_motor(motor_name: str, offset: int = 0) -> dict:
    """Calibrate a motor to adjust its neutral/center position.

    Use this if a motor is not centered correctly or has drifted. Calibration sets the
    offset so that 0 degrees maps to the true neutral position for that motor.

    Args:
        motor_name: The motor to calibrate. Valid names are:
            - neck, left_shoulder, right_shoulder, left_hip, right_hip
            - left_arm, right_arm, left_ankle, right_ankle
        offset: The calibration offset in degrees (default: 0).
            - Positive values: rotate the motor in the positive direction
            - Negative values: rotate the motor in the negative direction
            - 0: Reset to default neutral position
            - Typical range: -15 to +15 degrees

    Returns:
        dict with 'success' (bool), 'motor' (str), 'offset' (int), 'message' (str).

    When to calibrate:
        - Motor is tilted when standing normally
        - Motor drifts during operation
        - After assembly or servo replacement
        - If movements seem off-center

    Example:
        - Motor is tilted 10° to the left: use offset=-10 to correct
        - Motor is tilted 5° to the right: use offset=5 to correct
        - Reset to default: use offset=0
    """
    controller = _current_controller
    if not controller:
        return {"success": False, "message": "Controller not initialized"}

    try:
        cmd = f"c{int(offset)}"
        await controller.bittle.send_command(cmd)
        return {
            "success": True,
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


# Store raw implementation and create Mellea-wrapped version
_raw_tool_functions["bittle_calibrate_motor"] = _impl_calibrate_motor
tool_calibrate_motor = tool(name="bittle_calibrate_motor")(_impl_calibrate_motor)


async def _impl_sequence_motion(sequence: list[dict], repeat: int = 1) -> dict:
    """Execute a sequence of motor movements to create custom behaviors and animations.

    Combine skills and individual motor controls into a choreographed sequence. This is perfect
    for creating dances, expressive movements, or complex multi-step behaviors.

    Args:
        sequence: A list of motion step dictionaries. Each step is one of:
            Skill step: {"skill": "skill_name", "duration": 0.5}
                - Executes a predefined skill like 'walk_forward', 'trot_left', etc.
                - duration (optional): pause after the skill completes (in seconds)
            Motor step: {"motor": "motor_name", "angle": 45, "duration": 0.3}
                - Moves a specific motor to an angle
                - duration: how long the movement takes (in seconds)
        repeat: How many times to repeat the entire sequence (default: 1).
            - repeat=1: Execute once
            - repeat=2: Execute twice in a row
            - repeat=3+: Multiple repetitions for looped behaviors

    Returns:
        dict with 'success' (bool), 'sequence_id' (str), 'steps_executed' (int), 'message' (str).

    Examples:
        Dance sequence:
        [
            {"skill": "stand"},
            {"skill": "walk_forward", "duration": 1.0},
            {"motor": "neck", "angle": -30, "duration": 0.3},
            {"motor": "neck", "angle": 30, "duration": 0.3},
            {"skill": "trot_left", "duration": 0.5},
            {"skill": "trot_right", "duration": 0.5},
            {"skill": "sit"}
        ]

        Confusing gesture:
        [
            {"motor": "neck", "angle": 45, "duration": 0.2},
            {"motor": "neck", "angle": -45, "duration": 0.2},
            {"motor": "left_arm", "angle": -30, "duration": 0.2},
            {"motor": "right_arm", "angle": 30, "duration": 0.2}
        ]
    """
    controller = _current_controller
    if not controller:
        return {"success": False, "message": "Controller not initialized"}

    try:
        steps_executed = 0
        for rep in range(repeat):
            for step in sequence:
                if "skill" in step:
                    result = await tool_execute_skill(step["skill"])
                    if result["success"]:
                        steps_executed += 1
                    if "duration" in step:
                        await asyncio.sleep(step["duration"])
                elif "motor" in step and "angle" in step:
                    result = await tool_control_motor(
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


# Store raw implementation and create Mellea-wrapped version
_raw_tool_functions["bittle_sequence_motion"] = _impl_sequence_motion
tool_sequence_motion = tool(name="bittle_sequence_motion")(_impl_sequence_motion)


class LLMBittleController:
    """Bridge between Mellea LLM and Petoi Bittle robot"""

    def __init__(self, bittle_address: Optional[str] = None, enable_tracing: bool = True):
        global _current_controller
        self.bittle = BittleBLEController(address=bittle_address, command_delay=0.05)
        backend = OllamaModelBackend(model_id="granite4.2:3b")
        context = SimpleContext()
        self.mellea = MelleaSession(backend, context)
        _current_controller = self
        self.mellea_tools = self.get_tool_functions()  # Mellea-wrapped tools for LLM
        self.raw_tools = self._get_raw_tool_functions()  # Raw functions for execution
        self.enable_tracing = enable_tracing
        self._setup_logging()
        if self.enable_tracing:
            register([log_generation_pre_call, log_generation_post_call])

    def _setup_logging(self):
        """Configure logging for generation tracing"""
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(message)s"
        )
        # Ensure mellea generation tracing is captured (uses logger.debug)
        logging.getLogger("mellea.plugins.builtin_debug.generation").setLevel(logging.DEBUG)

    async def connect(self) -> bool:
        """Connect to the Bittle robot"""
        return await self.bittle.connect()

    async def disconnect(self):
        """Disconnect from the Bittle robot"""
        await self.bittle.disconnect()

    def get_tool_functions(self) -> dict:
        """Return Mellea-decorated tool implementations for LLM"""
        return {
            "bittle_execute_skill": tool_execute_skill,
            "bittle_control_motor": tool_control_motor,
            "bittle_sequence_motion": tool_sequence_motion,
            "bittle_get_status": tool_get_status,
            "bittle_beep": tool_beep,
            "bittle_calibrate_motor": tool_calibrate_motor,
        }

    def _get_raw_tool_functions(self) -> dict:
        """Return raw async function implementations for manual tool execution.

        Returns the undecorated tool functions stored in the module-level
        _raw_tool_functions dict. These are the actual implementations that
        get wrapped by @tool decorators for the LLM.
        """
        return _raw_tool_functions


    async def _execute_tool_calls(self, response) -> list:
        """Manually execute tool calls to preserve event loop context.

        Avoids using Mellea's acall_tools() which can break persistent connections
        like BLE by creating tool messages for each tool call and result.
        """
        tool_messages = []

        if not hasattr(response, 'tool_calls') or not response.tool_calls:
            logging.debug("No tool calls in response")
            return tool_messages

        logging.debug(f"LLM Response has {len(response.tool_calls)} tool call(s)")

        for i, tool_call in enumerate(response.tool_calls, 1):
            tool_name = getattr(tool_call, 'name', None)

            # Extract arguments - try different attribute names
            tool_args = {}
            if hasattr(tool_call, 'arguments'):
                tool_args = tool_call.arguments or {}
            elif hasattr(tool_call, 'args'):
                tool_args = tool_call.args or {}
            elif hasattr(tool_call, 'input'):
                tool_args = tool_call.input or {}

            # Log tool call information
            logging.debug(f"[TOOL-CALL #{i}] name={tool_name}")
            logging.debug(f"[TOOL-CALL #{i}] args={tool_args}")
            if hasattr(tool_call, 'id'):
                logging.debug(f"[TOOL-CALL #{i}] id={tool_call.id}")

            # Find the raw tool function (not the Mellea-wrapped version)
            if tool_name not in self.raw_tools:
                result = {"error": f"Unknown tool: {tool_name}"}
                logging.error(f"[TOOL-CALL #{i}] ❌ Unknown tool: {tool_name}")
            else:
                try:
                    tool_func = self.raw_tools[tool_name]
                    logging.debug(f"[TOOL-CALL #{i}] ⏱️  Executing {tool_name}...")
                    # Call the raw async function with unpacked arguments
                    result = await tool_func(**tool_args)
                    logging.debug(f"[TOOL-CALL #{i}] ✅ Success")
                    logging.debug(f"[TOOL-CALL #{i}] result={result}")
                except Exception as e:
                    result = {"error": f"Tool execution failed: {str(e)}"}
                    logging.error(f"[TOOL-CALL #{i}] ❌ Exception: {str(e)}")
                    logging.debug(f"[TOOL-CALL #{i}] result={result}", exc_info=True)

            # Create tool message with result
            tool_msg = ToolMessage(
                role="tool",
                content=str(result),
                tool_output=result,
                name=tool_name,
                args=tool_args,
                tool=tool_call,
            )
            tool_messages.append(tool_msg)
            logging.debug(f"[TOOL-CALL #{i}] Created tool message")

        return tool_messages

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

        Handles manual tool orchestration:
        - Add user message to context
        - Generate response with tool definitions
        - Execute requested tools manually
        - Add tool results back to context

        With tracing enabled, logs all LLM input/output and token usage.
        """
        try:
            ctx = self.mellea.ctx

            # Add user message to context
            user_msg = Message("user", user_message)
            ctx = ctx.add(user_msg)

            # Generate response with tool capability (use Mellea-wrapped tools for LLM)
            tools = list(self.mellea_tools.values())
            response, ctx = await aact(
                user_msg,
                ctx,
                self.mellea.backend,
                model_options={ModelOption.TOOLS: tools},
                tool_calls=True,
                await_result=True,
            )

            # Check if LLM requested tool calls
            if response.tool_calls:
                logging.debug("="*70)
                logging.debug("LLM requested tool calls, executing...")
                logging.debug("="*70)

                # Manually execute tools to preserve event loop context
                tool_messages = await self._execute_tool_calls(response)

                logging.debug("="*70)
                logging.debug(f"Executed {len(tool_messages)} tool call(s), adding to context")
                logging.debug("="*70)

                # Add tool messages to context
                for i, tool_msg in enumerate(tool_messages, 1):
                    logging.debug(f"Adding tool message {i}/{len(tool_messages)} to context")
                    ctx = ctx.add(tool_msg)

                # Get final response after tool execution
                logging.debug("Getting final LLM response after tool execution...")
                final_response, ctx = await aact(
                    tool_messages[-1] if tool_messages else user_msg,
                    ctx,
                    self.mellea.backend,
                    await_result=True,
                )
                response_text = str(final_response.value)
                logging.debug(f"Final response received: {response_text[:100]}...")
            else:
                # No tool calls, use response directly
                logging.debug("No tool calls requested by LLM")
                response_text = str(response.value)

            # Update stored context
            self.mellea._ctx = ctx

            return response_text

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
    parser.add_argument("--no-tracing", action="store_true", help="Disable generation tracing")
    args = parser.parse_args()

    controller = LLMBittleController(
        bittle_address=args.address,
        enable_tracing=not args.no_tracing
    )

    if not await controller.connect():
        print("\n❌ Failed to connect to Bittle")
        print("Troubleshooting:")
        print("  1. Ensure Bittle is powered on")
        print("  2. Pair Bittle via Bluetooth settings")
        # sys.exit(1)

    try:
        await controller.interactive_chat()
    finally:
        await controller.disconnect()
        print("Program terminated.")


if __name__ == "__main__":
    asyncio.run(main())
