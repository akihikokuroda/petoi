#!/usr/bin/env python3
"""
End-to-end tests with mocked Bittle hardware.

Simulates:
- Bittle Bluetooth connection
- Command execution
- Status responses
- Error scenarios
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from bittle_backend import BittleBackendController, RobotStatus
from bittle_mellea_tools import BittleMelleaTools


class MockBleakClient:
    """Mock Bleak client for testing without hardware"""

    def __init__(self):
        self.is_connected = False
        self.written_commands = []

    async def connect(self):
        self.is_connected = True

    async def disconnect(self):
        self.is_connected = False

    async def write_gatt_char(self, char, data):
        self.written_commands.append(data.decode())


class TestE2EWithMockHardware:
    """End-to-end tests with mocked Bittle hardware"""

    @pytest.mark.asyncio
    async def test_simple_skill_execution(self):
        """Test: User says 'sit down', robot executes sit skill"""
        controller = BittleBackendController()
        tools = BittleMelleaTools(controller)

        with patch("bittle_backend.BleakClient", return_value=MockBleakClient()):
            with patch("bittle_backend.BleakScanner.discover", new_callable=AsyncMock) as mock_discover:
                mock_device = MagicMock()
                mock_device.name = "Bittle"
                mock_device.address = "AA:BB:CC:DD:EE:FF"
                mock_discover.return_value = [mock_device]

                assert await controller.connect()
                result = await tools.execute_skill("sit")

                assert result["success"] is True
                assert result["skill"] == "sit"

    @pytest.mark.asyncio
    async def test_motor_control_sequence(self):
        """Test: User says 'look around', robot moves neck left and right"""
        controller = BittleBackendController()
        tools = BittleMelleaTools(controller)

        with patch("bittle_backend.BleakClient", return_value=MockBleakClient()):
            with patch("bittle_backend.BleakScanner.discover", new_callable=AsyncMock) as mock_discover:
                mock_device = MagicMock()
                mock_device.name = "Bittle"
                mock_device.address = "AA:BB:CC:DD:EE:FF"
                mock_discover.return_value = [mock_device]

                assert await controller.connect()

                sequence = [
                    {"motor": "neck", "angle": -45, "duration": 0.01},
                    {"motor": "neck", "angle": 0, "duration": 0.01},
                    {"motor": "neck", "angle": 45, "duration": 0.01},
                    {"motor": "neck", "angle": 0, "duration": 0.01},
                ]

                result = await tools.sequence_motion(sequence)
                assert result["success"] is True
                assert result["steps_executed"] == 4

    @pytest.mark.asyncio
    async def test_dance_sequence(self):
        """Test: User says 'dance', robot executes complex dance sequence"""
        controller = BittleBackendController()
        tools = BittleMelleaTools(controller)

        with patch("bittle_backend.BleakClient", return_value=MockBleakClient()):
            with patch("bittle_backend.BleakScanner.discover", new_callable=AsyncMock) as mock_discover:
                mock_device = MagicMock()
                mock_device.name = "Bittle"
                mock_device.address = "AA:BB:CC:DD:EE:FF"
                mock_discover.return_value = [mock_device]

                assert await controller.connect()

                sequence = [
                    {"skill": "stand", "duration": 0.01},
                    {"skill": "trot_left", "duration": 0.01},
                    {"skill": "trot_right", "duration": 0.01},
                    {"motor": "left_arm", "angle": 45, "duration": 0.01},
                    {"motor": "right_arm", "angle": -45, "duration": 0.01},
                    {"motor": "left_arm", "angle": -45, "duration": 0.01},
                    {"motor": "right_arm", "angle": 45, "duration": 0.01},
                ]

                result = await tools.sequence_motion(sequence, repeat=2)
                assert result["success"] is True
                assert result["steps_executed"] == 14

    @pytest.mark.asyncio
    async def test_status_check_workflow(self):
        """Test: User asks 'Are you okay?', robot reports status"""
        controller = BittleBackendController()
        tools = BittleMelleaTools(controller)

        with patch("bittle_backend.BleakClient", return_value=MockBleakClient()):
            with patch("bittle_backend.BleakScanner.discover", new_callable=AsyncMock) as mock_discover:
                mock_device = MagicMock()
                mock_device.name = "Bittle"
                mock_device.address = "AA:BB:CC:DD:EE:FF"
                mock_discover.return_value = [mock_device]

                assert await controller.connect()

                controller.battery_voltage = 7.2
                controller.current_motion = "idle"

                result = await tools.get_status()
                assert result["success"] is True
                assert result["connected"] is True
                assert result["battery_voltage"] == 7.2

    @pytest.mark.asyncio
    async def test_battery_warning_workflow(self):
        """Test: Robot warns when battery is low"""
        controller = BittleBackendController()
        tools = BittleMelleaTools(controller)

        controller.connected = True
        controller.battery_voltage = 5.5  # Below 6.0V threshold

        result = await tools.get_status()
        assert result["success"] is True
        assert "error" in result
        assert "Low battery" in result["error"]

    @pytest.mark.asyncio
    async def test_invalid_command_handling(self):
        """Test: Robot handles invalid commands gracefully"""
        controller = BittleBackendController()
        tools = BittleMelleaTools(controller)

        with patch("bittle_backend.BleakClient", return_value=MockBleakClient()):
            with patch("bittle_backend.BleakScanner.discover", new_callable=AsyncMock) as mock_discover:
                mock_device = MagicMock()
                mock_device.name = "Bittle"
                mock_device.address = "AA:BB:CC:DD:EE:FF"
                mock_discover.return_value = [mock_device]

                assert await controller.connect()

                # Test invalid skill
                result = await tools.execute_skill("invalid_skill")
                assert result["success"] is False
                assert "Unknown skill" in result["message"]

                # Test invalid motor
                result = await tools.control_motor("invalid_motor", 45)
                assert result["success"] is False
                assert "Invalid motor" in result["message"]

                # Test invalid angle
                result = await tools.control_motor("neck", 180)
                assert result["success"] is False
                assert "out of range" in result["message"]

    @pytest.mark.asyncio
    async def test_connection_failure_recovery(self):
        """Test: System recovers from connection failures"""
        controller = BittleBackendController()

        with patch("bittle_backend.BleakScanner.discover", new_callable=AsyncMock) as mock_discover:
            # First attempt: no devices found
            mock_discover.return_value = []
            assert not await controller.connect()

            # Second attempt: device found but connection fails
            mock_device = MagicMock()
            mock_device.name = "Bittle"
            mock_device.address = "AA:BB:CC:DD:EE:FF"
            mock_discover.return_value = [mock_device]

            with patch("bittle_backend.BleakClient") as mock_client_class:
                mock_client = MagicMock()
                mock_client.connect = AsyncMock(side_effect=Exception("Connection refused"))
                mock_client_class.return_value = mock_client

                assert not await controller.connect()

            # Third attempt: successful
            mock_discover.return_value = [mock_device]
            with patch("bittle_backend.BleakClient", return_value=MockBleakClient()):
                assert await controller.connect()

    @pytest.mark.asyncio
    async def test_sequence_interrupt(self):
        """Test: Can interrupt running sequence"""
        controller = BittleBackendController()
        tools = BittleMelleaTools(controller)

        with patch("bittle_backend.BleakClient", return_value=MockBleakClient()):
            with patch("bittle_backend.BleakScanner.discover", new_callable=AsyncMock) as mock_discover:
                mock_device = MagicMock()
                mock_device.name = "Bittle"
                mock_device.address = "AA:BB:CC:DD:EE:FF"
                mock_discover.return_value = [mock_device]

                assert await controller.connect()

                sequence = [
                    {"skill": "sit", "duration": 0.05},
                    {"skill": "stand", "duration": 0.05},
                    {"skill": "sit", "duration": 0.05},
                ]

                async def execute_and_interrupt():
                    # Start sequence in background
                    task = asyncio.create_task(tools.sequence_motion(sequence))
                    await asyncio.sleep(0.01)  # Let it start
                    controller.interrupt_sequence()  # Interrupt
                    return await task

                result = await execute_and_interrupt()
                assert result["success"] is True
                assert result["steps_executed"] < 3  # Should be less due to interrupt

    @pytest.mark.asyncio
    async def test_multi_turn_conversation_mock(self):
        """Test: Multi-turn conversation with status tracking"""
        controller = BittleBackendController()
        tools = BittleMelleaTools(controller)

        with patch("bittle_backend.BleakClient", return_value=MockBleakClient()):
            with patch("bittle_backend.BleakScanner.discover", new_callable=AsyncMock) as mock_discover:
                mock_device = MagicMock()
                mock_device.name = "Bittle"
                mock_device.address = "AA:BB:CC:DD:EE:FF"
                mock_discover.return_value = [mock_device]

                assert await controller.connect()
                controller.battery_voltage = 7.5

                # Turn 1: Execute action
                result1 = await tools.execute_skill("sit")
                assert result1["success"] is True
                assert controller.current_motion == "sit"

                # Turn 2: Check status
                result2 = await tools.get_status()
                assert result2["success"] is True
                assert result2["battery_voltage"] == 7.5

                # Turn 3: Execute motor control
                result3 = await tools.control_motor("neck", 45)
                assert result3["success"] is True
                assert controller.motor_positions[0] == 45

                # Turn 4: Check status again
                result4 = await tools.get_status()
                assert result4["success"] is True
                assert result4["motor_positions"][0] == 45

    @pytest.mark.asyncio
    async def test_all_motors_controllable(self):
        """Test: All available motors can be controlled"""
        controller = BittleBackendController()
        tools = BittleMelleaTools(controller)

        with patch("bittle_backend.BleakClient", return_value=MockBleakClient()):
            with patch("bittle_backend.BleakScanner.discover", new_callable=AsyncMock) as mock_discover:
                mock_device = MagicMock()
                mock_device.name = "Bittle"
                mock_device.address = "AA:BB:CC:DD:EE:FF"
                mock_discover.return_value = [mock_device]

                assert await controller.connect()

                motors = [
                    "neck", "left_shoulder", "right_shoulder", "right_hip", "left_hip",
                    "left_arm", "right_arm", "right_ankle", "left_ankle"
                ]

                for motor in motors:
                    result = await tools.control_motor(motor, 45)
                    assert result["success"] is True, f"Motor {motor} should be controllable"

    @pytest.mark.asyncio
    async def test_all_skills_executable(self):
        """Test: All available skills can be executed"""
        controller = BittleBackendController()
        tools = BittleMelleaTools(controller)

        with patch("bittle_backend.BleakClient", return_value=MockBleakClient()):
            with patch("bittle_backend.BleakScanner.discover", new_callable=AsyncMock) as mock_discover:
                mock_device = MagicMock()
                mock_device.name = "Bittle"
                mock_device.address = "AA:BB:CC:DD:EE:FF"
                mock_discover.return_value = [mock_device]

                assert await controller.connect()

                skills = controller.get_available_skills()

                for skill in skills:
                    result = await tools.execute_skill(skill)
                    assert result["success"] is True, f"Skill {skill} should be executable"

    @pytest.mark.asyncio
    async def test_beep_feedback(self):
        """Test: Beep feedback works"""
        controller = BittleBackendController()
        tools = BittleMelleaTools(controller)

        with patch("bittle_backend.BleakClient", return_value=MockBleakClient()):
            with patch("bittle_backend.BleakScanner.discover", new_callable=AsyncMock) as mock_discover:
                mock_device = MagicMock()
                mock_device.name = "Bittle"
                mock_device.address = "AA:BB:CC:DD:EE:FF"
                mock_discover.return_value = [mock_device]

                assert await controller.connect()

                result = await tools.beep(frequency=1000, duration=100)
                assert result["success"] is True

    @pytest.mark.asyncio
    async def test_motor_calibration(self):
        """Test: Motor calibration works"""
        controller = BittleBackendController()
        tools = BittleMelleaTools(controller)

        with patch("bittle_backend.BleakClient", return_value=MockBleakClient()):
            with patch("bittle_backend.BleakScanner.discover", new_callable=AsyncMock) as mock_discover:
                mock_device = MagicMock()
                mock_device.name = "Bittle"
                mock_device.address = "AA:BB:CC:DD:EE:FF"
                mock_discover.return_value = [mock_device]

                assert await controller.connect()

                result = await tools.calibrate_motor("neck", offset=5)
                assert result["success"] is True
                assert controller.motor_positions[0] == 5

    @pytest.mark.asyncio
    async def test_complex_dance_with_variations(self):
        """Test: Complex dance with multiple variations"""
        controller = BittleBackendController()
        tools = BittleMelleaTools(controller)

        with patch("bittle_backend.BleakClient", return_value=MockBleakClient()):
            with patch("bittle_backend.BleakScanner.discover", new_callable=AsyncMock) as mock_discover:
                mock_device = MagicMock()
                mock_device.name = "Bittle"
                mock_device.address = "AA:BB:CC:DD:EE:FF"
                mock_discover.return_value = [mock_device]

                assert await controller.connect()

                # Dance variation 1: Head shake
                sequence1 = [
                    {"motor": "neck", "angle": -30, "duration": 0.01},
                    {"motor": "neck", "angle": 30, "duration": 0.01},
                    {"motor": "neck", "angle": 0, "duration": 0.01},
                ]
                result1 = await tools.sequence_motion(sequence1)
                assert result1["success"] is True

                # Dance variation 2: Walking with arm movements
                sequence2 = [
                    {"skill": "walk_forward", "duration": 0.01},
                    {"motor": "left_arm", "angle": 45, "duration": 0.01},
                    {"motor": "right_arm", "angle": -45, "duration": 0.01},
                    {"motor": "left_arm", "angle": -45, "duration": 0.01},
                    {"motor": "right_arm", "angle": 45, "duration": 0.01},
                ]
                result2 = await tools.sequence_motion(sequence2)
                assert result2["success"] is True

                # Dance variation 3: Trotting with body roll
                sequence3 = [
                    {"skill": "trot_left", "duration": 0.01},
                    {"skill": "trot_right", "duration": 0.01},
                ]
                result3 = await tools.sequence_motion(sequence3)
                assert result3["success"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
