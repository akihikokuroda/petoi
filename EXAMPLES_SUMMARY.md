# Example Scripts Summary

Complete overview of all LLM-controlled Petoi Bittle example scripts.

## Quick Reference

| Script | Purpose | Complexity | Duration |
|--------|---------|-----------|----------|
| `llm_bittle_controller.py` | Interactive LLM chat | Medium | Continuous |
| `example_dance.py` | Dance choreography | Low | ~30s |
| `example_emotions.py` | Express emotions | Low | ~60s |
| `example_story.py` | Tell a narrative story | Medium | ~90s |
| `example_voice_commands.py` | Quick commands | Low | ~45s |
| `example_creative_poses.py` | Artistic positions | Medium | ~70s |
| `example_multi_step_task.py` | Complex scenarios | High | ~120s |
| `example_testing.py` | Validation & QA | High | ~60s |
| `example_advanced_integration.py` | Advanced patterns | High | ~150s |

---

## 1. Main Interactive Controller

**File:** `llm_bittle_controller.py`

**Purpose:** Primary interface for LLM-controlled Bittle

**Key Features:**
- Interactive chat loop
- Automatic tool discovery
- Conversation history
- Error handling
- Status monitoring

**How to Run:**
```bash
python llm_bittle_controller.py [optional_bittle_address]
```

**Example Interaction:**
```
You: Make Bittle stand up
You: Look around
You: Dance!
You: exit
```

**What It Teaches:**
- How to integrate Claude API with robot control
- Tool calling and result processing
- Conversation management
- Natural language interpretation

---

## 2. Dance Performance

**File:** `example_dance.py`

**Purpose:** Choreograph complex dance movements

**What It Does:**
1. Connects to Bittle
2. Interprets "dance" request
3. Creates motion sequences
4. Combines multiple gaits
5. Reports completion

**Output:**
```
🎵 Making Bittle dance...

🤖 Response: Bittle is now doing an energetic dance routine!
- Trotting left and right with rhythm
- Adding arm movements for expression
- Walking forward with style
- Dance complete! 💃
```

**What It Teaches:**
- Motion sequencing
- Gait selection
- Creative choreography
- Timing coordination

**Variations:**
- Try: "Slow waltz"
- Try: "Robot dance"
- Try: "Victory dance"

---

## 3. Emotion Expression

**File:** `example_emotions.py`

**Purpose:** Map emotions to physical movements

**Emotions Demonstrated:**
- Confused → Head tilting, uncertain movements
- Happy → Bouncing, trotting, upright posture
- Tired → Slow movements, sitting down
- Curious → Looking around, forward tilting
- Playful → Hopping, spinning, quick movements
- Angry → Aggressive stances, forward posture

**Output:**
```
==================================================
Expressing: confused
==================================================
🤖 Bittle looks confused - tilting its head left and right,
uncertain movements, and adjusting its posture...

==================================================
Expressing: happy
==================================================
🤖 Bittle is expressing happiness! Bouncing excitedly,
trotting in circles, and moving with a joyful energy...
```

**What It Teaches:**
- Semantic mapping (emotion → movement)
- Multi-motor coordination
- Sequential expression
- Personality simulation

**Extension Ideas:**
- Add more emotions (sad, shocked, proud)
- Combine emotions (happy but tired)
- Grade intensity (slightly happy vs. very happy)

---

## 4. Narrative Storytelling

**File:** `example_story.py`

**Purpose:** Act out a complete story through movement

**Story Arc:**
1. **Wake up** - Transition from sleep position
2. **Find food** - Search movements, looking around
3. **Fear** - Reaction to perceived danger
4. **Discovery** - Realizes it's a friend
5. **Play** - Interaction and play behavior
6. **Sleep** - Transition to rest

**Output:**
```
📖 Scene 1: Bittle wakes up in the morning...
🤖 Bittle is stretching after waking up, looking around
with a yawn, then standing up ready for the day!

📖 Scene 2: Bittle is very hungry...
🤖 Bittle is moving around searching for food, looking
left and right, sniffing and investigating...
```

**What It Teaches:**
- Narrative structure
- State transitions
- Context-aware behavior
- Sequential storytelling

**Extension Ideas:**
- Different story types (adventure, comedy, mystery)
- Branching narratives (user choices)
- Multi-character stories
- Recorded animations

---

## 5. Quick Voice Commands

**File:** `example_voice_commands.py`

**Purpose:** Rapid-fire natural language commands

**Commands Executed:**
- Stand up / Sit down
- Look left / Look right
- Walk forward / Walk backward
- Trot in circle
- Bow
- Stretch
- Do a little spin
- Sleep

**Output:**
```
🎤 Command: 'Stand up'
🤖 Bittle is now standing upright, ready for action! 👆

🎤 Command: 'Look left'
🤖 Bittle is looking to the left, checking things out...

🎤 Command: 'Walk forward a few steps'
🤖 Bittle is walking forward with confident strides...
```

**What It Teaches:**
- Quick interpretation
- Single-action execution
- Command variance handling
- Response efficiency

**Extension Ideas:**
- Custom command aliases
- Chained commands
- Speed variations
- Intensity modifiers

---

## 6. Creative Poses

**File:** `example_creative_poses.py`

**Purpose:** Create specific artistic positions

**Poses Demonstrated:**
- Yoga poses (downward dog)
- Thinking poses
- Laughing animations
- Heroic stances
- Greeting positions
- Surprise expressions
- Stretching routines

**Output:**
```
📝 Request: Make Bittle do a yoga pose...
🤖 Bittle is transitioning into a downward dog pose!
Rear raised, front lowered, very peaceful...

📝 Request: Create a pose where Bittle looks heroic...
🤖 Bittle is striking a heroic pose! Chest out, head high,
confident and ready for anything! 💪
```

**What It Teaches:**
- Static pose composition
- Motor positioning
- Artistic expression
- Balance and stability

**Extension Ideas:**
- Save pose library
- Blend between poses
- Pose transitions
- Stability checking

---

## 7. Multi-Step Complex Tasks

**File:** `example_multi_step_task.py`

**Purpose:** Execute complex scenarios with multiple steps

**Scenarios:**

### Patrol Routine
- Stand up
- Look around (surveillance)
- Walk forward (patrol)
- Report status

### Obstacle Avoidance
- Encounter obstacle
- React (stop, look down)
- Navigate around (step left/right)
- Resume motion

### Greeting Sequence
- Show excitement
- Perform greeting (bow/wave)
- Suggest activity

### Problem Solving
- Attempt to reach object
- Show frustration when failing
- Find clever solution

### Victory Celebration
- Celebrate success
- Happy movements
- Proud final pose

**Output:**
```
🚨 TASK 1: Patrol Routine
Bittle stands up and looks around the patrol area,
then walks forward with purpose, checking everything...

🚧 TASK 2: Obstacle Avoidance
Bittle encounters an obstacle, stops carefully,
then navigates around it with precision...
```

**What It Teaches:**
- Task decomposition
- State management
- Error recovery
- Complex choreography

**Extension Ideas:**
- Real sensor integration
- Adaptive behavior
- Learning from mistakes
- Performance optimization

---

## 8. Testing & Validation

**File:** `example_testing.py`

**Purpose:** Validate system functionality

**Tests:**

1. **Status Check** - Verify connection and readiness
2. **Motor Range** - Test extreme positions
3. **Walking Speed** - Validate different gaits
4. **Skills Validation** - Execute common behaviors
5. **Edge Cases** - Handle impossible requests gracefully
6. **Error Recovery** - Recover from errors

**Output:**
```
✓ TEST 1: Robot Status Check
Connected: true, Battery: 7.2V, Status: Idle ✓

✓ TEST 2: Motor Movement Range
Neck moved to extreme left (-90°)... Success
Neck moved to extreme right (+90°)... Success

✓ TEST 3: Walking Speed
Slow walk... Success
Fast trot... Success
Backward walk... Success

✓ TEST 4: Common Skills Validation
Sit... Success | Stand... Success | Stretch... Success

✓ TEST 5: Edge Case Handling
❌ Cannot move neck to 180° (outside range)
✓ Alternative: Move to 90° and create illusion
```

**What It Teaches:**
- System validation
- Edge case handling
- Error messages
- Quality assurance
- Graceful degradation

**Extension Ideas:**
- Automated regression testing
- Performance benchmarking
- Load testing
- Battery consumption analysis

---

## 9. Advanced Integration

**File:** `example_advanced_integration.py`

**Purpose:** Demonstrate advanced patterns and extensions

**Advanced Patterns:**

### Performance Tracking
- Log all motions
- Track frequency
- Save sequences
- Measure metrics

### Adaptive Behavior
- Context-aware decisions
- Resource management
- Audience adaptation
- Safety considerations

### Progressive Learning
- Step-by-step teaching
- Build complexity gradually
- Combine learned behaviors
- Refinement iterations

### Scenario-Based Behavior
- Morning routine
- Greeting behaviors
- Careful navigation
- Evening wind-down

### Creative Collaboration
- Multi-turn conversation
- Iterative refinement
- Personality development
- Expression personalization

**Output:**
```
📊 Example: Performance Tracking
Efficient dance routine created and saved!
Motion Log Summary:
  - STAND: 2x
  - TROT_LEFT: 3x
  - TROT_RIGHT: 3x
  - WALK_FORWARD: 1x

🧠 Example: Adaptive Behavior
Given confined space context:
Bittle is moving carefully and slowly, checking for obstacles...

🎓 Example: Progressive Learning
Step 1: Basic greeting (bow)
Step 2: Add arm movement
Step 3: Add step forward
...complete!

🎬 Example: Scenario-Based
Morning Routine: Bittle yawns, stretches, stands up...

🎨 Example: Creative Collaboration
[Turn 1] Show curious pose
[Turn 2] Add beep sound
[Turn 3] Investigate behavior
✨ Saved: 'curious_bittle' sequence
```

**What It Teaches:**
- Architecture patterns
- Custom tool integration
- State management
- Workflow design
- Advanced LLM usage

---

## Getting Started Path

### Day 1 - Basics
1. `QUICK_START.md` - Setup and overview
2. `llm_bittle_controller.py` - Interactive exploration
3. `example_voice_commands.py` - Simple commands

### Day 2 - Creative
1. `example_dance.py` - Complex sequences
2. `example_emotions.py` - Semantic mapping
3. `example_creative_poses.py` - Artistic expression

### Day 3 - Advanced
1. `example_story.py` - Narrative structure
2. `example_multi_step_task.py` - Task decomposition
3. `example_testing.py` - Quality assurance

### Day 4 - Expert
1. `example_advanced_integration.py` - Extended patterns
2. `LLM_CONTROLLER_DESIGN.md` - Architecture details
3. Custom extensions

---

## Common Patterns

### Pattern: Sequential Actions
```python
# Command multiple actions in sequence
"First sit down, then stand up, then walk forward"
```

### Pattern: Emotion Mapping
```python
# Express emotions through movement
"Look confused" → neck tilt + uncertain movements
"Be happy" → bouncing + trotting + upright
```

### Pattern: Narrative
```python
# Act out a story
"Show waking up, then looking for food, then sleeping"
```

### Pattern: Parameter Variation
```python
# Adjust intensity/duration
"Slowly look around" vs "Quickly look around"
"Gentle stretch" vs "Aggressive stretch"
```

### Pattern: Multi-Motor
```python
# Coordinate multiple motors
"Look left while stepping right" → neck + leg coordination
```

---

## Tips for Best Results

✓ **Be descriptive** - "express confusion" > "tilt neck"
✓ **Use emotions** - LLM excels at interpreting feelings
✓ **Combine actions** - Create rich narratives
✓ **Consider timing** - 0.3-0.5s for quick, 1-2s for slow
✓ **Think physically** - Remember motor limits (-90 to +90°)
✓ **Test first** - Validate with `example_testing.py`
✓ **Save sequences** - Reuse successful combinations
✓ **Iterate** - Refine through multiple interactions

---

## Troubleshooting Examples

### Issue: Motor not responding
```bash
# Run testing script
python example_testing.py
# Check motor index and angle range
```

### Issue: Slow response
```bash
# First request is slower (tool definitions included)
# Subsequent requests are cached and faster
```

### Issue: Lost connection
```bash
# Verify Bittle is powered
# Check Bluetooth pairing
# Retry connection
```

### Issue: LLM doesn't understand request
```bash
# Be more specific about physical movements
# Instead of "look happy", try "look happy by trotting and adjusting arms"
# Provide examples
```

---

## Next Steps

1. **Run examples** - Try each one to understand capabilities
2. **Modify examples** - Change prompts and parameters
3. **Combine patterns** - Mix ideas from different examples
4. **Create custom** - Write your own scenarios
5. **Deploy** - Use in production with proper error handling

---

## File Index

```
petoi/
├── QUICK_START.md                     # Start here
├── EXAMPLES_SUMMARY.md                # This file
├── LLM_CONTROLLER_DESIGN.md           # Architecture
├── LLM_EXAMPLES_README.md             # Full docs
│
├── llm_bittle_controller.py           # Main controller
├── example_dance.py                   # 🎵 Dancing
├── example_emotions.py                # 😊 Emotions
├── example_story.py                   # 📖 Story
├── example_voice_commands.py          # 🎤 Quick commands
├── example_creative_poses.py          # 🎨 Artistic poses
├── example_multi_step_task.py         # ⚙️  Complex tasks
├── example_testing.py                 # 🧪 Validation
├── example_advanced_integration.py    # 🚀 Advanced
│
└── petoi_bittle_controller.py         # Low-level API
```

---

**Happy exploring! 🤖✨**
