#!/usr/bin/env python3
"""
LLM-controlled Petoi Bittle using Mellea framework and backend controller.

Provides:
- Automatic tool orchestration with Claude or Ollama
- Full error handling and recovery
- Connection management
- Multi-turn conversation support
- Safety validation on all commands
"""

import asyncio
import json
import os
import sys
from typing import Optional, Any
import logging

try:
    from mellea import start_session
    from mellea.backends import ModelOption
    from mellea.stdlib.context import ChatContext
except ImportError:
    print("❌ Mellea not installed. Install with: pip install mellea")
    sys.exit(1)

from bittle_backend import BittleBackendController
from bittle_mellea_tools import BittleMelleaTools

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BitteleLLMController:
    """Bridge between Mellea LLM and Petoi Bittle robot with full backend support"""

    def __init__(
        self,
        bittle_address: Optional[str] = None,
        use_ollama: bool = False,
        model: str = "claude-opus-5",
        ollama_base_url: str = "http://localhost:11434",
        ollama_model: str = "granite4.2:3b",
    ):
        self.backend = BittleBackendController(address=bittle_address)
        self.tools = BittleMelleaTools(self.backend)
        self.use_ollama = use_ollama
        self.model = model
        self.ollama_base_url = ollama_base_url
        self.ollama_model = ollama_model
        self.conversation_history = []
        self.mellea = None
        self._initialize_mellea()

    def _initialize_mellea(self):
        """Initialize Mellea session with appropriate backend"""
        if self.use_ollama:
            logger.info(f"Initializing Mellea with Ollama backend: {self.ollama_model}")
            self.mellea = start_session(
                model_option=ModelOption(
                    provider="ollama",
                    model=self.ollama_model,
                    base_url=self.ollama_base_url,
                )
            )
        else:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                logger.warning("ANTHROPIC_API_KEY not set. Claude API may not work.")
            logger.info(f"Initializing Mellea with Anthropic backend: {self.model}")
            self.mellea = start_session(
                model_option=ModelOption(
                    provider="anthropic",
                    model=self.model,
                    api_key=api_key,
                )
            )

    async def connect(self) -> bool:
        """Connect to Bittle robot"""
        logger.info("Connecting to Bittle...")
        success = await self.backend.connect()
        if success:
            logger.info("✓ Successfully connected to Bittle")
            status = await self.backend.get_status()
            logger.info(f"Robot status: {status}")
        else:
            logger.error("❌ Failed to connect to Bittle")
        return success

    async def disconnect(self):
        """Disconnect from Bittle robot"""
        logger.info("Disconnecting from Bittle...")
        await self.backend.disconnect()

    async def chat(self, user_message: str) -> str:
        """
        Send message to LLM and execute tools automatically.

        The LLM processes the user message, calls appropriate tools,
        and returns a natural language response with results.
        """
        logger.info(f"User: {user_message}")

        self.conversation_history.append({"role": "user", "content": user_message})

        try:
            ctx = ChatContext(system_prompt=self.tools.get_system_prompt())

            for msg in self.conversation_history:
                if msg["role"] == "user":
                    ctx.add_user_message(msg["content"])
                elif msg["role"] == "assistant":
                    ctx.add_assistant_message(msg["content"])

            logger.info("🤔 Processing with LLM...")

            result = await asyncio.to_thread(
                self.mellea.instruct,
                ctx,
                tool_use=True,
                max_turns=5,
            )

            final_response = str(result)
            logger.info(f"Assistant: {final_response}")

            self.conversation_history.append({"role": "assistant", "content": final_response})

            return final_response

        except Exception as e:
            error_msg = f"Error processing request: {str(e)}"
            logger.error(error_msg)
            return error_msg

    async def direct_command(self, command: str, **kwargs) -> dict:
        """Execute tool directly without LLM (for testing)"""
        logger.info(f"Executing tool: {command} with args: {kwargs}")
        return await self.tools.execute_tool(command, **kwargs)

    async def interactive_loop(self):
        """Run interactive chat loop with connected Bittle"""
        print("\n" + "=" * 70)
        print("🤖 LLM-Controlled Petoi Bittle")
        print("=" * 70)
        print("Type commands in natural language (e.g., 'make Bittle dance')")
        print("Type 'exit' or 'quit' to exit")
        print("Type 'status' to check robot status")
        print("Type 'help' for help")
        print("=" * 70 + "\n")

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

                if user_input.lower() == "status":
                    status = await self.backend.get_status()
                    print(f"\n🤖 Robot Status:")
                    print(f"  Connected: {status.connected}")
                    print(f"  Battery: {status.battery_voltage}V" if status.battery_voltage else "  Battery: Unknown")
                    print(f"  Motion: {status.current_motion}")
                    print(f"  Timestamp: {status.timestamp}\n")
                    continue

                if user_input.lower() == "help":
                    self._print_help()
                    continue

                response = await self.chat(user_input)
                print(f"\n🤖 Bittle: {response}\n")

            except KeyboardInterrupt:
                print("\n\nInterrupted by user")
                break
            except Exception as e:
                logger.error(f"Error: {e}")
                print(f"❌ Error: {e}\n")

    def _print_help(self):
        """Print help information"""
        help_text = """
Commands:
  - Natural language: "Make Bittle dance", "Look around", "Are you okay?"
  - status: Check robot status
  - help: Show this help
  - exit/quit: Exit program

Example commands:
  - "Make Bittle sit down"
  - "Walk forward for a bit"
  - "Express confusion"
  - "Do a dance"
  - "Look around"
  - "How's the battery?"

The robot interprets your requests creatively and converts them to motions.
"""
        print(help_text)


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Control Petoi Bittle with LLM (Mellea-powered)"
    )
    parser.add_argument("--address", help="Bittle Bluetooth address (optional)")
    parser.add_argument(
        "--ollama",
        action="store_true",
        help="Use Ollama backend instead of Claude"
    )
    parser.add_argument(
        "--model",
        default="claude-opus-5",
        help="Claude model to use (default: claude-opus-5)"
    )
    parser.add_argument(
        "--ollama-base-url",
        default="http://localhost:11434",
        help="Ollama base URL (default: http://localhost:11434)"
    )
    parser.add_argument(
        "--ollama-model",
        default="granite4.2:3b",
        help="Ollama model to use (default: granite4.2:3b)"
    )

    args = parser.parse_args()

    controller = BitteleLLMController(
        bittle_address=args.address,
        use_ollama=args.ollama,
        model=args.model,
        ollama_base_url=args.ollama_base_url,
        ollama_model=args.ollama_model,
    )

    if not await controller.connect():
        print("\n❌ Failed to connect to Bittle")
        print("\nTroubleshooting:")
        print("  1. Ensure Bittle is powered on and in range")
        print("  2. Pair Bittle via Bluetooth settings")
        print("  3. For Claude: Set ANTHROPIC_API_KEY environment variable")
        print("  4. For Ollama: Start Ollama server (ollama serve)")
        sys.exit(1)

    try:
        await controller.interactive_loop()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    finally:
        await controller.disconnect()
        print("Program terminated.")


if __name__ == "__main__":
    asyncio.run(main())
