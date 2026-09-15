# LLM-Controlled Petoi Bittle: Tools & Prompts Design

## Overview

This document outlines the architecture for enabling an LLM to control a Petoi Bittle robot via tool use, powered by **Mellea** and **Ollama**. The system allows natural language commands to be translated into robot actions through a set of well-defined tools with automatic orchestration and error handling.

### Technology Stack

- **Mellea**: Framework for structured LLM orchestration with automatic tool calling, type safety, and error handling
- **Ollama**: Local LLM inference engine running `granite4.2:3b` model
- **Python**: Backend implementation with async/await for real-time control
- **Bluetooth LE**: Communication with Petoi Bittle robot

### Why Mellea + Ollama?

**Mellea advantages**:
- Automatic agentic loop (tool calling → execution → response processing)
- Schema-driven tool definitions ensure type-safe tool calls
- Multi-turn conversations with context preservation
- Built-in requirements validation and rejection sampling
- Works with any LLM backend via pluggable providers

**Ollama advantages**:
- Local inference (no cloud dependencies, full privacy)
- `granite4.2:3b` is lightweight yet capable for tool use
- Fast response times suitable for robot control
- Easy setup and model management

---

## Part 1: Core Tools for the LLM

### Tool 1: `bittle_execute_skill`

Execute predefined skills/behaviors on the Bittle robot.

**Parameters:**
- `skill_name` (string, required): Name of the skill to execute
  - Valid options: `sit`, `stand`, `walk_forward`, `walk_backward`, `walk_left`, `walk_right`, `trot_forward`, `trot_backward`, `trot_left`, `trot_right`, `balance`, `stretch`, `pee`, `rest`, `sleep`, `idle`, `pick_up_left`, `pick_up_right`

**Returns:**
```json
{
  "success": bool,
  "skill": string,
  "message": string
}
```

**Examples:**
```
bittle_execute_skill(skill_name="sit")
→ {"success": true, "skill": "sit", "message": "Robot is now sitting"}

bittle_execute_skill(skill_name="walk_forward")
→ {"success": true, "skill": "walk_forward", "message": "Robot walking forward"}
```

---

### Tool 2: `bittle_control_motor`

Fine-tune individual servo motors for precise movements.

**Parameters:**
- `motor_name` (string, required): Name or index of the motor
  - Valid options: `neck`, `left_shoulder`, `right_shoulder`, `right_hip`, `left_hip`, `left_arm`, `right_arm`, `right_ankle`, `left_ankle`
  - Or numeric index: `0`, `8`, `9`, `10`, `11`, `12`, `13`, `14`, `15`
- `angle` (integer, required): Target angle in degrees
  - Range: `-90` to `+90`
- `duration` (float, optional): Time to reach target angle in seconds (default: 0.1)

**Returns:**
```json
{
  "success": bool,
  "motor": string,
  "angle": int,
  "message": string
}
```

**Examples:**
```
bittle_control_motor(motor_name="neck", angle=30)
→ {"success": true, "motor": "neck", "angle": 30, "message": "Neck moved to 30°"}

bittle_control_motor(motor_name="left_shoulder", angle=-15)
→ {"success": true, "motor": "left_shoulder", "angle": -15, "message": "Left shoulder moved to -15°"}
```

---

### Tool 3: `bittle_sequence_motion`

Execute a sequence of motor movements with timing to create custom behaviors.

**Parameters:**
- `sequence` (array, required): List of motion steps
  - Each step: `{"motor": string, "angle": int, "duration": float}`
  - Or shorthand skill: `{"skill": string, "duration": float}`
- `repeat` (integer, optional): Number of times to repeat the sequence (default: 1)
- `loop_forever` (boolean, optional): Repeat indefinitely until interrupted (default: false)

**Returns:**
```json
{
  "success": bool,
  "sequence_id": string,
  "steps_executed": int,
  "message": string
}
```

**Example:**
```
bittle_sequence_motion(sequence=[
  {"skill": "stand", "duration": 1.0},
  {"motor": "neck", "angle": 30, "duration": 0.5},
  {"motor": "neck", "angle": -30, "duration": 0.5},
  {"motor": "neck", "angle": 0, "duration": 0.5},
  {"skill": "sit", "duration": 1.0}
])
→ {"success": true, "sequence_id": "seq_123", "steps_executed": 5, "message": "Sequence completed"}
```

---

### Tool 4: `bittle_get_status`

Query the current state of the robot.

**Parameters:** None

**Returns:**
```json
{
  "connected": bool,
  "battery_voltage": float,
  "current_motion": string,
  "motor_positions": {
    "motor_name": int
  },
  "timestamp": string
}
```

**Example:**
```
bittle_get_status()
→ {
  "connected": true,
  "battery_voltage": 7.2,
  "current_motion": "idle",
  "motor_positions": {
    "neck": 0,
    "left_shoulder": -5,
    ...
  },
  "timestamp": "2026-09-15T10:30:45Z"
}
```

---

### Tool 5: `bittle_beep`

Make the robot produce sound (beep).

**Parameters:**
- `frequency` (integer, optional): Beep frequency in Hz (default: 1000)
- `duration` (float, optional): Duration in milliseconds (default: 100)

**Returns:**
```json
{
  "success": bool,
  "message": string
}
```

---

### Tool 6: `bittle_calibrate_motor`

Calibrate a specific motor to its neutral position.

**Parameters:**
- `motor_name` (string, required): Motor to calibrate
- `offset` (integer, optional): Calibration offset in degrees (default: 0)

**Returns:**
```json
{
  "success": bool,
  "motor": string,
  "offset": int,
  "message": string
}
```

---

## Part 2: Mellea Integration Overview

### Architecture Flow

```
User Command
    ↓
Mellea Session (with Ollama backend)
    ↓
System Prompt + Tool Definitions
    ↓
LLM (granite4.2:3b via Ollama)
    ↓
Tool Selection & Arguments
    ↓
Mellea Tool Executor
    ↓
BittleController (Bluetooth LE)
    ↓
Robot Action
    ↓
Status/Result → LLM for Next Step
```

### System Prompt for Bittle Control

Use this as your base system prompt when creating a Mellea session:

```
You are a helpful assistant that controls a Petoi Bittle robot. You have access to tools 
that allow you to make the robot move, execute behaviors, and query its status.

## Core Capabilities

You can control the Bittle robot through the following tools:
1. Execute predefined skills (sit, stand, walk, etc.)
2. Control individual servo motors for precise movements
3. Create custom motion sequences
4. Query robot status and battery level
5. Make the robot beep for feedback

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

- Before executing new motions, I should check the robot is connected
- Avoid extreme angles or rapid movements that could strain servos
- Respect the robot's physical limitations
- Always provide feedback on what the robot is doing
```

---

## Part 3: Example Usage Patterns

### Pattern 1: Direct Motion Request

**User:** "Make Bittle sit down"

**LLM Reasoning:** 
- This is a simple predefined skill
- Use `bittle_execute_skill(skill_name="sit")`

**Flow:**
```
bittle_execute_skill(skill_name="sit")
→ Success
Response: "Bittle is now sitting down ✓"
```

---

### Pattern 2: Sequence Creation

**User:** "Make Bittle look around"

**LLM Reasoning:**
- This requires a sequence of neck movements
- Create a sequence that moves the head left, center, right, center

**Flow:**
```
bittle_sequence_motion(sequence=[
  {"motor": "neck", "angle": -45, "duration": 0.5},  # Look left
  {"motor": "neck", "angle": 0, "duration": 0.3},    # Center
  {"motor": "neck", "angle": 45, "duration": 0.5},   # Look right
  {"motor": "neck", "angle": 0, "duration": 0.3}     # Center
])
→ Success
Response: "Bittle is looking around 👀"
```

---

### Pattern 3: Complex Behavior

**User:** "Make Bittle dance!"

**LLM Reasoning:**
- Combine multiple skills and movements for a dance-like behavior
- Alternate between different gaits
- Add timing for rhythm

**Flow:**
```
bittle_sequence_motion(sequence=[
  {"skill": "stand", "duration": 0.5},
  {"skill": "trot_left", "duration": 1.0},
  {"skill": "trot_right", "duration": 1.0},
  {"motor": "left_arm", "angle": 45, "duration": 0.3},
  {"motor": "right_arm", "angle": -45, "duration": 0.3},
  {"motor": "left_arm", "angle": -45, "duration": 0.3},
  {"motor": "right_arm", "angle": 45, "duration": 0.3},
  {"skill": "walk_forward", "duration": 1.5},
], repeat=1)
→ Success
Response: "Bittle is dancing! 💃"
```

---

### Pattern 4: Status Checking

**User:** "Is Bittle okay? How's the battery?"

**LLM Reasoning:**
- Query current robot status
- Interpret battery voltage
- Report findings to user

**Flow:**
```
bittle_get_status()
→ {"connected": true, "battery_voltage": 7.2, "current_motion": "idle", ...}
Response: "Yes, Bittle is doing great! ✓
- Battery: 7.2V (good)
- Status: Idle and ready
- All motors responsive"
```

---

### Pattern 5: Error Handling

**User:** "Bend Bittle's neck to 180 degrees"

**LLM Reasoning:**
- 180° is outside valid range (-90° to +90°)
- Explain the limitation and suggest alternative

**Flow:**
```
❌ Cannot execute
Response: "I can't move the neck to 180° - that's beyond the servo's range of -90° to +90°. 

But I can make Bittle look all the way left (-90°) or right (+90°), or I could make 
it look around by combining multiple movements. Would you like me to do that instead?"
```

---

## Part 4: Implementation Checklist

### Backend (Python)

- [ ] Extend `BittleBLEController` class with async methods for each tool
- [ ] Implement motor validation and bounds checking
- [ ] Add sequence execution with timing
- [ ] Create status query endpoint
- [ ] Add error handling and recovery

### Integration Layer

- [ ] Create JSON tool definitions for Claude API
- [ ] Implement tool execution handler
- [ ] Add response parsing and formatting
- [ ] Set up Bluetooth connection management

### Safety Features

- [ ] Motor angle validation (-90 to +90)
- [ ] Connection health checks
- [ ] Graceful error messages
- [ ] Emergency stop capability
- [ ] Battery level warnings

### Testing

- [ ] Unit tests for each tool
- [ ] Integration tests with mock Bittle
- [ ] End-to-end tests with real robot
- [ ] Edge case testing (disconnects, invalid commands)

---

## Part 5: Tool Definitions (Mellea-style Python)

Tools are defined as Python functions. Mellea automatically converts these to JSON schemas for the LLM and handles tool execution.

```python
from mellea.backends.tools import MelleaTool
from mellea.core import ValidationResult

# Tool 1: Execute Skill
@MelleaTool.register(name="bittle_execute_skill")
def execute_skill(skill_name: str) -> dict:
    """Execute a predefined skill or behavior on the Bittle robot.
    
    Args:
        skill_name: One of: sit, stand, walk_forward, walk_backward, walk_left, 
                   walk_right, trot_forward, trot_backward, trot_left, trot_right,
                   balance, stretch, pee, rest, sleep, idle, pick_up_left, pick_up_right
    
    Returns:
        dict with success status, skill name, and message
    """
    try:
        result = controller.execute_skill(skill_name)
        return {
            "success": result,
            "skill": skill_name,
            "message": f"Executed skill: {skill_name}"
        }
    except Exception as e:
        return {
            "success": False,
            "skill": skill_name,
            "message": f"Error executing {skill_name}: {str(e)}"
        }


# Tool 2: Control Motor
@MelleaTool.register(name="bittle_control_motor")
def control_motor(motor_name: str, angle: int, duration: float = 0.1) -> dict:
    """Control an individual servo motor on the Bittle.
    
    Args:
        motor_name: Motor name (neck, left_shoulder, right_shoulder, etc.) or index (0, 8-15)
        angle: Target angle in degrees (-90 to +90)
        duration: Time to reach target in seconds (default: 0.1)
    
    Returns:
        dict with success status, motor, angle, and message
    """
    try:
        if angle < -90 or angle > 90:
            return {
                "success": False,
                "motor": motor_name,
                "angle": angle,
                "message": f"Angle {angle}° out of range [-90, +90]"
            }
        
        result = controller.control_motor(motor_name, angle, duration)
        return {
            "success": result,
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


# Tool 3: Sequence Motion
@MelleaTool.register(name="bittle_sequence_motion")
def sequence_motion(sequence: list[dict], repeat: int = 1) -> dict:
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
        seq_id, steps = controller.execute_sequence(sequence, repeat)
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


# Tool 4: Get Status
@MelleaTool.register(name="bittle_get_status")
def get_status() -> dict:
    """Query current status of the Bittle robot.
    
    Returns:
        dict with connection status, battery voltage, current motion, motor positions
    """
    try:
        status = controller.get_status()
        return {
            "connected": status.get("connected", False),
            "battery_voltage": status.get("battery", 0),
            "current_motion": status.get("motion", "unknown"),
            "motor_positions": status.get("motors", {}),
            "timestamp": status.get("timestamp", "")
        }
    except Exception as e:
        return {
            "connected": False,
            "battery_voltage": 0,
            "current_motion": "error",
            "motor_positions": {},
            "message": f"Error querying status: {str(e)}"
        }


# Tool 5: Beep
@MelleaTool.register(name="bittle_beep")
def beep(frequency: int = 1000, duration: float = 100) -> dict:
    """Make the Bittle produce a beep sound.
    
    Args:
        frequency: Frequency in Hz (default: 1000)
        duration: Duration in milliseconds (default: 100)
    
    Returns:
        dict with success status and message
    """
    try:
        controller.beep(frequency, int(duration))
        return {
            "success": True,
            "message": f"Beep: {frequency}Hz for {duration}ms"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error producing beep: {str(e)}"
        }


# Tool 6: Calibrate Motor
@MelleaTool.register(name="bittle_calibrate_motor")
def calibrate_motor(motor_name: str, offset: int = 0) -> dict:
    """Calibrate a motor to its neutral position.
    
    Args:
        motor_name: Motor to calibrate
        offset: Calibration offset in degrees (default: 0)
    
    Returns:
        dict with success status, motor, offset, and message
    """
    try:
        result = controller.calibrate_motor(motor_name, offset)
        return {
            "success": result,
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
```

Mellea automatically converts these function signatures to JSON schemas. The schema includes parameter names, types, descriptions, and defaults — exactly what the LLM needs for accurate tool calling.

---

## Part 6: Python Backend Integration with Mellea

```python
import asyncio
from mellea import start_session
from mellea.backends import ModelOption
from mellea.stdlib.context import ChatContext

# Configure Ollama backend
OLLAMA_CONFIG = {
    "base_url": "http://localhost:11434",  # Default Ollama server
    "model": "granite4.2:3b",
}

# System prompt for Bittle control
SYSTEM_PROMPT = """You are a helpful assistant that controls a Petoi Bittle robot. 
You have access to tools that allow you to make the robot move, execute behaviors, 
and query its status.

## Core Capabilities
1. Execute predefined skills (sit, stand, walk, etc.)
2. Control individual servo motors for precise movements
3. Create custom motion sequences
4. Query robot status and battery level
5. Make the robot beep for feedback

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

When users describe emotions or actions, break them down into robot movements."""


async def control_bittle_with_mellea(user_message: str):
    """Control Bittle using Mellea with Ollama backend.
    
    Mellea automatically handles:
    - Tool schema generation from Python functions
    - LLM invocation with tool definitions
    - Tool execution and result processing
    - Multi-turn conversation management
    """
    
    # Start Mellea session with Ollama backend
    m = start_session(
        model_option=ModelOption(
            provider="ollama",
            model="granite4.2:3b",
            base_url="http://localhost:11434",
        )
    )
    
    # Initialize chat context for multi-turn conversation
    ctx = ChatContext(system_prompt=SYSTEM_PROMPT)
    
    # Add user message to context
    ctx.add_user_message(user_message)
    
    # Call instruct with tool use enabled
    # Mellea automatically handles the agentic loop:
    # 1. Sends message + tools to LLM
    # 2. Extracts and executes tool calls
    # 3. Adds results back to context
    # 4. Returns final response
    result = m.instruct(
        ctx,
        tool_use=True,  # Enable automatic tool calling
        max_turns=5,    # Max agentic iterations
    )
    
    # Get final response text
    final_response = str(result)
    print(f"Assistant: {final_response}")
    
    # Check if any tool calls were executed
    if hasattr(result, "tool_calls") and result.tool_calls:
        print(f"\nExecuted tools: {list(result.tool_calls.keys())}")
    
    return result


# Example usage
async def main():
    """Demonstrate Bittle control via Mellea."""
    
    # Simple command
    await control_bittle_with_mellea("Make Bittle sit down")
    
    # Complex sequence
    await control_bittle_with_mellea("Make Bittle look around")
    
    # Status check
    await control_bittle_with_mellea("Is Bittle okay? How's the battery?")


if __name__ == "__main__":
    asyncio.run(main())
```

### Key Differences from Manual Tool Calling

**Without Mellea** (manual):
```python
messages = [{"role": "user", "content": user_message}]
while True:
    response = client.messages.create(model=..., messages=messages, tools=TOOLS)
    if response.stop_reason == "tool_use":
        # Manually extract, validate, execute each tool call
        # Add results back to messages
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})
    else:
        break  # Extract and print final response
```

**With Mellea** (automatic):
```python
result = m.instruct(ctx, tool_use=True)
# Mellea handles the entire loop internally
```

### Advantages of Mellea Approach

1. **Automatic agentic loop** - No manual while loop needed
2. **Type-safe tools** - Schema generated from Python function signatures
3. **Built-in error handling** - Tool execution failures don't crash the loop
4. **Context management** - ChatContext handles turn history automatically
5. **Extensible** - Add new tools by just adding Python functions with `@MelleaTool.register`
6. **Multi-backend support** - Switch from Ollama to Claude or other models with one line

---

## Part 7: Setup & Deployment

### Prerequisites

1. **Ollama Setup** (local LLM inference):
   ```bash
   # Install Ollama from https://ollama.ai
   # Pull granite model
   ollama pull granite4.2:3b
   # Start server (default: http://localhost:11434)
   ollama serve
   ```

2. **Python Dependencies**:
   ```bash
   pip install mellea bleak pydantic
   ```

3. **Bittle Hardware**:
   - Petoi Bittle robot with charged battery
   - Bluetooth LE enabled on control device
   - Robot firmware updated

### Integration Checklist

- [ ] Backend (Python):
  - [ ] Implement `BittleController` class with async methods for each tool
  - [ ] Add motor validation and bounds checking (-90° to +90°)
  - [ ] Implement sequence execution with timing
  - [ ] Create status query via BLE
  - [ ] Add error handling and graceful disconnection

- [ ] Mellea Integration:
  - [ ] Register all tools with `@MelleaTool.register` decorators
  - [ ] Configure Ollama backend with correct base_url and model
  - [ ] Implement `ChatContext` management for multi-turn conversations
  - [ ] Test tool schema generation and LLM tool calling

- [ ] Safety & Validation:
  - [ ] Motor angle validation in tool functions
  - [ ] Connection health checks before executing commands
  - [ ] Graceful error messages when robot is disconnected
  - [ ] Emergency stop capability (force disconnect)
  - [ ] Battery level warnings in status responses

- [ ] Testing:
  - [ ] Unit tests for each tool function
  - [ ] Mock BLE controller for testing without hardware
  - [ ] Integration tests with Mellea simulator
  - [ ] End-to-end tests with real Bittle robot

### Local Development Loop

```bash
# Terminal 1: Start Ollama server
ollama serve

# Terminal 2: Run Bittle controller
python bittle_controller_mellea.py

# Terminal 3: Interact (examples)
python -c "from bittle_controller import control_bittle; control_bittle('Make Bittle sit')"
```

## Part 8: Future Enhancements

- **Vision Integration**: Use camera + CV to let LLM see what Bittle sees
- **Multi-turn Planning**: Let LLM plan sequences before executing (e.g., "Create a dance with 5 moves")
- **Learning**: Allow LLM to save successful motion sequences as reusable "skills"
- **Multi-Robot**: Extend to control multiple Bittle robots in coordination
- **Real-time Feedback**: Stream motor positions/battery level back to LLM during execution
- **Emotional Expressions**: Map described emotions to predefined animation sequences
- **Voice Commands**: Add speech-to-text front-end for hands-free control
- **Performance Metrics**: Track which LLM models/tools are most efficient for Bittle control

---

## References

- [Mellea Framework](https://github.com/generative-computing/mellea) - LLM orchestration with tool use
- [Ollama Documentation](https://github.com/ollama/ollama) - Local LLM inference
- [Granite Models](https://huggingface.co/ibm-granite) - IBM's open-source models
- [Petoi Bittle Documentation](https://docs.petoi.com/) - Robot hardware and protocol
- [Petoi Serial Protocol](https://docs.petoi.com/apis/serial-protocol) - BLE communication
- [Bleak BLE Library](https://bleak.readthedocs.io/) - Python Bluetooth LE client
- [Mellea Tool Use Examples](https://github.com/generative-computing/mellea/blob/main/sudoku_tool_based_2.py) - Tool calling patterns

## Design Rationale

### Why Mellea over manual tool calling?

**Schema-Driven Contracts**: Mellea generates JSON schemas from Python function signatures. The LLM receives exactly what fields are available, ensuring tool calls never fail due to missing parameters.

**Automatic Loop Management**: Multi-turn interactions (LLM → tool execution → next step) are handled transparently. No manual while-loops or message history management.

**Extensibility**: Adding a new tool is just adding a Python function. No need to modify tool definitions in multiple places.

**Local-First Design**: Ollama + Mellea means full privacy and control. No cloud dependencies, no API keys, no rate limits.

### Why Granite4.2:3b for tool use?

- **Lightweight**: Only 3B parameters, suitable for real-time control
- **Tool-Aware**: Trained on code generation and tool calling patterns
- **Fast**: Runs locally on modest hardware (even on robot's companion device)
- **Capable**: Handles complex reasoning for multi-step robot behaviors
- **Open**: No licensing restrictions for robotics projects

### Tool Design Philosophy

**Tools as Capabilities, Not Implementations**: Each tool defines *what the robot can do*, not *how to do it*. This separation allows:
- LLM to focus on reasoning and planning
- Controller to handle low-level details (Bluetooth, servo timing, etc.)
- Easy testing and iteration on either side independently

**Validation in Tools, Not LLM**: Motor angle bounds, connection checks, etc. are in the tool functions. This way the LLM's response is deterministic and we catch edge cases at execution time, not in the prompt.
