#!/usr/bin/env python3
"""
Interactive Petoi Bittle Controller with Bluetooth LE (BLE)
Connects to the Bittle robot via Bluetooth Low Energy and sends commands.
Reference: https://docs.petoi.com/apis/serial-protocol
Based on: https://github.com/akihikokuroda/petoi/blob/main/bluetooth_testSkills.py
"""

import asyncio
import sys
from typing import Optional, Tuple
from enum import Enum

try:
    from bleak import BleakClient, BleakScanner
except ImportError:
    print("❌ Bleak not installed. Install with: pip install bleak")
    sys.exit(1)


class CommandType(Enum):
    """Enumeration of valid Bittle command types."""
    MOTOR = "m"
    SKILL = "k"
    CALIBRATE = "c"
    VOLTAGE = "v"
    QUIT = "q"
    BEEP = "b"


# Common skills for Bittle
SKILLS = {
    "sit": "ksit",
    "stand": "kstand",
    "walk_forward": "kwkF",
    "walk_backward": "kwkB",
    "walk_left": "kwkL",
    "walk_right": "kwkR",
    "trot_forward": "ktrF",
    "trot_backward": "ktrB",
    "trot_left": "ktrL",
    "trot_right": "ktrR",
    "balance": "kbalance",
    "stretch": "kstretch",
    "pee": "kpee",
    "rest": "krest",
    "sleep": "ksleep",
    "idle": "kidle",
    "pick_up_left": "kpickUpL",
    "pick_up_right": "kpickUpR",
}

# Motor indices and descriptions for Bittle X
# Based on BiBoard V1 joint pins
MOTOR_INDICES = {
    0: "Neck (Head tilt)",
    8: "Left shoulder",
    9: "Right shoulder",
    10: "Right hip",
    11: "Left hip",
    12: "Left arm",
    13: "Right arm",
    14: "Right ankle",
    15: "Left ankle",
}


class BittleBLEController:
    """Main controller for Petoi Bittle robot via Bluetooth LE."""

    def __init__(self, address: Optional[str] = None, command_delay: float = 0.1):
        """
        Initialize the Bittle BLE controller.

        Args:
            address: Bluetooth MAC address or UUID.
            command_delay: Delay between commands in seconds.
        """
        self.address = address
        self.command_delay = command_delay
        self.client: Optional[BleakClient] = None
        self.char = None
        self.connected = False

    async def discover_bittle(self) -> Optional[str]:
        """
        Discover Bittle device via Bluetooth LE.

        Returns:
            Device address if found, None otherwise.
        """
        print("Scanning for Bittle device...")
        try:
            devices = await BleakScanner.discover()
            print(f"Found {len(devices)} device(s):\n")

            for device in devices:
                print(f"  Name: {device.name}")
                print(f"  Address: {device.address}")

                if device.name and "Bittle" in device.name:
                    print(f"✓ Bittle found: {device.name} ({device.address})")
                    return device.address

            print("❌ Bittle device not found")
            return None
        except Exception as e:
            print(f"❌ Discovery failed: {e}")
            return None

    async def find_writable_characteristic(self):
        """
        Scan GATT services to find a writable characteristic.

        Returns:
            Characteristic UUID or None.
        """
        try:
            for service in self.client.services:
                for char in service.characteristics:
                    if "write" in char.properties:
                        print(f"Found writable characteristic: {char.uuid}")
                        return char
            return None
        except Exception as e:
            print(f"❌ Failed to find characteristic: {e}")
            return None

    async def connect(self) -> bool:
        """
        Connect to the Bittle robot via Bluetooth LE.

        Returns:
            True if connection successful, False otherwise.
        """
        try:
            if self.address is None:
                self.address = await self.discover_bittle()
                if self.address is None:
                    return False

            print(f"\nConnecting to {self.address}...")
            self.client = BleakClient(self.address)
            await self.client.connect()
            self.connected = True
            print(f"✓ Connected to Bittle")

            # Find writable characteristic
            self.char = await self.find_writable_characteristic()
            if not self.char:
                print("❌ Could not find writable characteristic")
                await self.disconnect()
                return False

            await asyncio.sleep(0.5)
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False

    async def disconnect(self):
        """Disconnect from the Bittle."""
        if self.client:
            try:
                await self.client.disconnect()
            except Exception:
                pass
            self.connected = False
            print("✓ Disconnected")

    async def send_command(self, command: str) -> bool:
        """
        Send a command to the Bittle.

        Args:
            command: The command string to send.

        Returns:
            True if sent successfully, False otherwise.
        """
        if not self.connected or not self.client or not self.char:
            print("❌ Not connected to Bittle")
            return False

        try:
            cmd_bytes = command.encode()
            await self.client.write_gatt_char(self.char, cmd_bytes)
            print(f"→ Sent: {command}")
            await asyncio.sleep(self.command_delay)
            return True
        except Exception as e:
            print(f"❌ Failed to send command: {e}")
            self.connected = False
            return False

    def validate_motor_command(self, index: int, angle: int) -> Tuple[bool, str]:
        """Validate motor command parameters."""
        valid_indices = list(MOTOR_INDICES.keys())
        if index not in valid_indices:
            return False, f"Motor index must be one of {valid_indices}, got {index}"
        if angle < -90 or angle > 90:
            return False, f"Angle must be -90 to 90, got {angle}"
        return True, "Valid"

    def validate_skill_command(self, skill: str) -> Tuple[bool, str]:
        """Validate skill command."""
        if skill in SKILLS:
            return True, f"Valid skill: {SKILLS[skill]}"
        if skill.startswith("k") and len(skill) > 1:
            return True, f"Valid custom skill: {skill}"
        return False, f"Unknown skill: {skill}"

    def build_motor_command(self, index: int, angle: int) -> str:
        """Build a motor control command."""
        return f"m{index} {angle}"

    def build_skill_command(self, skill: str) -> str:
        """Build a skill command."""
        if skill in SKILLS:
            return SKILLS[skill]
        if not skill.startswith("k"):
            return f"k{skill}"
        return skill

    async def execute_motor(self, index: int, angle: int) -> bool:
        """Execute motor command with validation."""
        valid, msg = self.validate_motor_command(index, angle)
        if not valid:
            print(f"❌ {msg}")
            return False

        cmd = self.build_motor_command(index, angle)
        return await self.send_command(cmd)

    async def execute_skill(self, skill: str) -> bool:
        """Execute skill command with validation."""
        valid, msg = self.validate_skill_command(skill)
        if not valid:
            print(f"❌ {msg}")
            return False

        cmd = self.build_skill_command(skill)
        return await self.send_command(cmd)


def show_help():
    """Display help information."""
    help_text = """
╔════════════════════════════════════════════════════════════════════╗
║    Petoi Bittle Bluetooth Interactive Controller v1.0              ║
╚════════════════════════════════════════════════════════════════════╝

COMMAND SYNTAX:
  motor <index> <angle>     - Control servo motor
  skill <name>              - Execute a predefined skill
  help                      - Show this help
  motors                    - List all motors
  skills                    - List all skills
  exit/quit                 - Exit program

MOTOR EXAMPLES:
  motor 0 30                - Move neck (head tilt) to 30°
  motor 8 -15               - Move left shoulder to -15°
  motor 12 45               - Move left arm to 45°

SKILL EXAMPLES:
  skill sit                 - Sit down
  skill stand               - Stand up
  skill walk_forward        - Walk forward
  skill trot_left           - Trot left

DIRECT COMMANDS:
  Send raw Petoi commands directly:
  ksit, kwkF, m0 30, c10 5, etc.

TYPE 'help' or 'motors' or 'skills' for more information.
"""
    print(help_text)


def show_motors():
    """Display motor information."""
    print("\n" + "=" * 60)
    print("BITTLE X MOTORS (Servo Indices)")
    print("=" * 60)
    for idx, name in sorted(MOTOR_INDICES.items()):
        print(f"  {idx:2d} - {name:<30} (Range: -90° to +90°)")
    print("=" * 60 + "\n")


def show_skills():
    """Display available skills."""
    print("\n" + "=" * 60)
    print("AVAILABLE SKILLS")
    print("=" * 60)
    for shorthand, command in sorted(SKILLS.items()):
        print(f"  {shorthand:<20} → {command}")
    print("=" * 60 + "\n")


async def interactive_loop(controller: BittleBLEController):
    """Run the interactive command loop."""
    print("\n" + "=" * 60)
    print("✓ Bittle BLE Controller Started")
    print("Type 'help' for commands, 'exit' to quit")
    print("=" * 60 + "\n")

    loop = asyncio.get_event_loop()

    while True:
        try:
            # Use run_in_executor to avoid blocking on input
            user_input = await loop.run_in_executor(None, input, "bittle> ")
            user_input = user_input.strip()

            if not user_input:
                continue

            parts = user_input.split()
            command = parts[0].lower()

            if command == "exit" or command == "quit":
                print("Exiting...")
                break

            elif command == "help":
                show_help()

            elif command == "motors":
                show_motors()

            elif command == "skills":
                show_skills()

            elif command == "motor":
                if len(parts) < 3:
                    print("Usage: motor <index> <angle>")
                    continue
                try:
                    index = int(parts[1])
                    angle = int(parts[2])
                    await controller.execute_motor(index, angle)
                except ValueError:
                    print("Error: index and angle must be integers")

            elif command == "skill":
                if len(parts) < 2:
                    print("Usage: skill <name>")
                    continue
                skill = "_".join(parts[1:]).lower()
                await controller.execute_skill(skill)

            else:
                # Raw Petoi command
                await controller.send_command(user_input)

        except KeyboardInterrupt:
            print("\n\nInterrupted by user")
            break
        except Exception as e:
            print(f"Error: {e}")


async def main():
    """Main entry point."""
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║    Petoi Bittle Bluetooth Interactive Controller v1.0              ║")
    print("╚════════════════════════════════════════════════════════════════════╝\n")

    # Get Bluetooth address from command line or use None for auto-discovery
    address = sys.argv[1] if len(sys.argv) > 1 else None

    # Create controller
    controller = BittleBLEController(address=address)

    # Connect to Bittle
    if not await controller.connect():
        print("\nTroubleshooting:")
        print("  1. Ensure Bittle is powered on")
        print("  2. Pair Bittle via Bluetooth settings")
        print("  3. Install Bleak: pip install bleak")
        print("  4. Or specify address: python petoi_bittle_controller.py <address>")
        sys.exit(1)

    try:
        await interactive_loop(controller)
    finally:
        await controller.disconnect()
        print("Program terminated.")


if __name__ == "__main__":
    asyncio.run(main())
