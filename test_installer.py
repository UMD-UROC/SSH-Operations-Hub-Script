#!/usr/bin/env python3
"""
Unit tests for SSH Operations Hub Installer.
"""

import unittest
from unittest.mock import patch, MagicMock, mock_open
import tempfile
import os
from pathlib import Path
import shutil
import sys

# Add the parent directory to the path to import the module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from install import SSHOperationsHubInstaller


class TestSSHOperationsHubInstaller(unittest.TestCase):
    """Test cases for SSH Operations Hub Installer."""
    
    def setUp(self):
        """Set up test fixture."""
        self.installer = SSHOperationsHubInstaller()
        # Create temporary directory for testing
        self.test_dir = Path(tempfile.mkdtemp())
        self.installer.source_script = self.test_dir / "ssh_operations_hub.py"
        
        # Create mock source script
        self.installer.source_script.write_text("#!/usr/bin/env python3\nprint('test')")
        
        # Override paths for testing
        self.installer.system_bin_dir = self.test_dir / "system_bin"
        self.installer.system_config_dir = self.test_dir / "system_config"
        self.installer.user_bin_dir = self.test_dir / "user_bin"
        self.installer.user_config_dir = self.test_dir / "user_config"
        self.installer.system_version_file = self.installer.system_config_dir / "version"
        self.installer.user_version_file = self.installer.user_config_dir / "version"

    def tearDown(self):
        """Clean up test fixture."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    @patch('os.geteuid')
    def test_check_sudo_with_root(self, mock_geteuid):
        """Test sudo check when running as root."""
        mock_geteuid.return_value = 0
        self.assertTrue(self.installer._check_sudo())

    @patch('os.geteuid')
    def test_check_sudo_without_root(self, mock_geteuid):
        """Test sudo check when not running as root."""
        mock_geteuid.return_value = 1000
        self.assertFalse(self.installer._check_sudo())

    def test_get_current_version_exists(self):
        """Test getting current version when version file exists."""
        # Create version file
        self.installer.user_config_dir.mkdir(parents=True, exist_ok=True)
        self.installer.user_version_file.write_text("1.5.0")
        
        version = self.installer._get_current_version(system_wide=False)
        self.assertEqual(version, "1.5.0")

    def test_get_current_version_not_exists(self):
        """Test getting current version when version file doesn't exist."""
        version = self.installer._get_current_version(system_wide=False)
        self.assertIsNone(version)

    def test_set_version(self):
        """Test setting version in version file."""
        self.installer._set_version(system_wide=False)
        
        self.assertTrue(self.installer.user_version_file.exists())
        version = self.installer.user_version_file.read_text().strip()
        self.assertEqual(version, self.installer.VERSION)

    def test_backup_existing(self):
        """Test backup of existing installation."""
        # Create existing file
        target = self.test_dir / "existing_file"
        target.write_text("existing content")
        
        backup_path = self.installer._backup_existing(target)
        
        self.assertIsNotNone(backup_path)
        self.assertTrue(backup_path.exists())
        self.assertEqual(backup_path.read_text(), "existing content")

    def test_backup_existing_no_file(self):
        """Test backup when no existing file."""
        target = self.test_dir / "nonexistent_file"
        backup_path = self.installer._backup_existing(target)
        self.assertIsNone(backup_path)

    def test_copy_config_files(self):
        """Test copying configuration files."""
        # Create mock config source
        config_source = self.test_dir / "config"
        config_source.mkdir()
        (config_source / "defaults.conf").write_text("IP_PREFIX=10.0.0")
        (config_source / "test.conf").write_text("TEST=value")
        
        # Mock the script directory to include config
        self.installer.script_dir = self.test_dir
        
        target_dir = self.test_dir / "target_config"
        self.installer._copy_config_files(target_dir)
        
        self.assertTrue(target_dir.exists())
        self.assertTrue((target_dir / "defaults.conf").exists())
        self.assertTrue((target_dir / "test.conf").exists())
        self.assertEqual((target_dir / "defaults.conf").read_text(), "IP_PREFIX=10.0.0")

    @patch.object(SSHOperationsHubInstaller, '_check_sudo')
    @patch.object(SSHOperationsHubInstaller, '_copy_config_files')
    def test_install_user_mode_success(self, mock_copy_config, mock_check_sudo):
        """Test successful user mode installation."""
        mock_check_sudo.return_value = False  # Not running as sudo
        
        result = self.installer.install(system_wide=False)
        
        self.assertTrue(result)
        self.assertTrue(self.installer.user_bin_dir.exists())
        self.assertTrue((self.installer.user_bin_dir / self.installer.SCRIPT_NAME).exists())
        self.assertTrue(self.installer.user_version_file.exists())
        mock_copy_config.assert_called_once()

    @patch.object(SSHOperationsHubInstaller, '_check_sudo')
    def test_install_system_mode_no_sudo(self, mock_check_sudo):
        """Test system mode installation without sudo."""
        mock_check_sudo.return_value = False
        
        result = self.installer.install(system_wide=True)
        
        self.assertFalse(result)

    @patch.object(SSHOperationsHubInstaller, '_check_sudo')
    @patch.object(SSHOperationsHubInstaller, '_get_current_version')
    def test_install_already_installed(self, mock_get_version, mock_check_sudo):
        """Test installation when already installed."""
        mock_check_sudo.return_value = False
        mock_get_version.return_value = "2.0.0"
        
        result = self.installer.install(system_wide=False, force=False)
        
        self.assertFalse(result)

    @patch.object(SSHOperationsHubInstaller, '_check_sudo')
    @patch.object(SSHOperationsHubInstaller, '_get_current_version')
    def test_install_force_reinstall(self, mock_get_version, mock_check_sudo):
        """Test force reinstallation."""
        mock_check_sudo.return_value = False
        mock_get_version.return_value = "1.0.0"
        
        result = self.installer.install(system_wide=False, force=True)
        
        self.assertTrue(result)

    def test_install_source_not_exists(self):
        """Test installation when source script doesn't exist."""
        self.installer.source_script = Path("/nonexistent/script.py")
        
        result = self.installer.install(system_wide=False)
        
        self.assertFalse(result)

    @patch.object(SSHOperationsHubInstaller, '_get_current_version')
    @patch.object(SSHOperationsHubInstaller, 'install')
    def test_update_existing_installation(self, mock_install, mock_get_version):
        """Test updating existing installation."""
        mock_get_version.return_value = "1.0.0"
        mock_install.return_value = True
        
        result = self.installer.update(system_wide=False)
        
        self.assertTrue(result)
        mock_install.assert_called_once_with(False, force=True)

    @patch.object(SSHOperationsHubInstaller, '_get_current_version')
    def test_update_no_installation(self, mock_get_version):
        """Test update when no existing installation."""
        mock_get_version.return_value = None
        
        result = self.installer.update(system_wide=False)
        
        self.assertFalse(result)

    @patch.object(SSHOperationsHubInstaller, '_get_current_version')
    def test_update_already_current(self, mock_get_version):
        """Test update when already current version."""
        mock_get_version.return_value = self.installer.VERSION
        
        result = self.installer.update(system_wide=False)
        
        self.assertTrue(result)  # Should return True for "no update needed"

    @patch.object(SSHOperationsHubInstaller, '_check_sudo')
    @patch.object(SSHOperationsHubInstaller, '_get_current_version')
    @patch('builtins.input')
    def test_uninstall_success(self, mock_input, mock_get_version, mock_check_sudo):
        """Test successful uninstallation."""
        mock_check_sudo.return_value = False
        mock_get_version.return_value = "2.0.0"
        mock_input.return_value = "y"
        
        # Create files to uninstall
        self.installer.user_bin_dir.mkdir(parents=True, exist_ok=True)
        script_path = self.installer.user_bin_dir / self.installer.SCRIPT_NAME
        script_path.write_text("#!/bin/bash\necho test")
        self.installer.user_config_dir.mkdir(parents=True, exist_ok=True)
        (self.installer.user_config_dir / "test.conf").write_text("test")
        
        result = self.installer.uninstall(system_wide=False)
        
        self.assertTrue(result)
        self.assertFalse(script_path.exists())

    @patch.object(SSHOperationsHubInstaller, '_check_sudo')
    def test_uninstall_system_no_sudo(self, mock_check_sudo):
        """Test system uninstallation without sudo."""
        mock_check_sudo.return_value = False
        
        result = self.installer.uninstall(system_wide=True)
        
        self.assertFalse(result)

    @patch.object(SSHOperationsHubInstaller, '_get_current_version')
    def test_uninstall_no_installation(self, mock_get_version):
        """Test uninstallation when no installation exists."""
        mock_get_version.return_value = None
        
        result = self.installer.uninstall(system_wide=False)
        
        self.assertFalse(result)

    @patch.object(SSHOperationsHubInstaller, '_get_current_version')
    def test_status(self, mock_get_version):
        """Test status display."""
        mock_get_version.side_effect = ["1.0.0", "2.0.0"]  # system, then user
        
        # This should not raise any exceptions
        self.installer.status()
        
        # Verify both version checks were called
        self.assertEqual(mock_get_version.call_count, 2)


class TestInstallerIntegration(unittest.TestCase):
    """Integration tests for the installer."""
    
    def setUp(self):
        """Set up integration test environment."""
        self.test_dir = Path(tempfile.mkdtemp())
        
    def tearDown(self):
        """Clean up integration test environment."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_full_install_uninstall_cycle(self):
        """Test complete install/uninstall cycle in user mode."""
        installer = SSHOperationsHubInstaller()
        
        # Override paths for testing
        installer.user_bin_dir = self.test_dir / "bin"
        installer.user_config_dir = self.test_dir / "config"
        installer.user_version_file = installer.user_config_dir / "version"
        
        # Create mock source script
        installer.source_script = self.test_dir / "ssh_operations_hub.py"
        installer.source_script.write_text("#!/usr/bin/env python3\nprint('test')")
        
        # Test install
        result = installer.install(system_wide=False)
        self.assertTrue(result)
        
        # Verify installation
        script_path = installer.user_bin_dir / installer.SCRIPT_NAME
        self.assertTrue(script_path.exists())
        self.assertTrue(installer.user_version_file.exists())
        
        # Test status
        version = installer._get_current_version(system_wide=False)
        self.assertEqual(version, installer.VERSION)
        
        # Test uninstall
        with patch('builtins.input', return_value='n'):  # Don't remove config
            result = installer.uninstall(system_wide=False)
        self.assertTrue(result)
        
        # Verify uninstallation
        self.assertFalse(script_path.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)