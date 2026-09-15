# Quick Start Guide - LLM Bittle Controller

Get up and running with LLM-controlled Petoi Bittle in 5 minutes.

## Installation

```bash
# Clone or navigate to the petoi directory
cd petoi

# Install dependencies
pip install bleak anthropic

# Set API key
export ANTHROPIC_API_KEY="your-key-here"
```

## 1. Interactive Chat (Recommended for First-Time Users)

```bash
python llm_bittle_controller.py
```

Then type natural language commands:
```
You: Make Bittle stand up
You: Look around
You: Dance!
You: exit
```

## 2. Run Example Scripts

### See Bittle Dance
```bash
python example_dance.py
```

### Express Emotions
```bash
python example_emotions.py
```

### Tell a Story
```bash
python example_story.py
```

### Quick Voice Commands
```bash
python example_voice_commands.py
```

### Artistic Poses
```bash
python example_creative_poses.py
```

### Complex Multi-Step Tasks
```bash
python example_multi_step_task.py
```

### Validate Everything Works
```bash
python example_testing.py
```

## Common Commands

### Motion
- "Stand up" / "Sit down"
- "Walk forward" / "Walk backward"
- "Trot left" / "Trot right"
- "Stretch"
- "Balance"

### Actions
- "Look left" / "Look right" / "Look around"
- "Bow"
- "Pick up something"
- "Spin"
- "Sleep"

### Emotions
- "Look confused"
- "Be happy"
- "Express anger"
- "Show surprise"
- "Look tired"

### Complex
- "Dance!"
- "Patrol the room"
- "Say hello"
- "Play dead"
- "Celebrate"

## File Structure

```
petoi/
├── llm_bittle_controller.py      # Main controller (START HERE)
├── example_dance.py               # Dancing demo
├── example_emotions.py            # Emotion expressions
├── example_story.py               # Narrative storytelling
├── example_voice_commands.py      # Quick commands
├── example_creative_poses.py      # Artistic poses
├── example_multi_step_task.py     # Complex scenarios
├── example_testing.py             # Validation suite
├── LLM_CONTROLLER_DESIGN.md       # Architecture details
├── LLM_EXAMPLES_README.md         # Full documentation
├── QUICK_START.md                 # This file
└── petoi_bittle_controller.py     # Low-level BLE API
```

## Troubleshooting

### "Bittle not found"
- Ensure Bittle is powered on
- Pair via Bluetooth settings
- Check distance (within 10m)

### "ANTHROPIC_API_KEY not set"
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### "Connection refused"
- Bittle may be paired with another device
- Unpair and re-pair
- Restart Bittle

### Slow responses
- First request is slower (includes tool definitions)
- Subsequent requests are faster (cached)
- Check internet connection

## Next Steps

1. **Run interactive controller** - Get familiar with the interface
2. **Try example scripts** - See different use cases
3. **Experiment with custom prompts** - Be creative!
4. **Read full docs** - Check `LLM_CONTROLLER_DESIGN.md`

## Tips

✓ **Be creative with descriptions** - "express confusion" is better than "tilt neck"
✓ **Use emotion-based prompts** - LLM excels at mapping emotions to movements
✓ **Combine multiple actions** - Create narratives and sequences
✓ **Check status first** - Validate connection before complex tasks
✓ **Use short durations** - 0.3-0.5s for snappy movements, 1-2s for slower ones

## Support

- 📖 Full docs: `LLM_EXAMPLES_README.md`
- 🏗️ Architecture: `LLM_CONTROLLER_DESIGN.md`
- 🤖 Robot API: `petoi_bittle_controller.py`
- 📝 Petoi docs: https://docs.petoi.com

## Example Session

```bash
$ export ANTHROPIC_API_KEY="sk-ant-..."
$ python llm_bittle_controller.py

✓ Connected to Bittle

🤖 LLM-Controlled Petoi Bittle
======================================================================
Type your commands in natural language (e.g., 'make Bittle dance')
Type 'exit' to quit

You: Stand up
🤔 Processing...
→ Calling tool: bittle_execute_skill
🤖 Bittle: Bittle is now standing up! Ready for action. 🤖

You: Look around slowly
🤔 Processing...
→ Calling tool: bittle_sequence_motion
🤖 Bittle: Bittle is looking around slowly, checking out its surroundings:
- Looks left (-45°)
- Center view
- Looks right (45°)
- Back to center
Complete! 👀

You: Dance!
🤔 Processing...
→ Calling tool: bittle_sequence_motion
🤖 Bittle: Bittle is dancing! 💃
Starting with a trot left, then trot right, arms moving rhythmically...
Dance complete!

You: exit
Goodbye! 👋
```

---

**Happy controlling! 🤖✨**
