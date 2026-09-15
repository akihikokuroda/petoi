#!/usr/bin/env python3
"""
Integration tests for Bittle controller.

These tests check:
- End-to-end tool execution
- Error recovery
- Multi-step sequences
- Connection management
- LLM integration (with mock Mellea)
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime

from bittle_backend import BittleBackendController
from bittle_mellea_tools import BittleMelleaTools


class TestToolExecution:
    """Test tool execution through Mellea interface"""

    def test_tool_registry(self):
        controller = BittleBackendController()
        tools = BittleMelleaTools(controller)

        registry = tools.tool_registry
        assert "bittle_execute_skill" in registry
        assert "bittle_control_motor" in registry
        assert "bittle_sequence_motion" in registry
        assert "bittle_get_status" in registry
        assert "bittle_beep" in registry
        assert "bittle_calibrate_motor" in registry

    def test_tool_definitions_schema(self):
        controller = BittleBackendController()
        tools = BittleMelleaTools(controller)

        definitions = tools.get_tool_definitions()
        assert len(definitions) == 6

        # Check structure
        for tool in definitions:
            assert "name" in tool
            assert "description" in tool
            assert "input_schema" in tool

    @pytest.mark.asyncio
    async def test_execute_skill_tool(self):
        controller = BittleBackendController()
        tools = BittleMelleaTools(controller)

        with patch.object(controller, "send_command", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            result = await tools.execute_skill("sit")
            assert result["success"] is True
            assert result["skill"] == "sit"

    @pytest.mark.asyncio
    async def test_execute_skill_tool_invalid(self):
        controller = BittleBackendController()
        tools = BittleMelleaTools(controller)

        result = await tools.execute_skill("invalid_skill")
        assert result["success"] is False
        assert "Unknown skill" in result["message"]

    @pytest.mark.asyncio
    async def test_control_motor_tool(self):
        controller = BittleBackendController()
        tools = BittleMelleaTools(controller)

        with patch.object(controller, "send_command", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            result = await tools.control_motor("neck", 45)
            assert result["success"] is True
            assert result["motor"] == "neck"
            assert result["angle"] == 45

    @pytest.mark.asyncio
    async def test_control_motor_tool_validation(self):
        controller = BittleBackendController()
        tools = BittleMelleaTools(controller)

        result = await tools.control_motor("neck", 180)
        assert result["success"] is False
        assert "out of range" in result["message"]

    @pytest.mark.asyncio
    async def test_sequence_motion_tool(self):
        controller = BittleBackendController()
        tools = BittleMelleaTools(controller)

        with patch.object(controller, "send_command", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True

            sequence = [
                {"skill": "sit", "duration": 0.01},
                {"motor": "neck", "angle": 30, "duration": 0.01},
            ]

            result = await tools.sequence_motion(sequence)
            assert result["success"] is True
            assert "sequence_id" in result
            assert result["steps_executed"] == 2

    @pytest.mark.asyncio
    async def test_get_status_tool(self):
        controller = BittleBackendController()
        tools = BittleMelleaTools(controller)

        controller.connected = True
        controller.battery_voltage = 7.5
        controller.current_motion = "idle"

        result = await tools.get_status()
        assert result["success"] is True
        assert result["connected"] is True
        assert result["battery_voltage"] == 7.5

    @pytest.mark.asyncio
    async def test_beep_tool(self):
        controller = BittleBackendController()
        tools = BittleMelleaTools(controller)

        with patch.object(controller, "send_command", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            result = await tools.beep(frequency=1000, duration=100)
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_calibrate_motor_tool(self):
        controller = BittleBackendController()
        tools = BittleMelleaTools(controller)

        with patch.object(controller, "send_command", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            result = await tools.calibrate_motor("neck", offset=5)
            assert result["success"] is True
            assert result["motor"] == "neck"

    @pytest.mark.asyncio
    async def test_execute_tool_by_name(self):
        controller = BittleBackendController()
        tools = BittleMelleaTools(controller)

        with patch.object(controller, "send_command", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            result = await tools.execute_tool("bittle_beep", frequency=1000)
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self):
        controller = BittleBackendController()
        tools = BittleMelleaTools(controller)

        result = await tools.execute_tool("unknown_tool")
        assert result["success"] is False
        assert "Unknown tool" in result["message"]


class TestComplexScenarios:
    """Test complex interaction scenarios"""

    @pytest.mark.asyncio
    async def test_multi_step_dance_sequence(self):
        """Simulate a dance sequence"""
        controller = BittleBackendController()
        tools = BittleMelleaTools(controller)

        with patch.object(controller, "send_command", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True

            # Dance sequence: stand → trot left → trot right → repeat
            sequence = [
                {"skill": "stand", "duration": 0.01},
                {"skill": "trot_left", "duration": 0.01},
                {"skill": "trot_right", "duration": 0.01},
                {"motor": "left_arm", "angle": 45, "duration": 0.01},
                {"motor": "right_arm", "angle": -45, "duration": 0.01},
            ]

            result = await tools.sequence_motion(sequence, repeat=2)
            assert result["success"] is True
            assert result["steps_executed"] == 10  # 5 steps × 2 repeats

    @pytest.mark.asyncio
    async def test_look_around_sequence(self):
        """Simulate looking around (neck movements)"""
        controller = BittleBackendController()
        tools = BittleMelleaTools(controller)

        with patch.object(controller, "send_command", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True

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
    async def test_error_recovery_in_sequence(self):
        """Test that sequence continues despite step failures"""
        controller = BittleBackendController()
        tools = BittleMelleaTools(controller)

        with patch.object(controller, "send_command", new_callable=AsyncMock) as mock_send:
            mock_send.side_effect = [True, Exception("Command failed"), True]

            sequence = [
                {"skill": "sit", "duration": 0.01},
                {"skill": "stand", "duration": 0.01},
                {"skill": "sit", "duration": 0.01},
            ]

            result = await tools.sequence_motion(sequence)
            assert result["success"] is True
            # Should execute 2 successful steps despite 1 failure

    @pytest.mark.asyncio
    async def test_status_checks_before_action(self):
        """Test checking status before executing commands"""
        controller = BittleBackendController()
        tools = BittleMelleaTools(controller)

        controller.connected = False
        status = await tools.get_status()
        assert status["success"] is True
        assert status["connected"] is False

        # Even though disconnected, can set up connection
        controller.connected = True
        controller.battery_voltage = 7.2

        status = await tools.get_status()
        assert status["connected"] is True
        assert status["battery_voltage"] == 7.2

    @pytest.mark.asyncio
    async def test_low_battery_warning(self):
        """Test battery warning in status"""
        controller = BittleBackendController()
        tools = BittleMelleaTools(controller)

        controller.connected = True
        controller.battery_voltage = 5.5  # Below 6.0V threshold

        status = await tools.get_status()
        assert status["success"] is True
        assert "error" in status
        assert "Low battery" in status["error"]


class TestSystemPrompt:
    """Test system prompt generation"""

    def test_system_prompt_content(self):
        controller = BittleBackendController()
        tools = BittleMelleaTools(controller)

        prompt = tools.get_system_prompt()
        assert "Petoi Bittle" in prompt
        assert "tools" in prompt.lower()
        assert "safety" in prompt.lower() or "Safety" in prompt
        assert "sit" in prompt
        assert "-90" in prompt
        assert "+90" in prompt

    def test_system_prompt_includes_motors(self):
        controller = BittleBackendController()
        tools = BittleMelleaTools(controller)

        prompt = tools.get_system_prompt()
        assert "neck" in prompt
        assert "shoulder" in prompt
        assert "hip" in prompt

    def test_system_prompt_includes_skills(self):
        controller = BittleBackendController()
        tools = BittleMelleaTools(controller)

        prompt = tools.get_system_prompt()
        assert "sit" in prompt
        assert "stand" in prompt
        assert "walk" in prompt


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    @pytest.mark.asyncio
    async def test_empty_sequence(self):
        controller = BittleBackendController()
        tools = BittleMelleaTools(controller)

        result = await tools.sequence_motion([])
        assert result["success"] is False
        assert "empty" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_motor_at_boundaries(self):
        """Test motors at exact boundary angles"""
        controller = BittleBackendController()
        tools = BittleMelleaTools(controller)

        with patch.object(controller, "send_command", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True

            # Test minimum angle
            result = await tools.control_motor("neck", -90)
            assert result["success"] is True

            # Test maximum angle
            result = await tools.control_motor("neck", 90)
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_all_motors(self):
        """Test controlling all available motors"""
        controller = BittleBackendController()

        motors = [
            "neck", "left_shoulder", "right_shoulder", "right_hip", "left_hip",
            "left_arm", "right_arm", "right_ankle", "left_ankle"
        ]

        for motor in motors:
            valid, index, msg = controller.validate_motor_name_or_index(motor)
            assert valid is True, f"Motor {motor} should be valid"

    @pytest.mark.asyncio
    async def test_all_skills(self):
        """Test all available skills"""
        controller = BittleBackendController()

        skills = controller.get_available_skills()
        assert len(skills) >= 18  # At least the ones defined

        for skill in skills:
            assert isinstance(skill, str)
            assert len(skill) > 0


class TestLogging:
    """Test that logging works correctly"""

    @pytest.mark.asyncio
    async def test_command_logging(self):
        """Test that commands are logged"""
        controller = BittleBackendController()

        with patch.object(controller, "send_command", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            await controller.execute_skill("sit")
            assert controller.last_command == "ksit"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
