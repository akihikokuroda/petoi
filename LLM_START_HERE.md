# 🤖 LLM-Controlled Petoi Bittle - START HERE

Welcome! This guide will help you get started with LLM-controlled Petoi Bittle.

## 📋 What You'll Find

This directory contains everything needed to control your Petoi Bittle robot using Claude AI through natural language commands.

### Core Files

| File | Purpose |
|------|---------|
| **QUICK_START.md** | ⚡ 5-minute setup guide |
| **LLM_CONTROLLER_DESIGN.md** | 🏗️ Complete architecture & tools |
| **LLM_EXAMPLES_README.md** | 📚 Full documentation |
| **EXAMPLES_SUMMARY.md** | 📖 All examples explained |

### Main Script

| File | Purpose |
|------|---------|
| **llm_bittle_controller.py** | 🎮 Interactive LLM chat interface |

### Example Scripts

| File | What It Does | Complexity |
|------|-------------|-----------|
| **example_dance.py** | Make Bittle dance | 🟢 Easy |
| **example_emotions.py** | Express emotions | 🟢 Easy |
| **example_story.py** | Tell a story | 🟡 Medium |
| **example_voice_commands.py** | Quick commands | 🟢 Easy |
| **example_creative_poses.py** | Artistic poses | 🟡 Medium |
| **example_multi_step_task.py** | Complex scenarios | 🔴 Hard |
| **example_testing.py** | Validate setup | 🔴 Hard |
| **example_advanced_integration.py** | Advanced patterns | 🔴 Hard |

### Helper Script

| File | Purpose |
|------|---------|
| **run_examples.sh** | 🚀 Interactive menu launcher |

---

## 🚀 Quick Start (30 seconds)

### 1. Install & Setup
```bash
pip install bleak anthropic
export ANTHROPIC_API_KEY="your-key-here"
```

### 2. Run Interactive Chat
```bash
python llm_bittle_controller.py
```

### 3. Try Commands
```
You: Make Bittle stand up
You: Look around
You: Dance!
You: exit
```

---

## 📖 Guided Learning Path

### ⏱️ 5 Minutes
- Read this file
- Read `QUICK_START.md`

### ⏱️ 15 Minutes
- Run: `python llm_bittle_controller.py`
- Try basic commands

### ⏱️ 30 Minutes
- Run: `python example_voice_commands.py`
- Run: `python example_emotions.py`

### ⏱️ 1 Hour
- Run: `python example_dance.py`
- Run: `python example_creative_poses.py`
- Experiment with custom prompts

### ⏱️ 2+ Hours
- Read: `LLM_CONTROLLER_DESIGN.md`
- Run: `python example_story.py`
- Run: `python example_multi_step_task.py`
- Explore advanced examples

---

## 🎯 Common Use Cases

### "I just want to play with Bittle"
👉 Run: `python llm_bittle_controller.py`
- Type natural language commands
- No setup needed (other than API key)

### "I want to see what it can do"
👉 Run: `./run_examples.sh` or `bash run_examples.sh`
- Interactive menu
- All examples in one place

### "I want to understand how it works"
👉 Read:
1. `QUICK_START.md` (5 min)
2. `LLM_CONTROLLER_DESIGN.md` (30 min)
3. `llm_bittle_controller.py` (20 min code review)

### "I want to build something custom"
👉 Study:
1. `example_dance.py` - How to create sequences
2. `example_multi_step_task.py` - How to handle complex logic
3. `example_advanced_integration.py` - How to extend
4. Then modify and create your own!

---

## 🛠️ System Architecture

```
Your Command (Natural Language)
           ↓
    LLMBittleController
           ↓
      Claude API (LLM)
           ↓
    Tool Calls (execute_skill, control_motor, etc.)
           ↓
    Process Tool Calls
           ↓
  Petoi Bittle (BLE Commands)
           ↓
    Robot Movements
           ↓
    Feedback Loop
           ↓
  Natural Language Response
```

---

## 🔧 Available Tools

The LLM can use these tools:

1. **Execute Skills** - Run predefined behaviors (sit, stand, walk, etc.)
2. **Control Motors** - Fine-tune servo angles (-90° to +90°)
3. **Sequence Motions** - Chain movements with timing
4. **Get Status** - Check battery and connection
5. **Beep** - Make sound effects

---

## 📚 Documentation Files

### For Getting Started
- **QUICK_START.md** - Fastest way to get running
- **LLM_EXAMPLES_README.md** - What each example does

### For Understanding
- **LLM_CONTROLLER_DESIGN.md** - Complete design & architecture
- **EXAMPLES_SUMMARY.md** - Detailed breakdown of each example

### For Reference
- **LLM_START_HERE.md** - This file

---

## 💡 Examples at a Glance

### 🎵 Dance
```bash
python example_dance.py
# Result: Bittle does an energetic dance routine
```

### 😊 Emotions
```bash
python example_emotions.py
# Result: Bittle expresses various emotions through movement
```

### 📖 Story
```bash
python example_story.py
# Result: Bittle acts out a complete narrative story
```

### 🎤 Voice Commands
```bash
python example_voice_commands.py
# Result: Quick commands executed sequentially
```

### 🎨 Creative Poses
```bash
python example_creative_poses.py
# Result: Artistic and expressive poses
```

### ⚙️ Complex Tasks
```bash
python example_multi_step_task.py
# Result: Multi-step scenarios with context
```

### 🧪 Testing
```bash
python example_testing.py
# Result: Validates all systems working
```

### 🚀 Advanced
```bash
python example_advanced_integration.py
# Result: Extended patterns and custom tools
```

---

## 🎓 What You'll Learn

### Beginner
- How to use the interactive chat
- Natural language command structure
- Basic Bittle movements

### Intermediate
- How to create motion sequences
- Emotion mapping techniques
- Story structure and narrative

### Advanced
- Custom tool integration
- State management
- Performance optimization
- Multi-turn conversation flows

---

## 📋 Checklist

Before you start:
- [ ] Python 3.7+ installed
- [ ] `pip install bleak anthropic` run
- [ ] API key set (`export ANTHROPIC_API_KEY=...`)
- [ ] Bittle powered on and Bluetooth enabled
- [ ] Bittle paired to your computer

Ready to go:
- [ ] Run `python llm_bittle_controller.py`
- [ ] Say "Stand up"
- [ ] Enjoy! 🎉

---

## ❓ FAQ

### Q: Do I need to understand Python?
**A:** No! You can just run the examples. To customize them, basic understanding helps.

### Q: Can I use this without Bluetooth?
**A:** The current implementation requires Bluetooth LE. No workaround available.

### Q: How much does Claude API cost?
**A:** Pricing varies by model. Check https://claude.ai/pricing

### Q: Can I control multiple Bittle robots?
**A:** Current implementation handles one. Multi-robot support is a possible extension.

### Q: Does Bittle need to be connected to WiFi?
**A:** No, only Bluetooth LE is needed.

### Q: Can I record and replay motions?
**A:** Partially - see `example_advanced_integration.py` for sequence saving.

---

## 🚨 Troubleshooting

### "Bittle not found"
```bash
# 1. Ensure Bittle is powered on
# 2. Check Bluetooth settings
# 3. Verify pairing
# 4. Check distance (within 10m)
```

### "API key not set"
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### "Connection refused"
- Restart Bittle
- Unpair and re-pair via Bluetooth settings
- Try running `example_testing.py`

### "Slow responses"
- First request includes tool definitions (slower)
- Subsequent requests are faster (cached)
- Check internet connection

---

## 🌟 Next Steps

1. **Install & Run** (5 min)
   ```bash
   pip install bleak anthropic
   export ANTHROPIC_API_KEY="your-key"
   python llm_bittle_controller.py
   ```

2. **Explore Examples** (30 min)
   ```bash
   python example_dance.py
   python example_emotions.py
   python example_story.py
   ```

3. **Read Documentation** (1 hour)
   - QUICK_START.md
   - LLM_CONTROLLER_DESIGN.md

4. **Build Custom Behavior** (varies)
   - Modify examples
   - Create new scripts
   - Extend with custom tools

---

## 📞 Support

- 📖 Full docs: `LLM_EXAMPLES_README.md`
- 🏗️ Architecture: `LLM_CONTROLLER_DESIGN.md`
- 💻 Robot API: `petoi_bittle_controller.py`
- 🤖 Petoi docs: https://docs.petoi.com
- 🧠 Claude docs: https://docs.anthropic.com

---

## 🎉 Ready to Start?

### Option 1: Interactive (Recommended)
```bash
python llm_bittle_controller.py
```

### Option 2: Menu Launcher
```bash
./run_examples.sh
# or
bash run_examples.sh
```

### Option 3: Run Examples Directly
```bash
python example_dance.py
python example_emotions.py
# ... etc
```

---

**Let's make Bittle dance! 🤖💃**

Questions? Check `LLM_EXAMPLES_README.md` or `LLM_CONTROLLER_DESIGN.md`
