#!/usr/bin/env python3
"""
Petoi Bittle Backend Controller - Full implementation of LLM_CONTROLLER_DESIGN.md

Provides:
- Enhanced BittleBLEController with async methods for all tools
- Motor validation and bounds checking
- Sequence execution with timing
- Status query endpoint
- Error handling and recovery
- Battery monitoring
- Connection health checks
"""

import asyncio
import time
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import logging

try:
    from bleak import BleakClient, BleakScanner
except ImportError:
    print("❌ Bleak not installed. Install with: pip install bleak")
    exit(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MotorName(str, Enum):
    """Motor name mappings"""
    NECK = "neck"
    LEFT_SHOULDER = "left_shoulder"
    RIGHT_SHOULDER = "right_shoulder"
    RIGHT_HIP = "right_hip"
    LEFT_HIP = "left_hip"
    LEFT_ARM = "left_arm"
    RIGHT_ARM = "right_arm"
    RIGHT_ANKLE = "right_ankle"
    LEFT_ANKLE = "left_ankle"


MOTOR_NAME_TO_INDEX = {
    MotorName.NECK.value: 0,
    MotorName.LEFT_SHOULDER.value: 8,
    MotorName.RIGHT_SHOULDER.value: 9,
    MotorName.RIGHT_HIP.value: 10,
    MotorName.LEFT_HIP.value: 11,
    MotorName.LEFT_ARM.value: 12,
    MotorName.RIGHT_ARM.value: 13,
    MotorName.RIGHT_ANKLE.value: 14,
    MotorName.LEFT_ANKLE.value: 15,
}

MOTOR_INDEX_TO_NAME = {v: k for k, v in MOTOR_NAME_TO_INDEX.items()}

MOTOR_INDEX_NAMES = {
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


@dataclass
class MotorPosition:
    """Represents a motor's current position"""
    name: str
    index: int
    angle: int
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RobotStatus:
    """Robot status snapshot"""
    connected: bool
    battery_voltage: Optional[float] = None
    current_motion: str = "unknown"
    motor_positions: Dict[str, int] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    is_charging: bool = False
    last_command: Optional[str] = None
    error: Optional[str] = None


class SequenceStep:
    """Represents a single step in a motion sequence"""

    def __init__(self, duration: float = 0.1, **kwargs):
        self.duration = duration
        self.data = kwargs

    def is_skill(self) -> bool:
        return "skill" in self.data

    def is_motor(self) -> bool:
        return "motor" in self.data and "angle" in self.data

    def get_skill(self) -> Optional[str]:
        return self.data.get("skill")

    def get_motor_info(self) -> Optional[Tuple[str, int]]:
        if self.is_motor():
            return self.data.get("motor"), self.data.get("angle")
        return None


class BittleBackendController:
    """Enhanced Bittle BLE controller with full backend implementation"""

    MOTOR_ANGLE_MIN = -90
    MOTOR_ANGLE_MAX = 90
    COMMAND_DELAY = 0.05
    BATTERY_WARNING_THRESHOLD = 6.0
    CONNECTION_TIMEOUT = 10.0

    def __init__(self, address: Optional[str] = None, command_delay: float = 0.05):
        self.address = address
        self.command_delay = command_delay
        self.client: Optional[BleakClient] = None
        self.char = None
        self.connected = False

        self.motor_positions: Dict[int, int] = {}
        self.battery_voltage: Optional[float] = None
        self.current_motion: str = "idle"
        self.last_command: Optional[str] = None
        self.last_command_time: Optional[float] = None
        self.connection_time: Optional[float] = None
        self.is_sequence_running = False
        self.sequence_id_counter = 0

    async def discover_bittle(self) -> Optional[str]:
        """Discover Bittle device via BLE"""
        logger.info("Scanning for Bittle device...")
        try:
            devices = await asyncio.wait_for(
                BleakScanner.discover(),
                timeout=self.CONNECTION_TIMEOUT
            )
            logger.info(f"Found {len(devices)} device(s)")

            for device in devices:
                if device.name and "Bittle" in device.name:
                    logger.info(f"✓ Bittle found: {device.name} ({device.address})")
                    return device.address

            logger.warning("❌ Bittle device not found")
            return None
        except asyncio.TimeoutError:
            logger.error("Device discovery timed out")
            return None
        except Exception as e:
            logger.error(f"Discovery failed: {e}")
            return None

    async def find_writable_characteristic(self):
        """Find writable characteristic in GATT services"""
        try:
            for service in self.client.services:
                for char in service.characteristics:
                    if "write" in char.properties:
                        logger.info(f"Found writable characteristic: {char.uuid}")
                        return char
            return None
        except Exception as e:
            logger.error(f"Failed to find characteristic: {e}")
            return None

    async def connect(self) -> bool:
        """Connect to Bittle robot"""
        try:
            if self.address is None:
                self.address = await self.discover_bittle()
                if self.address is None:
                    return False

            logger.info(f"Connecting to {self.address}...")
            self.client = BleakClient(self.address)
            await asyncio.wait_for(self.client.connect(), timeout=self.CONNECTION_TIMEOUT)
            self.connected = True
            self.connection_time = time.time()
            logger.info(f"✓ Connected to Bittle")

            self.char = await self.find_writable_characteristic()
            if not self.char:
                logger.error("Could not find writable characteristic")
                await self.disconnect()
                return False

            await asyncio.sleep(0.5)
            return True
        except asyncio.TimeoutError:
            logger.error("Connection timed out")
            self.connected = False
            return False
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self.connected = False
            return False

    async def disconnect(self):
        """Disconnect from Bittle"""
        if self.client:
            try:
                await self.client.disconnect()
            except Exception as e:
                logger.error(f"Error during disconnect: {e}")
            self.connected = False
            logger.info("✓ Disconnected")

    async def send_command(self, command: str) -> bool:
        """Send command to Bittle with error handling"""
        if not self.connected or not self.client or not self.char:
            logger.error("Not connected to Bittle")
            return False

        try:
            cmd_bytes = command.encode()
            await self.client.write_gatt_char(self.char, cmd_bytes)
            logger.info(f"→ Sent: {command}")
            self.last_command = command
            self.last_command_time = time.time()
            await asyncio.sleep(self.command_delay)
            return True
        except Exception as e:
            logger.error(f"Failed to send command: {e}")
            self.connected = False
            return False

    def validate_motor_angle(self, angle: int) -> Tuple[bool, str]:
        """Validate motor angle bounds"""
        if angle < self.MOTOR_ANGLE_MIN or angle > self.MOTOR_ANGLE_MAX:
            return False, f"Angle {angle}° out of range [{self.MOTOR_ANGLE_MIN}, {self.MOTOR_ANGLE_MAX}]"
        return True, "Valid"

    def validate_motor_name_or_index(self, motor: str) -> Tuple[bool, int, str]:
        """
        Validate motor name or index and return the index.
        Returns: (is_valid, motor_index, message)
        """
        try:
            if motor in MOTOR_NAME_TO_INDEX:
                return True, MOTOR_NAME_TO_INDEX[motor], f"Motor: {motor}"
            if motor.isdigit():
                index = int(motor)
                if index in MOTOR_INDEX_TO_NAME:
                    return True, index, f"Motor index: {index}"
        except (ValueError, KeyError):
            pass

        available = list(MOTOR_NAME_TO_INDEX.keys()) + list(str(i) for i in MOTOR_NAME_TO_INDEX.values())
        return False, -1, f"Invalid motor: {motor}. Available: {available}"

    async def execute_skill(self, skill_name: str) -> bool:
        """Execute predefined skill with validation"""
        if skill_name not in SKILLS:
            logger.error(f"Unknown skill: {skill_name}")
            return False

        cmd = SKILLS[skill_name]
        self.current_motion = skill_name
        return await self.send_command(cmd)

    async def control_motor(self, motor_name: str, angle: int, duration: float = 0.1) -> bool:
        """Control individual motor with validation"""
        valid, msg = self.validate_motor_angle(angle)
        if not valid:
            logger.error(msg)
            return False

        valid, motor_index, msg = self.validate_motor_name_or_index(motor_name)
        if not valid:
            logger.error(msg)
            return False

        cmd = f"m{motor_index} {angle}"
        success = await self.send_command(cmd)
        if success:
            self.motor_positions[motor_index] = angle
        return success

    async def execute_sequence(
        self,
        sequence: List[Dict[str, Any]],
        repeat: int = 1,
        loop_forever: bool = False
    ) -> Tuple[str, int]:
        """
        Execute sequence of motor movements with timing.
        Returns: (sequence_id, steps_executed)
        """
        if self.is_sequence_running:
            logger.warning("Another sequence is already running")
            return "", 0

        self.is_sequence_running = True
        self.sequence_id_counter += 1
        sequence_id = f"seq_{self.sequence_id_counter}_{int(time.time())}"
        steps_executed = 0

        try:
            iteration = 0
            while iteration < repeat or loop_forever:
                for step in sequence:
                    if not self.is_sequence_running:
                        break

                    step_obj = SequenceStep(**step)

                    try:
                        if step_obj.is_skill():
                            skill = step_obj.get_skill()
                            success = await self.execute_skill(skill)
                            if success:
                                steps_executed += 1
                        elif step_obj.is_motor():
                            motor, angle = step_obj.get_motor_info()
                            success = await self.control_motor(motor, angle, step_obj.duration)
                            if success:
                                steps_executed += 1

                        if step_obj.duration > 0:
                            await asyncio.sleep(step_obj.duration)
                    except Exception as e:
                        logger.error(f"Error executing step: {e}")
                        continue

                iteration += 1

            logger.info(f"Sequence {sequence_id} completed: {steps_executed} steps")
            return sequence_id, steps_executed
        finally:
            self.is_sequence_running = False

    def interrupt_sequence(self):
        """Stop currently running sequence"""
        self.is_sequence_running = False
        logger.info("Sequence interrupted")

    async def get_status(self) -> RobotStatus:
        """Query current robot status"""
        status = RobotStatus(
            connected=self.connected,
            battery_voltage=self.battery_voltage,
            current_motion=self.current_motion,
            motor_positions=self.motor_positions.copy(),
            timestamp=datetime.utcnow().isoformat() + "Z",
            last_command=self.last_command,
        )

        if not self.connected:
            status.error = "Robot is not connected"

        if self.battery_voltage and self.battery_voltage < self.BATTERY_WARNING_THRESHOLD:
            status.error = f"Low battery: {self.battery_voltage}V"

        return status

    async def beep(self, frequency: int = 1000, duration: float = 100) -> bool:
        """Make robot produce beep sound"""
        if frequency < 20 or frequency > 20000:
            logger.error(f"Frequency {frequency}Hz out of valid range [20, 20000]")
            return False

        cmd = f"b{int(frequency)}"
        return await self.send_command(cmd)

    async def calibrate_motor(self, motor_name: str, offset: int = 0) -> bool:
        """Calibrate motor to neutral position with optional offset"""
        if offset < self.MOTOR_ANGLE_MIN or offset > self.MOTOR_ANGLE_MAX:
            logger.error(f"Offset {offset}° out of range")
            return False

        valid, motor_index, msg = self.validate_motor_name_or_index(motor_name)
        if not valid:
            logger.error(msg)
            return False

        cmd = f"c{motor_index} {offset}"
        success = await self.send_command(cmd)
        if success:
            self.motor_positions[motor_index] = offset
        return success

    async def check_connection_health(self) -> bool:
        """Check if connection is still alive"""
        if not self.connected:
            return False

        try:
            if self.client and self.client.is_connected:
                return True
            else:
                self.connected = False
                return False
        except Exception as e:
            logger.error(f"Connection health check failed: {e}")
            self.connected = False
            return False

    def get_connection_uptime(self) -> Optional[float]:
        """Get how long the connection has been active (in seconds)"""
        if not self.connected or not self.connection_time:
            return None
        return time.time() - self.connection_time

    async def emergency_stop(self):
        """Interrupt sequence and force disconnect"""
        self.interrupt_sequence()
        await self.disconnect()
        logger.info("❌ EMERGENCY STOP activated")

    def get_available_skills(self) -> List[str]:
        """Get list of available skills"""
        return list(SKILLS.keys())

    def get_available_motors(self) -> Dict[int, str]:
        """Get map of motor indices to names"""
        return MOTOR_INDEX_NAMES.copy()

    def get_motor_range(self) -> Tuple[int, int]:
        """Get valid motor angle range"""
        return self.MOTOR_ANGLE_MIN, self.MOTOR_ANGLE_MAX
