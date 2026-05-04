"""
Systemd Integration Tests for myAudible

This module provides tests for the systemd integration setup.
Since this is a test environment (not a systemd system), these tests
verify that the required files exist and have valid syntax/structure.

Run with: pytest tests/test_systemd_integration.py
"""

import pytest
from pathlib import Path


class TestSystemdIntegration:
    """Test class for systemd integration setup verification."""

    # File paths to test
    PATH_FILE = Path("plans/systemd/myaudible-input.path")
    SERVICE_FILE = Path("plans/systemd/myaudible.service")
    INSTALL_SCRIPT = Path("plans/install.sh")
    ENV_TEMPLATE = Path("plans/.env.example")

    # Required sections for systemd unit files
    PATH_REQUIRED_SECTIONS = {"[Unit]", "[Path]", "[Install]"}
    SERVICE_REQUIRED_SECTIONS = {"[Unit]", "[Service]", "[Install]"}

    # Service unit requirements
    SERVICE_REQUIRED_KEYS = {"ExecStart", "Type", "Restart"}

    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Set up test environment for each test."""
        # Ensure we're working with absolute paths
        self.PATH_FILE = Path.cwd() / self.PATH_FILE
        self.SERVICE_FILE = Path.cwd() / self.SERVICE_FILE
        self.INSTALL_SCRIPT = Path.cwd() / self.INSTALL_SCRIPT
        self.ENV_TEMPLATE = Path.cwd() / self.ENV_TEMPLATE
        yield
        # Cleanup if needed

    def test_required_files_exist(self):
        """Test that all required systemd integration files exist."""
        # Check that all required files exist
        assert self.PATH_FILE.exists(), f"Path file not found: {self.PATH_FILE}"
        assert self.SERVICE_FILE.exists(), f"Service file not found: {self.SERVICE_FILE}"
        assert self.INSTALL_SCRIPT.exists(), f"Install script not found: {self.INSTALL_SCRIPT}"
        assert self.ENV_TEMPLATE.exists(), f"Environment template not found: {self.ENV_TEMPLATE}"

    def test_path_unit_has_required_sections(self):
        """Test that the path unit has required sections: [Unit], [Path], [Install]."""
        content = self.PATH_FILE.read_text()

        # Check for required sections
        for section in self.PATH_REQUIRED_SECTIONS:
            assert section in content, f"Missing required section: {section}"

    def test_service_unit_has_required_sections(self):
        """Test that the service unit has required sections: [Unit], [Service], [Install]."""
        content = self.SERVICE_FILE.read_text()

        # Check for required sections
        for section in self.SERVICE_REQUIRED_SECTIONS:
            assert section in content, f"Missing required section: {section}"

    def test_service_unit_has_required_settings(self):
        """Test that the service unit specifies ExecStart, Type, Restart settings."""
        content = self.SERVICE_FILE.read_text()

        # Check for required settings
        for setting in self.SERVICE_REQUIRED_KEYS:
            assert setting in content, f"Missing required setting: {setting}"

    def test_install_script_has_shebang(self):
        """Test that the installation script has a proper shebang."""
        content = self.INSTALL_SCRIPT.read_text()
        assert content.startswith("#!/bin/bash"), "Install script missing proper shebang"

    def test_install_script_references_key_directories(self):
        """Test that the installation script contains references to key directories."""
        content = self.INSTALL_SCRIPT.read_text()

        # Check for references to key directories
        assert "INPUT_DIR" in content or "input" in content.lower(), \
            "Install script should reference input directory"
        assert "OUTPUT_DIR" in content or "output" in content.lower(), \
            "Install script should reference output directory"
        assert "PROCESSED_DIR" in content or "processed" in content.lower(), \
            "Install script should reference processed directory"

    def test_install_script_references_systemd(self):
        """Test that the installation script contains references to systemd service management."""
        content = self.INSTALL_SCRIPT.read_text()

        # Check for systemd-related operations
        assert "systemctl" in content, "Install script should reference systemctl"
        assert "systemd" in content.lower(), \
            "Install script should reference systemd"

    def test_env_template_has_required_variables(self):
        """Test that the environment template contains all required variables."""
        content = self.ENV_TEMPLATE.read_text()

        # Required variables from the template
        required_variables = [
            "TTS_API_ENDPOINT",
            "TTS_API_KEY",
            "INPUT_DIR",
            "OUTPUT_DIR",
            "LOG_LEVEL",
        ]

        for var in required_variables:
            assert var in content, f"Missing required variable: {var}"

    def test_env_template_has_proper_format(self):
        """Test that the environment template has proper key=value format."""
        content = self.ENV_TEMPLATE.read_text()

        # Check that variables are in proper key=value format (excluding comments)
        lines = content.split("\n")
        for line in lines:
            # Skip comment lines and empty lines
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                # Non-comment lines should either be key=value or start with #
                # We're checking that variable assignments use = sign
                if "=" in stripped and not stripped.startswith("#"):
                    # This is a variable assignment line
                    key, _, _ = stripped.partition("=")
                    assert key.strip(), "Environment variable should not have empty key"
