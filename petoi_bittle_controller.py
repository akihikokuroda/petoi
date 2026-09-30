#!/usr/bin/env python3
"""
Interactive Petoi Bittle Controller with Bluetooth LE (BLE)
Connects to the Bittle robot via Bluetooth Low Energy and sends commands.
Reference: https://docs.petoi.com/apis/serial-protocol
Based on: https://github.com/akihikokuroda/petoi/blob/main/bluetooth_testSkills.py
"""

import asyncio
import sys
import re
from typing import Optional, Tuple, Dict, Any
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

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
    READ = "R"


@dataclass
class LightSensorReading:
    """Light sensor data (e.g., TCS34725 or similar)."""
    timestamp: datetime = field(default_factory=lambda: datetime.now())
    lux: Optional[float] = None
    red: Optional[int] = None
    green: Optional[int] = None
    blue: Optional[int] = None
    color_temperature: Optional[float] = None
    brightness: Optional[int] = None
    raw_value: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "lux": self.lux,
            "red": self.red,
            "green": self.green,
            "blue": self.blue,
            "color_temperature": self.color_temperature,
            "brightness": self.brightness,
            "raw_value": self.raw_value,
        }


@dataclass
class DistanceSensorReading:
    """IR distance sensor (double infrared reflection) data.

    value is the raw analog reading of the sensor pin. On the Petoi IR distance
    module the raw ADC reading correlates with distance (a closer object gives a
    different reading). The docs don't publish a fixed unit, so it is kept raw.
    """
    timestamp: datetime = field(default_factory=lambda: datetime.now())
    value: Optional[int] = None
    raw_value: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
            "raw_value": self.raw_value,
        }


@dataclass
class TouchSensorReading:
    """Touch sensor (double touch) data.

    value is the digital level of the touch pin: 0 = no touch, 1 = touched
    (the pad outputs a high level whether touched lightly or pressed hard).
    """
    timestamp: datetime = field(default_factory=lambda: datetime.now())
    value: Optional[int] = None
    raw_value: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
            "raw_value": self.raw_value,
        }


@dataclass
class BackTouchSensorReading:
    """Back touch sensor data (single multiplexed analog sensor, 4 pads).

    The four pads (Front Left, Front Right, Center, Back) share one analog
    channel (pin 38). The raw value is an ADC count; dividing it by 600
    selects the band and maps to a pad:

        value            -> touch_id -> location
        0                -> 1        -> Front Left
        600..1199        -> 3        -> Center
        1200..1799       -> 4        -> Back
        1800..2399       -> 2        -> Front Right
        2400 or higher   -> 0        -> No touch
        (0 < value < 600) is flagged as a possible bad connection.

    touch_id uses the reference convention:
        0 = No touch, 1 = Front Left, 2 = Front Right, 3 = Center, 4 = Back.
    """
    timestamp: datetime = field(default_factory=lambda: datetime.now())
    value: Optional[int] = None        # raw analog (ADC) value read from pin 38
    raw_value: Optional[str] = None    # raw serial response string
    touch_id: int = 0                  # 0=none,1=FL,2=FR,3=Center,4=Back
    location: str = "No touch"         # decoded human-readable pad name
    ok: bool = True                    # False if the value looks like a wiring error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
            "raw_value": self.raw_value,
            "touch_id": self.touch_id,
            "location": self.location,
            "ok": self.ok,
        }


@dataclass
class IMUSensorReading:
    """IMU sensor data (accelerometer and gyroscope)."""
    timestamp: datetime = field(default_factory=lambda: datetime.now())
    accel_x: Optional[float] = None
    accel_y: Optional[float] = None
    accel_z: Optional[float] = None
    gyro_x: Optional[float] = None
    gyro_y: Optional[float] = None
    gyro_z: Optional[float] = None
    raw_value: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "accel_x": self.accel_x,
            "accel_y": self.accel_y,
            "accel_z": self.accel_z,
            "gyro_x": self.gyro_x,
            "gyro_y": self.gyro_y,
            "gyro_z": self.gyro_z,
            "raw_value": self.raw_value,
        }


@dataclass
class GestureSensorReading:
    """Gesture sensor data.

    value: -1 No gesture detected; 0 Up; 1 Down; 2 Left; 3 Right.
    """
    timestamp: datetime = field(default_factory=lambda: datetime.now())
    value: Optional[int] = None
    gesture: Optional[str] = None
    raw_value: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
            "gesture": self.gesture,
            "raw_value": self.raw_value,
        }


# Gesture value mapping (same as readGestureVal in PetoiRobot/robot.py)
GESTURE_VALUE_NAMES = {
    -1: "no gesture",
    0: "up",
    1: "down",
    2: "left",
    3: "right",
}

# Index of the Gesture flag in the module-status list (moduleList in
# src/OpenCat.h: Grove_Serial, Voice, Double_Touch, Double_Light,
# Double_IR_Distance, PIR, BackTouch, Ultrasonic, Gesture, Camera, Quick_Demo)
# NOTE: that list is printed with Serial.print (USB only) and is NOT
# received over BLE — see activate_gesture_mode().
GESTURE_MODE_FLAG_INDEX = 8


# Common skills for Bittle
SKILLS = {
    # Basic postures
    "sit": "ksit",
    "stand": "kstand",
    "rest": "krest",
    "sleep": "ksleep",
    "idle": "kidle",
    "zero": "kzero",

    # Walking gaits
    "walk_forward": "kwkF",
    "walk_backward": "kwkB",
    "walk_left": "kwkL",
    "walk_right": "kwkR",

    # Trotting gaits
    "trot_forward": "ktrF",
    "trot_backward": "ktrB",
    "trot_left": "ktrL",
    "trot_right": "ktrR",

    # Crawling gaits
    "crawl_forward": "kcrF",
    "crawl_left": "kcrL",

    # Balance and movement
    "balance": "kbalance",

    # Stretching and postures
    "stretch": "kstr",
    "high": "khi",

    # Climbing
    "climb_ceiling": "kclimbCeil",

    # Falling and recovery
    "dropped": "kdropped",
    "lifted": "klifted",

    # Behavioral skills
    "pee": "kpee",
    "pick_up_left": "kpu1",  # pu1 = pick up left
    "pick_up_right": "kpu",   # pu = pick up (right)
    "purr": "kpurr",
    "check": "kck",
    "bark_forward": "kbf",
    "bark": "kbk",

    # Movement skills
    "step": "kstep",
    "tilt_forward": "ktf",
    "tilt": "ktilt",
    "roll_left": "krlL",
    "roll": "krl",
    "right_turn": "krt",
    "calibrate": "kcalib",

    # Extended movement (Mecha)
    "mech_forward": "kmhF",
    "mech_left": "kmhL",

    # Hopping skills
    "hop_left_forward": "khlwF",
    "hop_left_left": "khlwL",

    # Pedaling/Cycling
    "pedal_forward": "kpdF",
    "pedal_left": "kpdL",

    # Flip and tricks
    "flip": "kff",
    "flip_down": "kfd",

    # Joy and excitement
    "joy": "kjy",

    # Phase shifts (body parts specific)
    "phase_forward": "kphF",
    "phase_left": "kphL",

    # Roll and composite movements
    "roll_forward": "krF",
    "roll_left": "krL",
    "roll_right": "krR",
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

# Light sensor pin mapping.
# The Bittle's two light sensors are wired to GPIO 34 (left) and GPIO 35 (right).
# The 'light' command exposes them as 'L' and 'R'. Swap the two values here if
# your physical wiring is reversed.
LIGHT_PINS = {
    "L": 34,  # left light sensor  -> GPIO 34
    "R": 35,  # right light sensor -> GPIO 35
}

# IR distance sensor (double infrared reflection) pin mapping.
# This module has two analog sensors: left on GPIO 34 and right on GPIO 35
# (BiBoard; A2/A3 on NyBoard). It is read as a plain analog value (Ra + pin),
# just like the light sensor. The module mode is toggled with 'XD' / 'Xd'.
DISTANCE_PINS = {
    "L": 34,  # left  IR distance sensor -> GPIO 34
    "R": 35,  # right IR distance sensor -> GPIO 35
}

# Touch sensor (double touch) pin mapping.
# Two digital pads: left on GPIO 34 and right on GPIO 35. Read as a digital
# value (Rd + pin) -> 0 (no touch) or 1 (touched). Mode toggled with 'XT' / 'Xt'.
TOUCH_PINS = {
    "L": 34,  # left  touch pad -> GPIO 34
    "R": 35,  # right touch pad -> GPIO 35
}

# Back touch sensor (4 pads: Front Left, Front Right, Center, Back).
# Unlike the double-touch module, all four pads are multiplexed onto a SINGLE
# analog channel (GPIO 38). Reading the raw value and dividing by 600 selects
# the band that maps to a pad. Mode is toggled with 'XB' (on) / 'Xb' (off).
BACK_TOUCH_PIN = 38
# index (raw_value // 600) -> touch_id, matching the reference robot.py mapping.
BACK_TOUCH_PAD_MAP = [1, 3, 4, 2]
# touch_id -> human-readable location name (index = touch_id - 1).
BACK_TOUCH_LOCATIONS = ["Front Left", "Front Right", "Center", "Back"]


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
        self.last_light_reading: Optional[LightSensorReading] = None
        self.last_distance_reading: Optional[DistanceSensorReading] = None
        self.last_touch_reading: Optional[TouchSensorReading] = None
        self.last_back_touch_reading: Optional[BackTouchSensorReading] = None
        self.last_imu_reading: Optional[IMUSensorReading] = None
        self.last_gesture_reading: Optional[GestureSensorReading] = None
        self.gesture_mode_active: bool = False
        self.sensor_response_queue: asyncio.Queue = asyncio.Queue()
        self.imu_response_queue: asyncio.Queue = asyncio.Queue(maxsize=10)
        self.notify_char = None

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

    async def find_notify_characteristic(self):
        """
        Scan GATT services to find a notify characteristic for responses.

        Returns:
            Characteristic object or None.
        """
        try:
            for service in self.client.services:
                for char in service.characteristics:
                    if "notify" in char.properties or "read" in char.properties:
                        print(f"Found readable characteristic: {char.uuid}")
                        return char
            return None
        except Exception as e:
            print(f"❌ Failed to find notify characteristic: {e}")
            return None

    def _notification_handler(self, sender, data):
        """Handle incoming BLE notifications."""
        try:
            response = data.decode("utf-8").strip()
            if not response:
                return

            # Ignore handshake/info messages and echo replies
            # ('X'/'G' are command-completion echoes; gesture values are digits)
            if response in ("Petoi Bittle", "Bittle55_SSP", "p", "k", "R", "X", "G"):
                return

            # Check if this is IMU data
            if response.startswith("ICM:"):
                print(f"← Received IMU: {response}")
                asyncio.create_task(self.imu_response_queue.put(response))
            else:
                print(f"← Received: {repr(response)}")
                asyncio.create_task(self.sensor_response_queue.put(response))
        except Exception as e:
            print(f"Error decoding notification: {e}")

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

            # Find notify characteristic for responses
            self.notify_char = await self.find_notify_characteristic()
            if self.notify_char and "notify" in self.notify_char.properties:
                await self.client.start_notify(self.notify_char, self._notification_handler)
                print(f"Notification handler enabled")

            await asyncio.sleep(0.5)
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False

    async def disconnect(self):
        """Disconnect from the Bittle."""
        if self.client:
            try:
                if self.notify_char:
                    await self.client.stop_notify(self.notify_char)
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

    async def activate_light_mode(self) -> bool:
        """Activate light sensor mode on Bittle XL."""
        print("Activating light mode...")
        return await self.send_command("XL")

    async def deactivate_light_mode(self) -> bool:
        """Deactivate light sensor mode on Bittle XL."""
        print("Deactivating light mode...")
        return await self.send_command("Xl")

    async def activate_distance_mode(self) -> bool:
        """Activate the IR distance sensor mode (XD)."""
        print("Activating IR distance mode...")
        return await self.send_command("XD")

    async def deactivate_distance_mode(self) -> bool:
        """Deactivate the IR distance sensor mode (Xd)."""
        print("Deactivating IR distance mode...")
        return await self.send_command("Xd")

    async def activate_touch_mode(self) -> bool:
        """Activate the touch sensor mode (XT)."""
        print("Activating touch mode...")
        return await self.send_command("XT")

    async def deactivate_touch_mode(self) -> bool:
        """Deactivate the touch sensor mode (Xt)."""
        print("Deactivating touch mode...")
        return await self.send_command("Xt")

    async def activate_back_touch_mode(self) -> bool:
        """Activate the back touch sensor mode (XB)."""
        print("Activating back touch mode...")
        return await self.send_command("XB")

    async def deactivate_back_touch_mode(self) -> bool:
        """Deactivate the back touch sensor mode (Xb)."""
        print("Deactivating back touch mode...")
        return await self.send_command("Xb")

    def resolve_light_command(self, cmd: str) -> str:
        """Resolve a light argument to the raw Bittle command to send.

        Accepts:
          - 'L' or 'R' (case-insensitive): the left / right light sensor
            (see LIGHT_PINS -> GPIO 34 / 35).
          - A pin number, e.g. '34' or '35'.
          - A raw command already starting with 'Ra': passed through unchanged.

        The Bittle firmware reads the GPIO whose number equals the ASCII code
        of the single character after 'Ra', so we emit Ra<chr(pin)>:
        pin 34 -> Ra"   pin 35 -> Ra#
        """
        if cmd.startswith("Ra"):
            return cmd

        key = cmd.upper()
        if key in LIGHT_PINS:
            return f"Ra{chr(LIGHT_PINS[key])}"

        if cmd.isdigit():
            return f"Ra{chr(int(cmd))}"

        return cmd

    async def read_light_sensor(self, command: str = 'Ra"', timeout: float = 2.0) -> Optional[LightSensorReading]:
        """
        Read a single light sensor from the Bittle (default: left, GPIO 34).
        Sends command and waits for response (format: varies by command).

        Args:
            command: Raw command to send (default: left sensor, 'Ra"')
            timeout: Response timeout in seconds (default: 2.0)
        """
        if not self.connected or not self.client or not self.char:
            print("❌ Not connected to Bittle")
            return None

        try:
            print(f"Reading light sensor with command: '{command}'")
            await self.send_command(command)

            # Add small delay to let fragments accumulate
            await asyncio.sleep(0.3)

            # Drain queue to get all accumulated responses
            responses = []
            while not self.sensor_response_queue.empty():
                try:
                    response = self.sensor_response_queue.get_nowait()
                    responses.append(response)
                except asyncio.QueueEmpty:
                    break

            if responses:
                # Join without spaces to preserve format like "=0"
                combined = "".join(responses)
                print(f"Raw responses: {responses}")
                print(f"Combined: {repr(combined)}")
                return await self.parse_light_sensor_response(combined)
            else:
                print(f"⚠ No response received for command '{command}'")
                return None
        except Exception as e:
            print(f"❌ Failed to read light sensor: {e}")
            return None

    async def read_light_sensors(self, timeout: float = 2.0):
        """Read both light sensors (left = GPIO 34, right = GPIO 35).

        Reads them one after the other and prints both side by side.

        Returns:
            Dict {'L': LightSensorReading | None, 'R': LightSensorReading | None}
        """
        readings: Dict[str, Optional[LightSensorReading]] = {}
        for side in ("L", "R"):
            cmd = self.resolve_light_command(side)
            readings[side] = await self.read_light_sensor(command=cmd, timeout=timeout)
            # Small gap so the next command/response pair doesn't bleed into the queue.
            await asyncio.sleep(0.3)
        self.print_light_readings(readings)
        return readings

    def resolve_distance_command(self, side: str) -> str:
        """Resolve a distance side ('L'/'R') to the raw Bittle analog read command.

        The IR distance sensors are read as analog values (Ra + pin), where the
        pin is sent as the byte whose value equals the pin number (chr(pin)):
        pin 34 -> Ra"   pin 35 -> Ra#
        """
        side = side.upper()
        if side not in DISTANCE_PINS:
            return ""
        return f"Ra{chr(DISTANCE_PINS[side])}"

    async def read_distance_sensor(self, side: str = "L", timeout: float = 2.0) -> Optional[DistanceSensorReading]:
        """
        Read one IR distance sensor (left or right).

        Args:
            side: 'L' or 'R' (see DISTANCE_PINS for the pin).
            timeout: Response timeout in seconds (default: 2.0).
        """
        command = self.resolve_distance_command(side)
        if not command:
            print(f"❌ Unknown distance side: '{side}' (expected 'L' or 'R')")
            return None
        if not self.connected or not self.client or not self.char:
            print("❌ Not connected to Bittle")
            return None

        try:
            print(f"Reading distance ({side}) with command: '{command}'")
            await self.send_command(command)

            # Add small delay to let fragments accumulate
            await asyncio.sleep(0.3)

            # Drain queue to get all accumulated responses
            responses = []
            while not self.sensor_response_queue.empty():
                try:
                    response = self.sensor_response_queue.get_nowait()
                    responses.append(response)
                except asyncio.QueueEmpty:
                    break

            if responses:
                combined = "".join(responses)
                print(f"Raw responses: {responses}")
                print(f"Combined: {repr(combined)}")
                return await self.parse_distance_response(combined)
            else:
                print(f"⚠ No response received for command '{command}'")
                return None
        except Exception as e:
            print(f"❌ Failed to read distance: {e}")
            return None

    async def read_distance_sensors(self, timeout: float = 2.0):
        """Read both distance sensors (left + right) and print them side by side.

        Returns:
            Dict {'L': DistanceSensorReading | None, 'R': DistanceSensorReading | None}
        """
        readings: Dict[str, Optional[DistanceSensorReading]] = {}
        for side in ("L", "R"):
            readings[side] = await self.read_distance_sensor(side=side, timeout=timeout)
            # Small gap so the next command/response pair doesn't bleed into the queue.
            await asyncio.sleep(0.3)
        self.print_distance_readings(readings)
        return readings

    async def parse_distance_response(self, response: str) -> Optional[DistanceSensorReading]:
        """Parse an IR distance (analog) response.

        Format: '=<value>' where value is the raw analog reading of the sensor
        pin (e.g. '=512'), the same shape as the light/analog read.
        """
        try:
            response = response.strip()
            if "=" in response:
                value_str = response.split("=", 1)[1]
                value_str = value_str.rstrip("=, \t\r\n").strip()
                if re.fullmatch(r"\d+", value_str):
                    reading = DistanceSensorReading(
                        value=int(value_str),
                        raw_value=response,
                    )
                    self.last_distance_reading = reading
                    print(f"✓ Parsed distance value: {reading.value}")
                    return reading
                print(f"❌ Invalid distance value: {response}")
                return None
            print(f"❌ Unrecognized distance response: {response}")
            return None
        except Exception as e:
            print(f"❌ Failed to parse distance response: {e}")
            return None

    def resolve_touch_command(self, side: str) -> str:
        """Resolve a touch side ('L'/'R') to the raw Bittle digital read command.

        The touch pads are read as digital values (Rd + pin), where the pin is
        sent as the byte whose value equals the pin number (chr(pin)):
        pin 34 -> Rd"   pin 35 -> Rd#
        """
        side = side.upper()
        if side not in TOUCH_PINS:
            return ""
        return f"Rd{chr(TOUCH_PINS[side])}"

    async def read_touch_sensor(self, side: str = "L", timeout: float = 2.0) -> Optional[TouchSensorReading]:
        """
        Read one touch pad (left or right).

        Args:
            side: 'L' or 'R' (see TOUCH_PINS for the pin).
            timeout: Response timeout in seconds (default: 2.0).
        """
        command = self.resolve_touch_command(side)
        if not command:
            print(f"❌ Unknown touch side: '{side}' (expected 'L' or 'R')")
            return None
        if not self.connected or not self.client or not self.char:
            print("❌ Not connected to Bittle")
            return None

        try:
            print(f"Reading touch ({side}) with command: '{command}'")
            await self.send_command(command)

            # Add small delay to let fragments accumulate
            await asyncio.sleep(0.3)

            # Drain queue to get all accumulated responses
            responses = []
            while not self.sensor_response_queue.empty():
                try:
                    response = self.sensor_response_queue.get_nowait()
                    responses.append(response)
                except asyncio.QueueEmpty:
                    break

            if responses:
                combined = "".join(responses)
                print(f"Raw responses: {responses}")
                print(f"Combined: {repr(combined)}")
                return await self.parse_touch_response(combined)
            else:
                print(f"⚠ No response received for command '{command}'")
                return None
        except Exception as e:
            print(f"❌ Failed to read touch: {e}")
            return None

    async def read_touch_sensors(self, timeout: float = 2.0):
        """Read both touch pads (left + right) and print them side by side.

        Returns:
            Dict {'L': TouchSensorReading | None, 'R': TouchSensorReading | None}
        """
        readings: Dict[str, Optional[TouchSensorReading]] = {}
        for side in ("L", "R"):
            readings[side] = await self.read_touch_sensor(side=side, timeout=timeout)
            # Small gap so the next command/response pair doesn't bleed into the queue.
            await asyncio.sleep(0.3)
        self.print_touch_readings(readings)
        return readings

    async def parse_touch_response(self, response: str) -> Optional[TouchSensorReading]:
        """Parse a touch (digital) response.

        Format: '=<value>' where value is 0 (no touch) or 1 (touched).
        """
        try:
            response = response.strip()
            if "=" in response:
                value_str = response.split("=", 1)[1]
                value_str = value_str.rstrip("=, \t\r\n").strip()
                if re.fullmatch(r"\d+", value_str):
                    reading = TouchSensorReading(
                        value=int(value_str),
                        raw_value=response,
                    )
                    self.last_touch_reading = reading
                    state = "touched" if reading.value == 1 else "no touch"
                    print(f"✓ Parsed touch: {state} (value={reading.value})")
                    return reading
                print(f"❌ Invalid touch value: {response}")
                return None
            print(f"❌ Unrecognized touch response: {response}")
            return None
        except Exception as e:
            print(f"❌ Failed to parse touch response: {e}")
            return None

    def resolve_back_touch_command(self) -> str:
        """Return the raw Bittle command to read the back touch sensor.

        The back touch module is a single analog sensor on pin 38, so this is
        just an analog read: 'Ra' + chr(38) -> 'Ra&'.
        """
        return f"Ra{chr(BACK_TOUCH_PIN)}"

    async def read_back_touch_sensor(self, timeout: float = 2.0) -> Optional[BackTouchSensorReading]:
        """
        Read the back touch sensor (Front Left / Front Right / Center / Back).

        Reads one analog value from pin 38 and decodes it into a touch
        location. Returns a BackTouchSensorReading, or None if no response.
        """
        command = self.resolve_back_touch_command()
        if not self.connected or not self.client or not self.char:
            print("❌ Not connected to Bittle")
            return None

        try:
            print(f"Reading back touch with command: '{command}'")
            await self.send_command(command)

            # Add small delay to let fragments accumulate
            await asyncio.sleep(0.3)

            # Drain queue to get all accumulated responses
            responses = []
            while not self.sensor_response_queue.empty():
                try:
                    response = self.sensor_response_queue.get_nowait()
                    responses.append(response)
                except asyncio.QueueEmpty:
                    break

            if responses:
                combined = "".join(responses)
                print(f"Raw responses: {responses}")
                print(f"Combined: {repr(combined)}")
                return await self.parse_back_touch_response(combined)
            else:
                print(f"⚠ No response received for command '{command}'")
                return None
        except Exception as e:
            print(f"❌ Failed to read back touch: {e}")
            return None

    async def parse_back_touch_response(self, response: str) -> Optional[BackTouchSensorReading]:
        """Parse a back touch response and decode the touched location.

        Format: '=<value>' where value is the raw analog (ADC) reading.
        The raw value is divided by 600 to pick a band, which maps to one of
        the four pads via BACK_TOUCH_PAD_MAP (see BackTouchSensorReading).
        """
        try:
            response = response.strip()
            if "=" in response:
                value_str = response.split("=", 1)[1]
                value_str = value_str.rstrip("=, \t\r\n").strip()
                if not re.fullmatch(r"\d+", value_str):
                    print(f"❌ Invalid back touch value: {response}")
                    return None

                raw = int(value_str)
                reading = BackTouchSensorReading(value=raw, raw_value=response)

                # Decode the raw analog value into a touch location, matching
                # the reference robot.py readBackTouchSensorVal() logic.
                if raw > 0 and raw < 600:
                    reading.ok = False
                    reading.touch_id = -1
                    reading.location = "No touch (check sensor connection)"
                elif raw < 2400:
                    index = min(int(raw // 600), len(BACK_TOUCH_PAD_MAP) - 1)
                    reading.touch_id = BACK_TOUCH_PAD_MAP[index]
                    reading.location = BACK_TOUCH_LOCATIONS[reading.touch_id - 1]
                else:
                    reading.touch_id = 0
                    reading.location = "No touch"

                self.last_back_touch_reading = reading
                print(f"✓ Parsed back touch: {reading.location} "
                      f"(value={reading.value}, id={reading.touch_id})")
                return reading

            print(f"❌ Unrecognized back touch response: {response}")
            return None
        except Exception as e:
            print(f"❌ Failed to parse back touch response: {e}")
            return None

    async def parse_light_sensor_response(self, response: str) -> Optional[LightSensorReading]:
        """
        Parse light sensor response from Bittle.
        Formats:
        - Analog read: "=<value>" (e.g., "=512")
        - CSV format: "lux,red,green,blue,cct,brightness"
        """
        try:
            response = response.strip()

            # Handle analog read format: =value or =value=
            if response.startswith("="):
                try:
                    # Remove leading and trailing '='
                    value_str = response[1:].rstrip("=")
                    value = int(value_str)
                    reading = LightSensorReading(
                        brightness=value,
                        raw_value=response,
                    )
                    self.last_light_reading = reading
                    print(f"✓ Parsed analog value: {value}")
                    return reading
                except ValueError:
                    print(f"❌ Invalid analog value: {response}")
                    return None

            # Handle CSV format: lux,red,green,blue,cct,brightness
            parts = response.split(",")
            if len(parts) >= 6:
                reading = LightSensorReading(
                    lux=float(parts[0]),
                    red=int(parts[1]),
                    green=int(parts[2]),
                    blue=int(parts[3]),
                    color_temperature=float(parts[4]),
                    brightness=int(parts[5]),
                    raw_value=response,
                )
                self.last_light_reading = reading
                return reading

            print(f"❌ Unrecognized sensor response format: {response}")
            return None
        except (ValueError, IndexError) as e:
            print(f"❌ Failed to parse sensor response: {e}")
            return None

    def get_last_light_reading(self) -> Optional[LightSensorReading]:
        """Get the last recorded light sensor reading."""
        return self.last_light_reading

    async def read_imu_sensor(self, timeout: float = 2.0) -> Optional[IMUSensorReading]:
        """
        Read IMU data from Bittle (broadcasts automatically).
        Waits for the next available IMU reading.

        Args:
            timeout: Wait timeout in seconds (default: 2.0)
        """
        if not self.connected:
            print("❌ Not connected to Bittle")
            return None

        try:
            # Wait for IMU data with timeout
            response = await asyncio.wait_for(
                self.imu_response_queue.get(),
                timeout=timeout
            )
            return await self.parse_imu_response(response)
        except asyncio.TimeoutError:
            print(f"⚠ No IMU data received (waited {timeout}s)")
            print("  Bittle broadcasts IMU data continuously")
            print("  Current issue: No IMU data in buffer")
            return None
        except Exception as e:
            print(f"❌ Failed to read IMU: {e}")
            return None

    async def parse_imu_response(self, response: str) -> Optional[IMUSensorReading]:
        """
        Parse IMU response from Bittle.
        Expected format: "ICM:  accel_x  accel_y  accel_z gyro_x  gyro_y  gyro_z"
        Example: "ICM:  -7.5  -2.9 100.0 -141.2   -4.2   -1.8"
        """
        try:
            if not response.startswith("ICM:"):
                return None

            parts = response.replace("ICM:", "").split()
            parts = [p for p in parts if p]

            if len(parts) < 6:
                return None

            reading = IMUSensorReading(
                accel_x=float(parts[0]),
                accel_y=float(parts[1]),
                accel_z=float(parts[2]),
                gyro_x=float(parts[3]),
                gyro_y=float(parts[4]),
                gyro_z=float(parts[5]),
                raw_value=response,
            )
            self.last_imu_reading = reading
            return reading
        except Exception as e:
            print(f"❌ Failed to parse IMU: {response[:50]} - Error: {e}")
            return None

    def get_last_imu_reading(self) -> Optional[IMUSensorReading]:
        """Get the last recorded IMU reading."""
        return self.last_imu_reading

    async def activate_gesture_mode(self, reactions: bool = False) -> bool:
        """Enable the gesture module and start the continuous value stream.

        Firmware behavior (src/moduleManager.h, src/reaction.h):
          - "X" + uppercase letter enables that module (and disables the
            other non-protected modules).
          - option "P" -> continuous print: every detected gesture value is
            pushed to the client (0=up 1=down 2=left 3=right).
          - option "r" -> turn the automatic reactions (sit/scratch/head
            turn) OFF; "R" -> leave them ON.

        So "XGPr" (default) = module on + value stream + robot stays still,
        which is what you want for reading. "XGPR" = same but the dog
        reacts to each gesture (sit/scratch/head turn) as well.

        Note: the module status list the robot prints on activation
        (showModuleStatus) goes to the USB serial port only, so it never
        arrives over BLE — a successful write is our confirmation here.
        """
        if not self.connected or not self.client or not self.char:
            print("❌ Not connected to Bittle")
            return False

        cmd = "XGPR" if reactions else "XGPr"
        note = "reactions ON (dog will sit/scratch/turn head)" if reactions \
            else "reactions OFF (dog stays still)"
        print(f"Activating gesture mode ({cmd}) — continuous value stream, {note}")
        if not await self.send_command(cmd):
            return False

        self.gesture_mode_active = True
        print("✓ Gesture mode active — wave your hand in front of the sensor")
        return True

    async def deactivate_gesture_mode(self) -> bool:
        """Disable the gesture module (Xg) and stop the value stream."""
        if not self.connected or not self.client or not self.char:
            print("❌ Not connected to Bittle")
            return False

        print("Deactivating gesture mode (Xg)...")
        if not await self.send_command("Xg"):
            return False

        self.gesture_mode_active = False
        print("✓ Gesture mode deactivated")
        return True

    def _gesture_flag_active(self, response: str) -> bool:
        """Check the Gesture flag (index 8) in a module-status list response.

        Only useful over USB serial — the list is not sent over BLE.
        """
        pattern = re.compile(r'^(?=.*[01])(?=.*,).+$', flags=re.MULTILINE)
        for line in pattern.findall(response):
            line = line.replace('\t', '').replace('\r', '').replace('\n', '').strip()
            try:
                flags = [int(x) for x in line.split(',')[:-1]]
            except ValueError:
                continue
            if len(flags) > GESTURE_MODE_FLAG_INDEX and flags[GESTURE_MODE_FLAG_INDEX] == 1:
                return True
        return False

    def _is_gesture_value(self, message: str) -> bool:
        """True if this BLE message is a pushed gesture value (-1..3)."""
        if not re.fullmatch(r"-?\d+", message):
            return False
        return int(message) in GESTURE_VALUE_NAMES

    async def read_gesture_sensor(self, timeout: float = 10.0) -> Optional[GestureSensorReading]:
        """
        Read one gesture value from the Bittle.

        Value meaning: -1 No gesture; 0 Up; 1 Down; 2 Left; 3 Right.

        While the gesture module runs in continuous print mode (XGP), the
        firmware pushes every detected value to the client, so this method
        enables the stream if needed, then waits up to `timeout` seconds
        for a pushed value, skipping unrelated traffic on the BLE channel.
        (A one-shot "XGp" read is unreliable: once the module is enabled
        the robot's main loop consumes detected gestures every iteration,
        so XGp almost always returns -1.)

        Wave your hand in front of the sensor while it is waiting.

        Args:
            timeout: How long to wait for a gesture, in seconds
        """
        if not self.connected or not self.client or not self.char:
            print("❌ Not connected to Bittle")
            return None

        if not self.gesture_mode_active:
            if not await self.activate_gesture_mode():
                return None

        # Drop stale messages left over from earlier commands
        while not self.sensor_response_queue.empty():
            try:
                self.sensor_response_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        loop = asyncio.get_event_loop()
        deadline = loop.time() + timeout
        print(f"Waiting for a gesture — wave your hand now... ({timeout:.0f}s)")
        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                print("⚠ No gesture detected in time")
                print("  Keep your hand within ~20cm of the sensor and move it clearly")
                return None
            try:
                message = await asyncio.wait_for(
                    self.sensor_response_queue.get(), timeout=remaining
                )
            except asyncio.TimeoutError:
                print("⚠ No gesture detected in time")
                return None
            if self._is_gesture_value(message):
                return self.parse_gesture_response(message)
            # anything else (reaction echoes, status text, ...) is ignored

    def parse_gesture_response(self, response: str) -> Optional[GestureSensorReading]:
        """Parse a gesture value from the Bittle.

        Accepts the streamed bare value ("1") as well as the one-shot
        "=<value>" reply ("=1"). Values: -1 none, 0 up, 1 down, 2 left,
        3 right.
        """
        try:
            match = re.search(r"=\s*(-?\d+)|^(-?\d+)$", response.strip())
            if not match:
                print(f"❌ No gesture value in response: {response!r}")
                return None
            value = int(match.group(1) or match.group(2))
            if value not in GESTURE_VALUE_NAMES:
                print(f"❌ Gesture value out of range (-1..3): {value}")
                return None
            gesture = GESTURE_VALUE_NAMES[value]
            reading = GestureSensorReading(value=value, gesture=gesture, raw_value=response)
            self.last_gesture_reading = reading
            print(f"✓ Gesture: {gesture} (value={value})")
            return reading
        except (ValueError, re.error) as e:
            print(f"❌ Failed to parse gesture response: {e}")
            return None

    def get_last_gesture_reading(self) -> Optional[GestureSensorReading]:
        """Get the last recorded gesture sensor reading."""
        return self.last_gesture_reading

    def print_light_reading(self, reading: Optional[LightSensorReading] = None):
        """Pretty print light sensor reading."""
        if reading is None:
            reading = self.last_light_reading
        if reading is None:
            print("❌ No light sensor reading available")
            return

        print("\n" + "=" * 60)
        print("LIGHT SENSOR READING")
        print("=" * 60)
        print(f"  Timestamp:        {reading.timestamp.isoformat()}")
        print(f"  Illuminance (Lux):{reading.lux if reading.lux is not None else 'N/A':>35}")
        print(f"  Brightness:       {reading.brightness if reading.brightness is not None else 'N/A':>35}")
        print(f"  Color Temp (K):   {reading.color_temperature if reading.color_temperature is not None else 'N/A':>35}")
        print(f"  Red:              {reading.red if reading.red is not None else 'N/A':>35}")
        print(f"  Green:            {reading.green if reading.green is not None else 'N/A':>35}")
        print(f"  Blue:             {reading.blue if reading.blue is not None else 'N/A':>35}")
        if reading.raw_value:
            print(f"  Raw Response:     {reading.raw_value}")
        print("=" * 60 + "\n")

    def print_light_readings(self, readings: Dict[str, Optional[LightSensorReading]]):
        """Pretty print both light sensor readings (left + right) side by side."""
        print("\n" + "=" * 60)
        print("LIGHT SENSOR READINGS")
        print("=" * 60)
        for side, name in (("L", "Left "), ("R", "Right")):
            pin = LIGHT_PINS[side]
            reading = readings.get(side)
            if reading is None:
                print(f"  {name} (pin {pin}):  no response")
            else:
                value = reading.brightness if reading.brightness is not None else "N/A"
                print(f"  {name} (pin {pin}):  {value}")
                if reading.raw_value:
                    print(f"      raw: {reading.raw_value}")
        print("=" * 60 + "\n")

    def print_distance_reading(self, reading: Optional[DistanceSensorReading] = None):
        """Pretty print one distance sensor reading."""
        if reading is None:
            reading = self.last_distance_reading
        if reading is None:
            print("❌ No distance sensor reading available")
            return

        print("\n" + "=" * 60)
        print("DISTANCE SENSOR READING")
        print("=" * 60)
        print(f"  Timestamp:          {reading.timestamp.isoformat()}")
        print(f"  Value (analog):     {reading.value if reading.value is not None else 'N/A':>35}")
        if reading.raw_value:
            print(f"  Raw Response:       {reading.raw_value}")
        print("=" * 60 + "\n")

    def print_distance_readings(self, readings: Dict[str, Optional[DistanceSensorReading]]):
        """Pretty print both distance sensor readings (left + right) side by side."""
        print("\n" + "=" * 60)
        print("DISTANCE SENSOR READINGS")
        print("=" * 60)
        for side, name in (("L", "Left "), ("R", "Right")):
            pin = DISTANCE_PINS[side]
            reading = readings.get(side)
            if reading is None:
                print(f"  {name} (pin {pin}):  no response")
            else:
                value = reading.value if reading.value is not None else "N/A"
                print(f"  {name} (pin {pin}):  {value}")
                if reading.raw_value:
                    print(f"      raw: {reading.raw_value}")
        print("=" * 60 + "\n")

    def print_touch_reading(self, reading: Optional[TouchSensorReading] = None):
        """Pretty print a single touch sensor reading."""
        if reading is None:
            reading = self.last_touch_reading
        if reading is None:
            print("❌ No touch sensor reading available")
            return

        print("\n" + "=" * 60)
        print("TOUCH SENSOR READING")
        print("=" * 60)
        print(f"  Timestamp:          {reading.timestamp.isoformat()}")
        state = "touched" if reading.value == 1 else ("no touch" if reading.value == 0 else "N/A")
        print(f"  State:              {state:>35}")
        print(f"  Value (digital):    {reading.value if reading.value is not None else 'N/A':>35}")
        if reading.raw_value:
            print(f"  Raw Response:       {reading.raw_value}")
        print("=" * 60 + "\n")

    def print_touch_readings(self, readings: Dict[str, Optional[TouchSensorReading]]):
        """Pretty print both touch sensor readings (left + right) side by side."""
        print("\n" + "=" * 60)
        print("TOUCH SENSOR READINGS")
        print("=" * 60)
        for side, name in (("L", "Left "), ("R", "Right")):
            pin = TOUCH_PINS[side]
            reading = readings.get(side)
            if reading is None:
                print(f"  {name} (pin {pin}):  no response")
            else:
                if reading.value == 1:
                    state = "touched"
                elif reading.value == 0:
                    state = "no touch"
                else:
                    state = "N/A"
                print(f"  {name} (pin {pin}):  {state}")
                if reading.raw_value:
                    print(f"      raw: {reading.raw_value}")
        print("=" * 60 + "\n")

    def print_back_touch_reading(self, reading: Optional[BackTouchSensorReading] = None):
        """Pretty print one back touch sensor reading."""
        if reading is None:
            reading = self.last_back_touch_reading
        if reading is None:
            print("❌ No back touch sensor reading available")
            return

        print("\n" + "=" * 60)
        print("BACK TOUCH SENSOR READING")
        print("=" * 60)
        print(f"  Timestamp:          {reading.timestamp.isoformat()}")
        print(f"  Location:           {reading.location:>35}")
        print(f"  Touch ID:           {reading.touch_id:>35}")
        value = reading.value if reading.value is not None else "N/A"
        print(f"  Raw Value (analog): {value:>35}")
        if not reading.ok:
            print("  ⚠ Value looks like a bad connection (0 < value < 600).")
        if reading.raw_value:
            print(f"  Raw Response:       {reading.raw_value}")
        print("=" * 60 + "\n")

    def print_imu_reading(self, reading: Optional[IMUSensorReading] = None):
        """Pretty print IMU sensor reading."""
        if reading is None:
            reading = self.last_imu_reading
        if reading is None:
            print("❌ No IMU reading available")
            return

        print("\n" + "=" * 60)
        print("IMU SENSOR READING (Accelerometer & Gyroscope)")
        print("=" * 60)
        print(f"  Timestamp:        {reading.timestamp.isoformat()}")
        print("  Accelerometer (m/s²):")
        print(f"    X: {reading.accel_x if reading.accel_x is not None else 'N/A':>40.1f}")
        print(f"    Y: {reading.accel_y if reading.accel_y is not None else 'N/A':>40.1f}")
        print(f"    Z: {reading.accel_z if reading.accel_z is not None else 'N/A':>40.1f}")
        print("  Gyroscope (°/s):")
        print(f"    X: {reading.gyro_x if reading.gyro_x is not None else 'N/A':>40.1f}")
        print(f"    Y: {reading.gyro_y if reading.gyro_y is not None else 'N/A':>40.1f}")
        print(f"    Z: {reading.gyro_z if reading.gyro_z is not None else 'N/A':>40.1f}")
        if reading.raw_value:
            print(f"  Raw: {reading.raw_value}")
        print("=" * 60 + "\n")

    def print_gesture_reading(self, reading: Optional[GestureSensorReading] = None):
        """Pretty print gesture sensor reading."""
        if reading is None:
            reading = self.last_gesture_reading
        if reading is None:
            print("❌ No gesture sensor reading available")
            return

        print("\n" + "=" * 60)
        print("GESTURE SENSOR READING")
        print("=" * 60)
        print(f"  Timestamp:  {reading.timestamp.isoformat()}")
        print(f"  Value:      {reading.value if reading.value is not None else 'N/A'}")
        print(f"  Gesture:    {reading.gesture if reading.gesture is not None else 'N/A'}")
        if reading.raw_value:
            print(f"  Raw:        {reading.raw_value}")
        print("  Legend:     -1=none  0=up  1=down  2=left  3=right")
        print("=" * 60 + "\n")


def show_help():
    """Display help information."""
    help_text = """
╔════════════════════════════════════════════════════════════════════╗
║    Petoi Bittle Bluetooth Interactive Controller v1.0              ║
╚════════════════════════════════════════════════════════════════════╝

COMMAND SYNTAX:
  motor <index> <angle>     - Control servo motor
  skill <name>              - Execute a predefined skill
  imu                       - Read IMU sensor (accelerometer/gyroscope)
  light [L|R]               - Read light sensor(s); no arg reads both (L=pin34, R=pin35)
  distance [L|R]            - Read IR distance sensor(s); no arg reads both (L=pin34, R=pin35)
  touch [L|R]               - Read touch sensor(s); no arg reads both (L=pin34, R=pin35)
  backtouch                 - Read the back touch sensor (Front Left/Front Right/Center/Back, pin38)
  light_on                  - Activate light sensor mode (XL)
  light_off                 - Deactivate light sensor mode (Xl)
  distance_on               - Activate IR distance mode (XD)
  distance_off              - Deactivate IR distance mode (Xd)
  touch_on                  - Activate touch mode (XT)
  touch_off                 - Deactivate touch mode (Xt)
  backtouch_on              - Activate back touch mode (XB)
  backtouch_off             - Deactivate back touch mode (Xb)
  gesture                   - Read one gesture value (auto-enables stream)
  gesture_on                - Enable gesture stream, dog stays still (XGPr)
  gesture_off               - Disable the gesture module (Xg)
  gesture_react             - Stream + let the dog react (XGPR)
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

SENSOR EXAMPLES:
  imu                       - Read IMU (accel/gyro data)
  light                     - Read both light sensors (left + right)
  light L                   - Read left light sensor  (GPIO 34)
  light R                   - Read right light sensor (GPIO 35)
  light 34                  - Read a pin number directly
  distance                  - Read both IR distance sensors (left + right)
  distance L                - Read left IR distance sensor  (GPIO 34)
  distance R                - Read right IR distance sensor (GPIO 35)
  distance_on               - Activate IR distance mode (XD) before reading
  touch                     - Read both touch pads (left + right)
  touch L                   - Read left touch pad  (GPIO 34)
  touch R                   - Read right touch pad (GPIO 35)
  touch_on                  - Activate touch mode (XT) before reading
  backtouch                 - Read the back touch sensor -> Front Left/Front Right/Center/Back
  backtouch_on              - Activate back touch mode (XB) before reading
  gesture                   - Read one gesture (wave your hand while it waits)
  gesture_on                - Start continuous gesture stream, dog still (XGPr)
  gesture_off               - Stop the gesture module (Xg)
  gesture_react             - Stream + let the dog react (XGPR)
  gesture values:           -1=none 0=up 1=down 2=left 3=right

DIRECT COMMANDS:
  Send raw Petoi commands directly:
  ksit, kwkF, m0 30, c10 5, s, etc.

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

            elif command == "imu":
                reading = await controller.read_imu_sensor()
                if reading:
                    controller.print_imu_reading(reading)

            elif command == "light":
                arg = parts[1].upper() if len(parts) > 1 else None
                if arg in ("L", "R"):
                    sensor_cmd = controller.resolve_light_command(arg)
                    reading = await controller.read_light_sensor(command=sensor_cmd)
                    if reading:
                        controller.print_light_reading(reading)
                else:
                    # No side given -> read both light sensors.
                    await controller.read_light_sensors()

            elif command == "distance":
                arg = parts[1].upper() if len(parts) > 1 else None
                if arg in ("L", "R"):
                    reading = await controller.read_distance_sensor(side=arg)
                    if reading:
                        controller.print_distance_reading(reading)
                else:
                    # No side given -> read both distance sensors.
                    await controller.read_distance_sensors()

            elif command == "touch":
                arg = parts[1].upper() if len(parts) > 1 else None
                if arg in ("L", "R"):
                    reading = await controller.read_touch_sensor(side=arg)
                    if reading:
                        controller.print_touch_reading(reading)
                else:
                    # No side given -> read both touch pads.
                    await controller.read_touch_sensors()

            elif command == "backtouch":
                reading = await controller.read_back_touch_sensor()
                if reading:
                    controller.print_back_touch_reading(reading)

            elif command == "light_on":
                await controller.activate_light_mode()

            elif command == "light_off":
                await controller.deactivate_light_mode()

            elif command == "distance_on":
                await controller.activate_distance_mode()

            elif command == "distance_off":
                await controller.deactivate_distance_mode()

            elif command == "touch_on":
                await controller.activate_touch_mode()

            elif command == "touch_off":
                await controller.deactivate_touch_mode()

            elif command == "backtouch_on":
                await controller.activate_back_touch_mode()

            elif command == "backtouch_off":
                await controller.deactivate_back_touch_mode()

            elif command == "gesture":
                reading = await controller.read_gesture_sensor()
                if reading:
                    controller.print_gesture_reading(reading)

            elif command == "gesture_on":
                await controller.activate_gesture_mode()

            elif command == "gesture_off":
                await controller.deactivate_gesture_mode()

            elif command == "gesture_react":
                await controller.activate_gesture_mode(reactions=True)

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
