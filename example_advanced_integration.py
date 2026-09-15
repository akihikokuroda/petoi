#!/usr/bin/env python3
"""
Example: Advanced integration patterns
Shows how to extend LLM controller with custom tools and workflows
"""

import asyncio
import json
import sys
import os
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

# Try to import the Mellea version first, fall back to Claude API version
try:
    from llm_bittle_controller_mellea import LLMBittleController as BaseLLMBittleController
    USING_MELLEA = True
except ImportError:
    from llm_bittle_controller import LLMBittleController as BaseLLMBittleController
    USING_MELLEA = False


class AdvancedBittleController(BaseLLMBittleController):
    """Extended controller with custom tools"""

    def __init__(self, bittle_address=None, use_ollama=False):
        if USING_MELLEA:
            super().__init__(bittle_address, use_ollama=use_ollama)
        else:
            super().__init__(bittle_address)
        self.motion_log = []
        self.command_count = 0

    def log_motion(self, action: str, details: str):
        """Log motion for analysis"""
        self.motion_log.append(
            {
                "timestamp": datetime.now().isoformat(),
                "action": action,
                "details": details,
            }
        )

    def get_motion_summary(self) -> str:
        """Generate summary of performed motions"""
        if not self.motion_log:
            return "No motions logged yet"

        actions = {}
        for entry in self.motion_log:
            action = entry["action"]
            actions[action] = actions.get(action, 0) + 1

        summary = "Motion Summary:\n"
        for action, count in sorted(actions.items()):
            summary += f"  - {action}: {count}x\n"

        return summary

    def get_tools(self):
        """Override to add custom tools"""
        base_tools = super().get_tools()

        # Add custom tools
        custom_tools = [
            {
                "name": "get_motion_log",
                "description": "Get a summary of all motions performed",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "save_motion_sequence",
                "description": "Save the current session as a reusable motion sequence",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name for this motion sequence",
                        },
                        "description": {
                            "type": "string",
                            "description": "What this sequence does",
                        },
                    },
                    "required": ["name"],
                },
            },
            {
                "name": "time_motion",
                "description": "Measure performance metrics",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "metric_type": {
                            "type": "string",
                            "enum": ["response_time", "command_count", "battery_efficient"],
                            "description": "Type of metric to track",
                        },
                    },
                },
            },
        ]

        return base_tools + custom_tools

    async def process_tool_call(self, tool_name: str, tool_input: dict) -> str:
        """Override to handle custom tools"""
        if tool_name == "get_motion_log":
            return json.dumps(
                {"success": True, "message": self.get_motion_summary()}
            )

        elif tool_name == "save_motion_sequence":
            sequence_name = tool_input.get("name", "unnamed")
            description = tool_input.get("description", "")
            self.log_motion("SAVE_SEQUENCE", f"{sequence_name}: {description}")
            return json.dumps(
                {
                    "success": True,
                    "message": f"Saved sequence: {sequence_name}",
                    "session_duration": len(self.motion_log),
                }
            )

        elif tool_name == "time_motion":
            metric_type = tool_input.get("metric_type", "command_count")
            if metric_type == "command_count":
                return json.dumps(
                    {
                        "success": True,
                        "metric": metric_type,
                        "value": len(self.motion_log),
                    }
                )
            return json.dumps(
                {
                    "success": False,
                    "message": f"Metric type not implemented: {metric_type}",
                }
            )

        else:
            # Call parent for standard tools
            return await super().process_tool_call(tool_name, tool_input)


async def example_performance_tracking():
    """Track performance of motions"""
    print("\n" + "=" * 70)
    print("📊 Example: Performance Tracking")
    print("=" * 70)

    controller = AdvancedBittleController()

    if not await controller.connect():
        print("❌ Failed to connect")
        return

    try:
        # Request performance-aware choreography
        response = await controller.chat(
            """Create an efficient dance routine.
            After each major movement, check the motion log.
            Save this as 'efficient_dance_routine' when complete."""
        )
        print(f"\n🤖 {response}\n")

        # Show summary
        print(controller.get_motion_summary())

    finally:
        await controller.disconnect()


async def example_adaptive_behavior():
    """Demonstrate adaptive behavior based on context"""
    print("\n" + "=" * 70)
    print("🧠 Example: Adaptive Behavior")
    print("=" * 70)

    controller = AdvancedBittleController()

    if not await controller.connect():
        print("❌ Failed to connect")
        return

    try:
        # Context-aware behavior
        contexts = [
            ("Bittle is in a small confined space", "Move carefully and slowly"),
            (
                "Bittle has 30% battery remaining",
                "Conserve energy with minimal movements",
            ),
            ("Bittle is performing in front of an audience", "Be expressive and bold"),
            ("Bittle is playing with children", "Be gentle and playful"),
        ]

        for context, behavior_hint in contexts:
            print(f"\n📍 Context: {context}")
            print(f"💡 Suggested behavior: {behavior_hint}")
            print("-" * 70)

            prompt = f"""Given this context: {context}

            Respond with: {behavior_hint}

            Show 1-2 movements that reflect this context."""

            response = await controller.chat(prompt)
            print(f"🤖 {response}")
            await asyncio.sleep(1)

    finally:
        await controller.disconnect()


async def example_learning_sequence():
    """Build a learning sequence"""
    print("\n" + "=" * 70)
    print("🎓 Example: Progressive Learning")
    print("=" * 70)

    controller = AdvancedBittleController()

    if not await controller.connect():
        print("❌ Failed to connect")
        return

    try:
        progression = [
            "Teach Bittle a basic greeting (bow or head nod)",
            "Add arm movement to the greeting",
            "Combine greeting with a small step forward",
            "Add a beep sound to make it more interesting",
            "Repeat the complete greeting sequence",
            "Now teach Bittle a goodbye (reverse of greeting)",
        ]

        print("\n🎓 Building a greeting routine step by step:\n")

        for i, step in enumerate(progression, 1):
            print(f"Step {i}: {step}")
            print("-" * 70)

            response = await controller.chat(step)
            print(f"🤖 {response}\n")

            await asyncio.sleep(1)

        # Now use both together
        print("\n✨ Combining greeting and goodbye:")
        print("-" * 70)
        response = await controller.chat(
            "Show the complete greeting routine followed by the goodbye routine"
        )
        print(f"🤖 {response}\n")

    finally:
        await controller.disconnect()


async def example_scenario_based():
    """Scenario-based behavior"""
    print("\n" + "=" * 70)
    print("🎬 Example: Scenario-Based Behavior")
    print("=" * 70)

    controller = AdvancedBittleController()

    if not await controller.connect():
        print("❌ Failed to connect")
        return

    try:
        scenarios = [
            {
                "title": "Morning Routine",
                "context": "It's 8 AM and Bittle is just waking up",
                "task": "Show a morning wakeup sequence (yawn, stretch, stand up)",
            },
            {
                "title": "Excited Greeting",
                "context": "A friend just arrived",
                "task": "Show enthusiastic greeting with lots of movement",
            },
            {
                "title": "Careful Navigation",
                "context": "There are obstacles in the room",
                "task": "Walk carefully, checking left and right before each step",
            },
            {
                "title": "Tired Evening",
                "context": "It's late and Bittle had a long day",
                "task": "Show slow movements, maybe a yawn, and prepare for sleep",
            },
        ]

        for scenario in scenarios:
            print(f"\n🎬 Scenario: {scenario['title']}")
            print(f"📍 Context: {scenario['context']}")
            print(f"📋 Task: {scenario['task']}")
            print("-" * 70)

            response = await controller.chat(scenario["task"])
            print(f"🤖 {response}\n")

            await asyncio.sleep(1.5)

    finally:
        await controller.disconnect()


async def example_creative_collaboration():
    """Creative collaboration with multi-turn conversation"""
    print("\n" + "=" * 70)
    print("🎨 Example: Creative Collaboration")
    print("=" * 70)

    controller = AdvancedBittleController()

    if not await controller.connect():
        print("❌ Failed to connect")
        return

    try:
        # Multi-turn creative conversation
        turns = [
            ("Start", "Let's create a unique personality for Bittle. Show me a pose that reflects curiosity."),
            ("Enhance", "Great! Now add a sound to that. Make Bittle beep curiously."),
            ("Expand", "Perfect! Now show Bittle using that curious pose to investigate something interesting."),
            ("Refine", "That was great! Can you make the movements smoother and more graceful?"),
            ("Finalize", "Excellent! That's Bittle's signature curiosity behavior. Show it one more time with confidence."),
        ]

        for phase, prompt in turns:
            print(f"\n[{phase}]")
            print(f"Prompt: {prompt}")
            print("-" * 70)

            response = await controller.chat(prompt)
            print(f"🤖 {response}\n")

            await asyncio.sleep(1)

        # Save the result
        final_response = await controller.chat(
            "Save this personality as 'curious_bittle' sequence"
        )
        print(f"\n✨ Saved: {final_response}")

    finally:
        await controller.disconnect()


async def main():
    """Run advanced examples"""
    parser = argparse.ArgumentParser(description="Advanced LLM Bittle integration examples")
    parser.add_argument("--address", help="Bittle Bluetooth address (optional)")
    parser.add_argument("--ollama", action="store_true", help="Use Ollama backend instead of Claude")
    args = parser.parse_args()

    examples = [
        ("Performance Tracking", example_performance_tracking),
        ("Adaptive Behavior", example_adaptive_behavior),
        ("Learning Sequence", example_learning_sequence),
        ("Scenario-Based", example_scenario_based),
        ("Creative Collaboration", example_creative_collaboration),
    ]

    print("\n" + "=" * 70)
    print("🚀 Advanced LLM Bittle Integration Examples")
    print("=" * 70)
    print(f"Using: {'Mellea Framework' if USING_MELLEA else 'Claude API'}")
    print("\nAvailable examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")

    # Store args for example functions to use
    import builtins
    original_print = builtins.print
    example_args = args

    # Run all examples sequentially
    for name, example_func in examples:
        try:
            # Create controller with proper args
            controller = AdvancedBittleController(
                bittle_address=args.address,
                use_ollama=args.ollama if USING_MELLEA else False
            )
            await example_func()
            await asyncio.sleep(2)
        except Exception as e:
            print(f"❌ Error in {name}: {e}")

    print("\n" + "=" * 70)
    print("✅ All advanced examples completed!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
