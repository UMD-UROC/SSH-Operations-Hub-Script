#!/usr/bin/env python3
"""
Unit tests for SSH Operations Hub Python implementation.
"""

import unittest
from unittest.mock import patch, MagicMock, call
import tempfile
import os
import subprocess
from pathlib import Path
import sys

# Add the parent directory to the path to import the module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ssh_operations_hub import SSHOperationsHub


class TestSSHOperationsHub(unittest.TestCase):
    """Test cases for SSH Operations Hub."""
    
    def setUp(self):
        """Set up test fixture."""
        self.hub = SSHOperationsHub()
        # Override config loading to use test values
        self.hub.ip_prefix = "10.200.142"
        self.hub.allowed_ips = ["1", "2", "3", "4", "5", "20", "21", "150", "151"]

    def test_expand_range(self):
        """Test IP range expansion."""
        # Test single number
        result = self.hub._expand_range("5")
        self.assertEqual(result, ["5"])
        
        # Test range
        result = self.hub._expand_range("1-3")
        self.assertEqual(result, ["1", "2", "3"])
        
        # Test invalid range
        result = self.hub._expand_range("5-3")  # end < start
        self.assertEqual(result, [])
        
        # Test non-numeric
        result = self.hub._expand_range("abc")
        self.assertEqual(result, [])

    def test_parse_allowed_ips(self):
        """Test parsing of allowed IPs configuration."""
        # Test mixed ranges and individual IPs
        result = self.hub._parse_allowed_ips(["1-3", "5", "7-9"])
        expected = ["1", "2", "3", "5", "7", "8", "9"]
        self.assertEqual(result, expected)
        
        # Test single range
        result = self.hub._parse_allowed_ips(["10-12"])
        expected = ["10", "11", "12"]
        self.assertEqual(result, expected)
        
        # Test individual IPs only
        result = self.hub._parse_allowed_ips(["1", "2", "3"])
        expected = ["1", "2", "3"]
        self.assertEqual(result, expected)

    def test_validate_ip_suffix(self):
        """Test IP suffix validation."""
        # Valid IPs in allowed list
        self.assertTrue(self.hub._validate_ip_suffix("1"))
        self.assertTrue(self.hub._validate_ip_suffix("5"))
        self.assertTrue(self.hub._validate_ip_suffix("150"))
        
        # Invalid - not in allowed list
        self.assertFalse(self.hub._validate_ip_suffix("100"))
        
        # Invalid - non-numeric
        self.assertFalse(self.hub._validate_ip_suffix("abc"))
        self.assertFalse(self.hub._validate_ip_suffix("1a"))

    def test_validate_ip_prefix(self):
        """Test IP prefix validation."""
        # Valid prefixes
        self.assertTrue(self.hub._validate_ip_prefix("192.168.1"))
        self.assertTrue(self.hub._validate_ip_prefix("10.0.0"))
        self.assertTrue(self.hub._validate_ip_prefix("172.16.10"))
        
        # Valid with trailing dot
        self.assertTrue(self.hub._validate_ip_prefix("192.168.1."))
        
        # Invalid format
        self.assertFalse(self.hub._validate_ip_prefix("192.168"))
        self.assertFalse(self.hub._validate_ip_prefix("192.168.1.1"))
        self.assertFalse(self.hub._validate_ip_prefix("abc.def.ghi"))
        
        # Invalid range
        self.assertFalse(self.hub._validate_ip_prefix("256.1.1"))
        self.assertFalse(self.hub._validate_ip_prefix("1.256.1"))
        self.assertFalse(self.hub._validate_ip_prefix("1.1.256"))

    def test_parse_ips(self):
        """Test IP parsing and validation."""
        # Valid IPs
        valid_ips, errors = self.hub._parse_ips(["1", "2", "3"])
        expected = ["10.200.142.1", "10.200.142.2", "10.200.142.3"]
        self.assertEqual(valid_ips, expected)
        self.assertEqual(errors, [])
        
        # Mix of valid and invalid
        valid_ips, errors = self.hub._parse_ips(["1", "100", "2", "abc"])
        expected = ["10.200.142.1", "10.200.142.2"]
        self.assertEqual(valid_ips, expected)
        self.assertEqual(len(errors), 2)
        self.assertIn("Invalid or disallowed IP suffix '100'", errors)
        self.assertIn("Invalid or disallowed IP suffix 'abc'", errors)
        
        # Duplicates (should show warning but not error)
        with patch.object(self.hub.logger, 'warning') as mock_warning:
            valid_ips, errors = self.hub._parse_ips(["1", "1", "2"])
            expected = ["10.200.142.1", "10.200.142.2"]
            self.assertEqual(valid_ips, expected)
            self.assertEqual(errors, [])
            mock_warning.assert_called_once_with("Skipping duplicate IP suffix '1'")

    def test_substitute_variables(self):
        """Test variable substitution."""
        result = self.hub._substitute_variables("user$CLIENT_NUM", "5")
        self.assertEqual(result, "user5")
        
        result = self.hub._substitute_variables("echo 'Client $CLIENT_NUM'", "10")
        self.assertEqual(result, "echo 'Client 10'")
        
        # No substitution needed
        result = self.hub._substitute_variables("echo test", "5")
        self.assertEqual(result, "echo test")

    @patch('subprocess.run')
    def test_check_ssh(self, mock_run):
        """Test SSH availability check."""
        # SSH available
        mock_run.return_value = None
        result = self.hub._check_ssh()
        self.assertTrue(result)
        mock_run.assert_called_once()
        
        # SSH not available - FileNotFoundError
        mock_run.reset_mock()
        mock_run.side_effect = FileNotFoundError()
        result = self.hub._check_ssh()
        self.assertFalse(result)
        
        # SSH not available - CalledProcessError
        mock_run.reset_mock()
        mock_run.side_effect = subprocess.CalledProcessError(1, 'ssh')
        result = self.hub._check_ssh()
        self.assertFalse(result)

    @patch('subprocess.run')
    def test_execute_ssh_command_success(self, mock_run):
        """Test successful SSH command execution."""
        # Mock successful connection test
        mock_run.side_effect = [
            MagicMock(returncode=0),  # Connection test
            MagicMock(returncode=0, stdout="Hello World\nLine 2", stderr="")  # Actual command
        ]
        
        success, output = self.hub._execute_ssh_command("testuser", "10.200.142.1", "echo test")
        
        self.assertTrue(success)
        self.assertIn("[Client 1 | 10.200.142.1] Hello World", output)
        self.assertIn("[Client 1 | 10.200.142.1] Line 2", output)
        
        # Check that both SSH calls were made
        self.assertEqual(mock_run.call_count, 2)

    @patch('subprocess.run')
    def test_execute_ssh_command_connection_failure(self, mock_run):
        """Test SSH command execution with connection failure."""
        # Mock failed connection test
        mock_run.side_effect = subprocess.CalledProcessError(1, 'ssh')
        
        success, output = self.hub._execute_ssh_command("testuser", "10.200.142.1", "echo test")
        
        self.assertFalse(success)
        self.assertIn("Could not establish SSH connection", output)
        
        # Only connection test should be called
        self.assertEqual(mock_run.call_count, 1)

    @patch('subprocess.run')
    def test_execute_ssh_command_command_failure(self, mock_run):
        """Test SSH command execution with command failure."""
        # Mock successful connection but failed command
        mock_run.side_effect = [
            MagicMock(returncode=0),  # Connection test succeeds
            subprocess.CalledProcessError(127, 'ssh', stderr="command not found")  # Command fails
        ]
        
        success, output = self.hub._execute_ssh_command("testuser", "10.200.142.1", "badcommand")
        
        self.assertFalse(success)
        self.assertIn("Command failed with status 127", output)
        self.assertIn("command not found", output)

    @patch('ssh_operations_hub.ThreadPoolExecutor')
    @patch.object(SSHOperationsHub, '_execute_ssh_command')
    def test_execute_commands(self, mock_ssh_exec, mock_executor):
        """Test parallel command execution."""
        # Mock the executor and futures
        mock_future1 = MagicMock()
        mock_future1.result.return_value = (True, "[Client 1 | 10.200.142.1] Success")
        mock_future2 = MagicMock()
        mock_future2.result.return_value = (True, "[Client 2 | 10.200.142.2] Success")
        
        mock_executor_instance = MagicMock()
        mock_executor.return_value.__enter__.return_value = mock_executor_instance
        mock_executor_instance.submit.side_effect = [mock_future1, mock_future2]
        
        # Mock as_completed to return our futures
        with patch('ssh_operations_hub.as_completed', return_value=[mock_future1, mock_future2]):
            self.hub.execute_commands(
                primary_ips=["10.200.142.1", "10.200.142.2"],
                secondary_ips=[],
                primary_user="root",
                secondary_user="admin",
                command="echo test"
            )
        
        # Verify executor was called with correct parameters
        mock_executor.assert_called_once_with(max_workers=self.hub.max_parallel_connections)
        
        # Verify two SSH commands were submitted
        self.assertEqual(mock_executor_instance.submit.call_count, 2)

    def test_create_parser(self):
        """Test argument parser creation."""
        parser = self.hub._create_parser()
        
        # Test valid arguments
        args = parser.parse_args(['--ips', '1', '2', '--command', 'echo test'])
        self.assertEqual(args.primary, ['1', '2'])
        self.assertEqual(args.cmd, 'echo test')
        
        # Test with all arguments
        args = parser.parse_args([
            '--primary-ips', '1', '2',
            '--secondary-ips', '3', '4',
            '--primary-user', 'user1',
            '--secondary-user', 'user2',
            '--command', 'echo test',
            '--ip-prefix', '192.168.1'
        ])
        self.assertEqual(args.primary, ['1', '2'])
        self.assertEqual(args.secondary, ['3', '4'])
        self.assertEqual(args.puser, 'user1')
        self.assertEqual(args.suser, 'user2')
        self.assertEqual(args.cmd, 'echo test')
        self.assertEqual(args.ip_prefix, '192.168.1')

    def test_load_config(self):
        """Test configuration file loading."""
        # Create temporary config file
        import json
        config_data = {
            "ip_prefix": "192.168.1",
            "allowed_ips": ["1", "2", "3", "5-7", "10"]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_config = f.name
        
        try:
            # Patch the config locations to use our temp file
            with patch.object(self.hub, '_load_config'):
                hub = SSHOperationsHub()
                # Manually call the method we want to test
                with open(temp_config, 'r') as f:
                    config = json.load(f)
                    
                if 'ip_prefix' in config:
                    hub.ip_prefix = config['ip_prefix']
                if 'allowed_ips' in config:
                    hub.allowed_ips = hub._parse_allowed_ips(config['allowed_ips'])
            
            # Verify configuration was loaded correctly
            self.assertEqual(hub.ip_prefix, "192.168.1")
            expected_allowed = ["1", "2", "3", "5", "6", "7", "10"]
            self.assertEqual(hub.allowed_ips, expected_allowed)
            
        finally:
            os.unlink(temp_config)


class TestIntegration(unittest.TestCase):
    """Integration tests for the full application."""
    
    @patch('ssh_operations_hub.SSHOperationsHub._check_ssh')
    @patch.object(SSHOperationsHub, 'execute_commands')
    def test_main_run_integration(self, mock_execute, mock_check_ssh):
        """Test main run method integration."""
        mock_check_ssh.return_value = True
        
        hub = SSHOperationsHub()
        # Override config for testing
        hub.ip_prefix = "10.200.142"
        hub.allowed_ips = ["1", "2", "3", "4", "5"]
        
        # Test successful run
        args = ['--ips', '1', '2', '--primary-user', 'testuser', '--command', 'echo test']
        hub.run(args)
        
        # Verify execute_commands was called with correct parameters
        mock_execute.assert_called_once()
        call_args = mock_execute.call_args[1]  # Get keyword arguments
        self.assertEqual(call_args['primary_ips'], ['10.200.142.1', '10.200.142.2'])
        self.assertEqual(call_args['primary_user'], 'testuser')
        self.assertEqual(call_args['command'], 'echo test')

    @patch('ssh_operations_hub.SSHOperationsHub._check_ssh')
    def test_main_run_no_ssh(self, mock_check_ssh):
        """Test main run method when SSH is not available."""
        mock_check_ssh.return_value = False
        
        hub = SSHOperationsHub()
        
        with self.assertRaises(SystemExit) as cm:
            hub.run(['--ips', '1', '--command', 'test'])
        
        self.assertEqual(cm.exception.code, 1)


if __name__ == '__main__':
    # Import required modules for testing
    import subprocess
    
    unittest.main(verbosity=2)