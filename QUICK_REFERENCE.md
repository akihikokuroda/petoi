# Bittle LLM Controller - Quick Reference

## Installation

```bash
pip install bleak mellea anthropic
```

## Quick Start

```python
import asyncio
from bittle_llm_controller import BitteleLLMController

async def main():
    controller = BitteleLLMController()
    await controller.connect()
    response = await controller.chat("Make Bittle dance")
    print(response)
    await controller.disconnect()

asyncio.run(main())
```

## Available Motors

| Name | Index | Range |
|------|-------|-------|
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

`sit`, `stand`, `walk_forward`, `walk_backward`, `walk_left`, `walk_right`, `trot_forward`, `trot_backward`, `trot_left`, `trot_right`, `balance`, `stretch`, `pee`, `rest`, `sleep`, `idle`, `pick_up_left`, `pick_up_right`

## Tools

### bittle_execute_skill
Execute a predefined skill.
```python
result = await controller.direct_command("bittle_execute_skill", skill_name="sit")
```

### bittle_control_motor
Control individual motor.
```python
result = await controller.direct_command(
    "bittle_control_motor",
    motor_name="neck",
    angle=45,
    duration=0.1
)
```

### bittle_sequence_motion
Execute timed sequence.
```python
sequence = [
    {"skill": "sit", "duration": 1.0},
    {"motor": "neck", "angle": 30, "duration": 0.5},
]
result = await controller.direct_command("bittle_sequence_motion", sequence=sequence)
```

### bittle_get_status
Get robot status.
```python
result = await controller.direct_command("bittle_get_status")
```

### bittle_beep
Make robot beep.
```python
result = await controller.direct_command(
    "bittle_beep",
    frequency=1000,
    duration=100
)
```

### bittle_calibrate_motor
Calibrate motor.
```python
result = await controller.direct_command(
    "bittle_calibrate_motor",
    motor_name="neck",
    offset=5
)
```

## Common Commands

```python
# Chat with LLM
response = await controller.chat("Make Bittle dance")

# Direct tool execution
result = await controller.direct_command("bittle_execute_skill", skill_name="sit")

# Check status
status = await controller.backend.get_status()

# Emergency stop
await controller.backend.emergency_stop()
```

## Configuration

### Claude Backend
```python
controller = BitteleLLMController(
    use_ollama=False,
    model="claude-opus-5"
)
```

### Ollama Backend
```python
controller = BitteleLLMController(
    use_ollama=True,
    ollama_base_url="http://localhost:11434",
    ollama_model="granite4.2:3b"
)
```

### Specific Device
```python
controller = BitteleLLMController(
    bittle_address="AA:BB:CC:DD:EE:FF"
)
```

## Error Handling

```python
if not await controller.connect():
    print("Failed to connect")
    return

try:
    response = await controller.chat("command")
except Exception as e:
    print(f"Error: {e}")
finally:
    await controller.disconnect()
```

## Testing

```bash
# Unit tests
python3 -m pytest test_bittle_backend.py -v

# Integration tests
python3 -m pytest test_bittle_integration.py -v

# End-to-end tests (mocked)
python3 -m pytest test_e2e_mock.py -v
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection fails | Ensure Bittle powered on, paired via Bluetooth |
| Claude API error | Set `ANTHROPIC_API_KEY` environment variable |
| Ollama not responding | Run `ollama serve`, pull `granite4.2:3b` |
| Motor won't move | Check angle is -90 to +90 degrees |
| Sequence interrupted | Check `is_sequence_running` flag |

## Safety Limits

- Motor angles: -90° to +90°
- Beep frequency: 20Hz to 20kHz
- Command delay: ≥ 50ms
- Connection timeout: 10 seconds
- Battery warning: < 6.0V
- Max agentic turns: 5

## File Reference

| File | Purpose |
|------|---------|
| `bittle_backend.py` | Core controller |
| `bittle_mellea_tools.py` | Tool definitions |
| `bittle_llm_controller.py` | LLM integration |
| `test_bittle_backend.py` | Unit tests |
| `test_bittle_integration.py` | Integration tests |
| `test_e2e_mock.py` | E2E with mocks |
| `example_llm_control.py` | Usage examples |
| `BACKEND_IMPLEMENTATION.md` | Full documentation |
| `DEVELOPMENT_GUIDE.md` | Developer guide |

## Links

- [Petoi Documentation](https://docs.petoi.com/)
- [Mellea GitHub](https://github.com/generative-computing/mellea)
- [Claude API Docs](https://docs.anthropic.com/)
- [Ollama GitHub](https://github.com/ollama/ollama)
