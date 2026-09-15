# LLM-Controlled Petoi Bittle - Example Scripts

This directory contains example scripts demonstrating how to control a Petoi Bittle robot using Claude AI through natural language commands.

## Prerequisites

```bash
# Install required packages
pip install bleak anthropic

# Set your API key
export ANTHROPIC_API_KEY="your-api-key-here"
```

## Main Controller

### `llm_bittle_controller.py`

The core controller that bridges Claude API to Petoi Bittle.

**Features:**
- Connects to Bittle via Bluetooth LE
- Translates Claude tool calls to robot commands
- Maintains conversation history for context
- Provides interactive chat interface

**Usage:**
```bash
# Interactive mode
python llm_bittle_controller.py

# With specific Bittle address
python llm_bittle_controller.py "XX:XX:XX:XX:XX:XX"
```

**Interactive Commands:**
```
You: Make Bittle dance
🤖: [processes tool calls and responds]

You: Look around
🤖: [moves neck and reports]

You: exit
```

## Example Scripts

### 1. `example_dance.py` - Dance Performance

Makes Bittle perform energetic dance movements.

```bash
python example_dance.py
```

**What it does:**
- Creates complex motion sequences
- Combines multiple gaits (walking, trotting)
- Choreographs arm and body movements
- Demonstrates creative motion composition

---

### 2. `example_emotions.py` - Emotion Expression

Shows Bittle expressing different emotions through movement.

```bash
python example_emotions.py
```

**Emotions demonstrated:**
- Confused (head tilting)
- Happy (bouncing, trotting)
- Tired (slow movements, sitting)
- Curious (looking around)
- Playful (hopping, spinning)
- Angry (aggressive stances)

---

### 3. `example_story.py` - Narrative Storytelling

Tells a complete story where Bittle acts out scenes.

```bash
python example_story.py
```

**Story progression:**
1. Waking up in the morning
2. Looking for food
3. Seeing something scary
4. Discovering it's a friend
5. Playing together
6. Getting tired and sleeping

---

### 4. `example_voice_commands.py` - Quick Commands

Demonstrates natural language interpretation for rapid-fire commands.

```bash
python example_voice_commands.py
```

**Commands:**
- Stand up / Sit down
- Look left / Look right
- Walk forward / Trot in circle
- Bow / Stretch
- Spin / Sleep

---

### 5. `example_creative_poses.py` - Artistic Movements

Creates specific poses and artistic positions.

```bash
python example_creative_poses.py
```

**Poses include:**
- Yoga poses (downward dog)
- Thinking/pondering poses
- Laughing animations
- Heroic stances
- Greeting positions
- Surprise expressions
- Stretching routines

---

### 6. `example_multi_step_task.py` - Complex Scenarios

Demonstrates multi-step tasks with context and planning.

```bash
python example_multi_step_task.py
```

**Scenarios:**
1. **Patrol Routine** - Look around, walk, report
2. **Obstacle Avoidance** - Stop, analyze, navigate, continue
3. **Greeting Sequence** - Show excitement, bow, propose activity
4. **Problem Solving** - Try, fail, find clever solution
5. **Celebration** - Victory dance and proud pose

---

### 7. `example_testing.py` - Quality Assurance

Tests robot functionality and validates movements.

```bash
python example_testing.py
```

**Tests:**
1. Robot status verification
2. Motor range checking
3. Walking speed validation
4. Common skills verification
5. Edge case handling
6. Error recovery

---

## Architecture

```
User Input (Natural Language)
           ↓
    LLMBittleController
           ↓
      Claude API
    (tool_use loop)
           ↓
  Tool Calls (execute_skill, control_motor, etc.)
           ↓
    Process Tool Calls
           ↓
Petoi Bittle Robot (BLE Commands)
           ↓
    Robot Movements
           ↓
    Feedback to Claude
           ↓
    Natural Language Response
```

## Available Tools

The LLM has access to these tools:

### 1. `bittle_execute_skill`
Execute predefined behaviors like sit, stand, walk, etc.

### 2. `bittle_control_motor`
Fine-tune individual servo motors (-90° to +90°)

### 3. `bittle_sequence_motion`
Chain multiple movements with timing

### 4. `bittle_get_status`
Query robot status and battery level

### 5. `bittle_beep`
Make robot produce sound effects

## How It Works

### 1. Natural Language Input
```
"Make Bittle dance"
```

### 2. Claude Interpretation
Claude understands the request and decides which tools to use:
- Combine multiple skills
- Create motion sequences
- Add creative timing

### 3. Tool Calls
```json
[
  {"tool": "bittle_execute_skill", "params": {"skill_name": "stand"}},
  {"tool": "bittle_sequence_motion", "params": {...}}
]
```

### 4. Robot Execution
The controller executes each tool call, sending BLE commands to Bittle

### 5. Feedback Loop
Results are sent back to Claude for context-aware responses

### 6. Natural Language Response
```
"Bittle is now dancing! Moving forward with trotting, 
adding arm movements for rhythm..."
```

## Motor Reference

| Motor | Index | Range |
|-------|-------|-------|
| Neck | 0 | -90° to +90° |
| Left Shoulder | 8 | -90° to +90° |
| Right Shoulder | 9 | -90° to +90° |
| Right Hip | 10 | -90° to +90° |
| Left Hip | 11 | -90° to +90° |
| Left Arm | 12 | -90° to +90° |
| Right Arm | 13 | -90° to +90° |
| Right Ankle | 14 | -90° to +90° |
| Left Ankle | 15 | -90° to +90° |

## Available Skills

- `sit` - Sit down
- `stand` - Stand up
- `walk_forward` - Walk forward
- `walk_backward` - Walk backward
- `walk_left` / `walk_right` - Strafe
- `trot_forward` / `trot_backward` - Trot
- `trot_left` / `trot_right` - Trot strafe
- `balance` - Balance pose
- `stretch` - Stretch
- `pee` - Cute pose
- `rest` - Rest position
- `sleep` - Sleep mode
- `idle` - Idle/neutral
- `pick_up_left` / `pick_up_right` - Pickup poses

## Troubleshooting

### Connection Issues
```bash
# Ensure Bittle is powered on and paired
# Check Bluetooth connection
bluetoothctl devices

# Run without address for auto-discovery
python llm_bittle_controller.py
```

### API Key Issues
```bash
# Verify API key is set
echo $ANTHROPIC_API_KEY

# Or set it explicitly
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Slow Responses
- First request to Claude includes tool definitions (slower)
- Subsequent requests are faster (conversation cached)
- Bluetooth latency between commands is ~50-100ms

### Motor Not Responding
- Check motor index is correct
- Ensure angle is within -90 to +90 range
- Verify Bittle is powered and connected
- Try the status check: `python example_testing.py`

## Tips & Tricks

### Creating Smooth Animations
```python
# Use sequences with small timing intervals
sequence = [
    {"motor": "neck", "angle": -30, "duration": 0.3},
    {"motor": "neck", "angle": 30, "duration": 0.3},
    {"motor": "neck", "angle": 0, "duration": 0.3},
]
```

### Combining Skills and Motors
```python
# First execute a skill, then adjust
sequence = [
    {"skill": "stand", "duration": 0.5},
    {"motor": "neck", "angle": 45, "duration": 0.5},
    {"skill": "walk_forward", "duration": 2.0},
]
```

### Looping Behaviors
```python
# Use repeat parameter for looping
await controller.sequence_motion(sequence, repeat=3)
```

### Natural Language Descriptions
The LLM is creative - you don't need exact commands:
- ✓ "Make Bittle look around"
- ✓ "Express confusion"
- ✓ "Dance like you're happy"
- ✓ "Patrol the room"
- ✓ "React with excitement"

## Performance Metrics

| Operation | Time |
|-----------|------|
| Connect to Bittle | ~2-3s |
| Single motor command | ~50-100ms |
| Execute skill | ~500ms-2s |
| LLM response (first) | ~2-5s |
| LLM response (cached) | ~1-2s |
| Complete sequence (10 steps) | ~5-10s |

## Next Steps

### Learn More
- Read `LLM_CONTROLLER_DESIGN.md` for detailed architecture
- Check `petoi_bittle_controller.py` for low-level API
- Visit https://docs.petoi.com for official documentation

### Extend Functionality
- Add vision feedback (camera integration)
- Create custom skill library
- Build multi-robot choreography
- Implement reinforcement learning for motion optimization

### Production Deployment
- Add error recovery mechanisms
- Implement reconnection logic
- Create motion logging/playback
- Add scheduling for autonomous routines

## Support

For issues or questions:
1. Check troubleshooting section above
2. Run `example_testing.py` to validate setup
3. Review `LLM_CONTROLLER_DESIGN.md` for architecture
4. Visit https://docs.petoi.com for robot-specific issues

## License

Based on Petoi Bittle API and Anthropic Claude API.
