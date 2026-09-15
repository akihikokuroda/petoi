#!/usr/bin/env python3
"""
Unit tests for Bittle backend controller.

Tests:
- Motor validation and bounds checking
- Skill validation
- Sequence execution with timing
- Status queries
- Error handling and recovery
- Connection management
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime

from bittle_backend import (
    BittleBackendController,
    RobotStatus,
    SequenceStep,
    MOTOR_NAME_TO_INDEX,
    MOTOR_INDEX_TO_NAME,
    SKILLS,
)


class TestMotorValidation:
    """Test motor validation and bounds checking"""

    def test_validate_motor_angle_valid(self):
        controller = BittleBackendController()
        valid, msg = controller.validate_motor_angle(0)
        assert valid is True
        assert "Valid" in msg

    def test_validate_motor_angle_min_boundary(self):
        controller = BittleBackendController()
        valid, msg = controller.validate_motor_angle(-90)
        assert valid is True

    def test_validate_motor_angle_max_boundary(self):
        controller = BittleBackendController()
        valid, msg = controller.validate_motor_angle(90)
        assert valid is True

    def test_validate_motor_angle_out_of_range_negative(self):
        controller = BittleBackendController()
        valid, msg = controller.validate_motor_angle(-91)
        assert valid is False
        assert "out of range" in msg

    def test_validate_motor_angle_out_of_range_positive(self):
        controller = BittleBackendController()
        valid, msg = controller.validate_motor_angle(91)
        assert valid is False
        assert "out of range" in msg

    def test_validate_motor_name_by_name(self):
        controller = BittleBackendController()
        valid, index, msg = controller.validate_motor_name_or_index("neck")
        assert valid is True
        assert index == 0

    def test_validate_motor_name_by_index(self):
        controller = BittleBackendController()
        valid, index, msg = controller.validate_motor_name_or_index("8")
        assert valid is True
        assert index == 8

    def test_validate_motor_invalid_name(self):
        controller = BittleBackendController()
        valid, index, msg = controller.validate_motor_name_or_index("invalid_motor")
        assert valid is False
        assert "Invalid motor" in msg

    def test_validate_motor_invalid_index(self):
        controller = BittleBackendController()
        valid, index, msg = controller.validate_motor_name_or_index("99")
        assert valid is False


class TestSkillExecution:
    """Test skill validation and execution"""

    @pytest.mark.asyncio
    async def test_get_available_skills(self):
        controller = BittleBackendController()
        skills = controller.get_available_skills()
        assert "sit" in skills
        assert "stand" in skills
        assert "walk_forward" in skills
        assert len(skills) == len(SKILLS)

    @pytest.mark.asyncio
    async def test_execute_skill_command_building(self):
        controller = BittleBackendController()
        with patch.object(controller, "send_command", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            await controller.execute_skill("sit")
            mock_send.assert_called_once_with("ksit")

    @pytest.mark.asyncio
    async def test_execute_invalid_skill(self):
        controller = BittleBackendController()
        with patch.object(controller, "send_command", new_callable=AsyncMock) as mock_send:
            result = await controller.execute_skill("invalid_skill")
            assert result is False
            mock_send.assert_not_called()


class TestMotorControl:
    """Test motor control"""

    @pytest.mark.asyncio
    async def test_control_motor_by_name(self):
        controller = BittleBackendController()
        with patch.object(controller, "send_command", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            result = await controller.control_motor("neck", 30)
            assert result is True
            mock_send.assert_called_once_with("m0 30")
            assert controller.motor_positions[0] == 30

    @pytest.mark.asyncio
    async def test_control_motor_by_index(self):
        controller = BittleBackendController()
        with patch.object(controller, "send_command", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            result = await controller.control_motor("8", -15)
            assert result is True
            mock_send.assert_called_once_with("m8 -15")
            assert controller.motor_positions[8] == -15

    @pytest.mark.asyncio
    async def test_control_motor_invalid_angle(self):
        controller = BittleBackendController()
        with patch.object(controller, "send_command", new_callable=AsyncMock) as mock_send:
            result = await controller.control_motor("neck", 180)
            assert result is False
            mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_control_motor_invalid_name(self):
        controller = BittleBackendController()
        with patch.object(controller, "send_command", new_callable=AsyncMock) as mock_send:
            result = await controller.control_motor("invalid", 30)
            assert result is False
            mock_send.assert_not_called()


class TestSequenceExecution:
    """Test sequence execution with timing"""

    @pytest.mark.asyncio
    async def test_sequence_step_skill(self):
        step = SequenceStep(duration=0.5, skill="sit")
        assert step.is_skill() is True
        assert step.get_skill() == "sit"
        assert step.duration == 0.5

    @pytest.mark.asyncio
    async def test_sequence_step_motor(self):
        step = SequenceStep(duration=0.3, motor="neck", angle=30)
        assert step.is_motor() is True
        assert step.get_motor_info() == ("neck", 30)

    @pytest.mark.asyncio
    async def test_execute_sequence_basic(self):
        controller = BittleBackendController()
        with patch.object(controller, "send_command", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True

            sequence = [
                {"skill": "sit", "duration": 0.1},
                {"motor": "neck", "angle": 30, "duration": 0.1},
            ]

            seq_id, steps = await controller.execute_sequence(sequence)
            assert "seq_" in seq_id
            assert steps == 2

    @pytest.mark.asyncio
    async def test_execute_sequence_with_repeat(self):
        controller = BittleBackendController()
        with patch.object(controller, "send_command", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True

            sequence = [{"skill": "sit", "duration": 0.01}]
            seq_id, steps = await controller.execute_sequence(sequence, repeat=3)
            assert steps == 3
            assert mock_send.call_count == 3

    @pytest.mark.asyncio
    async def test_interrupt_sequence(self):
        controller = BittleBackendController()
        controller.is_sequence_running = True
        controller.interrupt_sequence()
        assert controller.is_sequence_running is False

    @pytest.mark.asyncio
    async def test_sequence_already_running(self):
        controller = BittleBackendController()
        controller.is_sequence_running = True
        sequence = [{"skill": "sit", "duration": 0.01}]
        seq_id, steps = await controller.execute_sequence(sequence)
        assert seq_id == ""
        assert steps == 0


class TestRobotStatus:
    """Test status query and reporting"""

    @pytest.mark.asyncio
    async def test_get_status_disconnected(self):
        controller = BittleBackendController()
        controller.connected = False
        status = await controller.get_status()
        assert status.connected is False
        assert status.error == "Robot is not connected"

    @pytest.mark.asyncio
    async def test_get_status_connected(self):
        controller = BittleBackendController()
        controller.connected = True
        controller.battery_voltage = 7.5
        controller.current_motion = "walking"
        controller.motor_positions = {0: 30}

        status = await controller.get_status()
        assert status.connected is True
        assert status.battery_voltage == 7.5
        assert status.current_motion == "walking"
        assert 0 in status.motor_positions

    @pytest.mark.asyncio
    async def test_get_status_low_battery(self):
        controller = BittleBackendController()
        controller.connected = True
        controller.battery_voltage = 5.5
        status = await controller.get_status()
        assert "Low battery" in status.error


class TestBeepAndCalibration:
    """Test beep and calibration features"""

    @pytest.mark.asyncio
    async def test_beep_valid_frequency(self):
        controller = BittleBackendController()
        with patch.object(controller, "send_command", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            result = await controller.beep(frequency=1000, duration=100)
            assert result is True
            mock_send.assert_called_once_with("b1000")

    @pytest.mark.asyncio
    async def test_beep_invalid_frequency_low(self):
        controller = BittleBackendController()
        with patch.object(controller, "send_command", new_callable=AsyncMock) as mock_send:
            result = await controller.beep(frequency=10, duration=100)
            assert result is False
            mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_beep_invalid_frequency_high(self):
        controller = BittleBackendController()
        with patch.object(controller, "send_command", new_callable=AsyncMock) as mock_send:
            result = await controller.beep(frequency=30000, duration=100)
            assert result is False
            mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_calibrate_motor(self):
        controller = BittleBackendController()
        with patch.object(controller, "send_command", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            result = await controller.calibrate_motor("neck", offset=5)
            assert result is True
            mock_send.assert_called_once_with("c0 5")
            assert controller.motor_positions[0] == 5


class TestConnectionManagement:
    """Test connection health checks and management"""

    @pytest.mark.asyncio
    async def test_check_connection_health_disconnected(self):
        controller = BittleBackendController()
        controller.connected = False
        health = await controller.check_connection_health()
        assert health is False

    @pytest.mark.asyncio
    async def test_check_connection_health_connected(self):
        controller = BittleBackendController()
        controller.connected = True
        mock_client = MagicMock()
        mock_client.is_connected = True
        controller.client = mock_client

        health = await controller.check_connection_health()
        assert health is True

    @pytest.mark.asyncio
    async def test_get_connection_uptime(self):
        import time
        controller = BittleBackendController()
        controller.connected = False
        assert controller.get_connection_uptime() is None

        controller.connected = True
        controller.connection_time = time.time() - 10
        uptime = controller.get_connection_uptime()
        assert uptime is not None
        assert uptime >= 10

    @pytest.mark.asyncio
    async def test_emergency_stop(self):
        controller = BittleBackendController()
        controller.connected = True
        controller.is_sequence_running = True
        mock_client = MagicMock()
        mock_client.disconnect = AsyncMock()
        controller.client = mock_client

        await controller.emergency_stop()
        assert controller.is_sequence_running is False


class TestAvailableResources:
    """Test getting available resources"""

    def test_get_available_motors(self):
        controller = BittleBackendController()
        motors = controller.get_available_motors()
        assert 0 in motors
        assert 8 in motors
        assert "Neck" in motors[0]

    def test_get_motor_range(self):
        controller = BittleBackendController()
        min_angle, max_angle = controller.get_motor_range()
        assert min_angle == -90
        assert max_angle == 90


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
