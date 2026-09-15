#!/usr/bin/env python3
"""
Example: LLM-controlled Bittle with natural language commands.

Shows how to use the BitteleLLMController for interactive control.

Usage:
    # With Claude backend (default)
    ANTHROPIC_API_KEY=your-key python3 example_llm_control.py

    # With Ollama backend
    python3 example_llm_control.py --ollama
"""

import asyncio
import sys
from bittle_llm_controller import BitteleLLMController


async def example_basic_commands():
    """Example 1: Basic commands with Claude"""
    print("\n" + "=" * 70)
    print("Example 1: Basic Commands")
    print("=" * 70)

    controller = BitteleLLMController(use_ollama=False)

    if not await controller.connect():
        print("Failed to connect to Bittle")
        return

    try:
        commands = [
            "Make Bittle sit down",
            "Stand up",
            "Look around",
        ]

        for cmd in commands:
            print(f"\nUser: {cmd}")
            response = await controller.chat(cmd)
            print(f"Bittle: {response}")
            await asyncio.sleep(1)

    finally:
        await controller.disconnect()


async def example_complex_sequences():
    """Example 2: Complex motion sequences"""
    print("\n" + "=" * 70)
    print("Example 2: Complex Motion Sequences")
    print("=" * 70)

    controller = BitteleLLMController(use_ollama=False)

    if not await controller.connect():
        print("Failed to connect to Bittle")
        return

    try:
        commands = [
            "Can you dance?",
            "Express confusion",
            "Show me what you can do",
        ]

        for cmd in commands:
            print(f"\nUser: {cmd}")
            response = await controller.chat(cmd)
            print(f"Bittle: {response}")
            await asyncio.sleep(2)

    finally:
        await controller.disconnect()


async def example_status_queries():
    """Example 3: Status checking and feedback"""
    print("\n" + "=" * 70)
    print("Example 3: Status Queries")
    print("=" * 70)

    controller = BitteleLLMController(use_ollama=False)

    if not await controller.connect():
        print("Failed to connect to Bittle")
        return

    try:
        commands = [
            "How's the battery?",
            "Are you okay?",
            "What's your status?",
        ]

        for cmd in commands:
            print(f"\nUser: {cmd}")
            response = await controller.chat(cmd)
            print(f"Bittle: {response}")
            await asyncio.sleep(1)

    finally:
        await controller.disconnect()


async def example_multi_turn_conversation():
    """Example 4: Multi-turn conversation"""
    print("\n" + "=" * 70)
    print("Example 4: Multi-Turn Conversation")
    print("=" * 70)

    controller = BitteleLLMController(use_ollama=False)

    if not await controller.connect():
        print("Failed to connect to Bittle")
        return

    try:
        # This is a single conversation - context persists
        print("\n[Conversation about Bittle's mood and capabilities]")

        response = await controller.chat("Hey Bittle, how are you feeling?")
        print(f"\nUser: Hey Bittle, how are you feeling?")
        print(f"Bittle: {response}")

        response = await controller.chat("Can you show me some emotions?")
        print(f"\nUser: Can you show me some emotions?")
        print(f"Bittle: {response}")

        response = await controller.chat("That was cool! Can you do something different?")
        print(f"\nUser: That was cool! Can you do something different?")
        print(f"Bittle: {response}")

    finally:
        await controller.disconnect()


async def example_direct_tool_calling():
    """Example 5: Direct tool execution for testing"""
    print("\n" + "=" * 70)
    print("Example 5: Direct Tool Execution (Testing)")
    print("=" * 70)

    controller = BitteleLLMController(use_ollama=False)

    if not await controller.connect():
        print("Failed to connect to Bittle")
        return

    try:
        # Direct tool calls without going through LLM
        print("\n[Testing individual tools directly]")

        print("\n1. Execute skill (sit)")
        result = await controller.direct_command("bittle_execute_skill", skill_name="sit")
        print(f"Result: {result}")

        print("\n2. Control motor (neck to 45 degrees)")
        result = await controller.direct_command(
            "bittle_control_motor",
            motor_name="neck",
            angle=45
        )
        print(f"Result: {result}")

        print("\n3. Get status")
        result = await controller.direct_command("bittle_get_status")
        print(f"Result: {result}")

        print("\n4. Beep")
        result = await controller.direct_command("bittle_beep", frequency=1000, duration=100)
        print(f"Result: {result}")

    finally:
        await controller.disconnect()


async def example_with_ollama():
    """Example 6: Using Ollama backend instead of Claude"""
    print("\n" + "=" * 70)
    print("Example 6: Using Ollama Backend")
    print("=" * 70)
    print("Make sure Ollama is running: ollama serve")
    print("And granite model is pulled: ollama pull granite4.2:3b")

    controller = BitteleLLMController(
        use_ollama=True,
        ollama_base_url="http://localhost:11434",
        ollama_model="granite4.2:3b"
    )

    if not await controller.connect():
        print("Failed to connect to Bittle")
        return

    try:
        commands = [
            "Make Bittle sit",
            "Look around",
            "Dance",
        ]

        for cmd in commands:
            print(f"\nUser: {cmd}")
            response = await controller.chat(cmd)
            print(f"Bittle (via Ollama): {response}")
            await asyncio.sleep(1)

    finally:
        await controller.disconnect()


async def example_error_handling():
    """Example 7: Error handling"""
    print("\n" + "=" * 70)
    print("Example 7: Error Handling")
    print("=" * 70)

    controller = BitteleLLMController(use_ollama=False)

    if not await controller.connect():
        print("Failed to connect to Bittle")
        return

    try:
        # These commands should produce helpful error messages
        print("\n[Testing error handling with invalid commands]")

        print("\n1. Invalid skill")
        response = await controller.chat("Make Bittle do the invalid_move")
        print(f"Bittle: {response}")

        print("\n2. Physical impossibility")
        response = await controller.chat("Bend your neck 180 degrees")
        print(f"Bittle: {response}")

        print("\n3. Valid recovery")
        response = await controller.chat("Instead, look left")
        print(f"Bittle: {response}")

    finally:
        await controller.disconnect()


async def main():
    """Run all examples or a specific one"""
    if len(sys.argv) > 1:
        example_num = sys.argv[1]
        if example_num == "1":
            await example_basic_commands()
        elif example_num == "2":
            await example_complex_sequences()
        elif example_num == "3":
            await example_status_queries()
        elif example_num == "4":
            await example_multi_turn_conversation()
        elif example_num == "5":
            await example_direct_tool_calling()
        elif example_num == "6":
            await example_with_ollama()
        elif example_num == "7":
            await example_error_handling()
        else:
            print(f"Unknown example: {example_num}")
            print("Available examples: 1-7")
    else:
        print("\n" + "=" * 70)
        print("Bittle LLM Controller - Examples")
        print("=" * 70)
        print("\nUsage: python3 example_llm_control.py [1-7]")
        print("\nExamples:")
        print("  1 - Basic Commands")
        print("  2 - Complex Motion Sequences")
        print("  3 - Status Queries")
        print("  4 - Multi-Turn Conversation")
        print("  5 - Direct Tool Execution")
        print("  6 - Ollama Backend")
        print("  7 - Error Handling")
        print("\nRun with --interactive for interactive mode")

        if "--interactive" in sys.argv:
            print("\n" + "=" * 70)
            print("Interactive Mode")
            print("=" * 70)

            controller = BitteleLLMController(use_ollama=False)
            if await controller.connect():
                try:
                    await controller.interactive_loop()
                finally:
                    await controller.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
