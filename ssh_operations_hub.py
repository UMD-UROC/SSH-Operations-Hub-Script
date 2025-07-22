#!/usr/bin/env python3
"""
SSH Operations Hub

TECHNICAL DETAILS:
- Uses concurrent.futures for parallel SSH execution
- Implements proper signal handling for clean termination
- Handles SSH connections with enhanced security options
- Supports configuration via config files

SECURITY FEATURES:
- IP validation against whitelist
- Strict SSH options (StrictHostKeyChecking, BatchMode)
- Protected configuration files
- Sanitized command handling

CONFIGURATION FILES:
1. User config: $HOME/.config/ssh-operations-hub/defaults.conf
2. System config: /etc/ssh-operations-hub/defaults.conf

For complete documentation:
https://umd-uroc.github.io/docs/SSH Operations Hub
"""

import argparse
import configparser
import logging
import os
import re
import signal
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Set, Tuple, Optional


class SSHOperationsHub:
    """Main class for SSH Operations Hub functionality."""
    
    def __init__(self):
        self.default_ip_prefix = "10.200.142"
        self.ip_prefix = self.default_ip_prefix
        self.allowed_ips = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", 
                           "15", "17", "20", "21", "22", "23", "24", "25"]
        self.max_parallel_connections = 10
        self.ssh_options = [
            "-o", "BatchMode=yes",
            "-o", "ConnectTimeout=5",
            "-o", "StrictHostKeyChecking=accept-new",
            "-o", "ControlMaster=no"
        ]
        self.global_timeout = 3600  # 1 hour
        self.connection_timeout = 10
        self.shutdown_event = threading.Event()
        
        # Set up signal handling
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        self._load_config()

    def _signal_handler(self, signum, frame):
        """Handle SIGINT and SIGTERM for clean shutdown."""
        self.logger.info("Interrupted! Stopping all SSH connections...")
        self.shutdown_event.set()
        sys.exit(1)

    def _load_config(self):
        """Load configuration from available config files."""
        config_locations = [
            Path.home() / ".config" / "ssh-operations-hub" / "defaults.conf",
            Path(__file__).parent / "config" / "defaults.conf",
            Path("/etc/ssh-operations-hub/defaults.conf")
        ]
        
        for config_file in config_locations:
            if config_file.exists():
                try:
                    # Handle simple bash-style config format
                    with open(config_file, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#'):
                                if '=' in line:
                                    key, value = line.split('=', 1)
                                    key = key.strip()
                                    value = value.strip().strip('"')
                                    
                                    if key == 'IP_PREFIX':
                                        self.ip_prefix = value
                                    elif key == 'ALLOWED_IPS':
                                        self.allowed_ips = self._parse_allowed_ips(value)
                    break
                except Exception as e:
                    self.logger.warning(f"Failed to load config from {config_file}: {e}")

    def _parse_allowed_ips(self, allowed_ips_str: str) -> List[str]:
        """Parse ALLOWED_IPS configuration string into list of IP suffixes."""
        allowed = []
        ranges = allowed_ips_str.split()
        
        for range_str in ranges:
            allowed.extend(self._expand_range(range_str))
        
        return allowed

    def _expand_range(self, range_str: str) -> List[str]:
        """Expand IP range string into individual IP suffixes."""
        if '-' in range_str:
            try:
                start, end = range_str.split('-', 1)
                start_num, end_num = int(start), int(end)
                if start_num <= end_num:
                    return [str(i) for i in range(start_num, end_num + 1)]
            except ValueError:
                pass
        
        return [range_str] if range_str.isdigit() else []

    def _validate_ip_suffix(self, ip_suffix: str) -> bool:
        """Validate IP suffix against allowed list."""
        return ip_suffix.isdigit() and ip_suffix in self.allowed_ips

    def _validate_ip_prefix(self, prefix: str) -> bool:
        """Validate IP prefix format and range."""
        # Remove trailing dot if present
        prefix = prefix.rstrip('.')
        
        # Check format: X.X.X where X is 1-3 digits
        if not re.match(r'^(\d{1,3}\.){2}\d{1,3}$', prefix):
            return False
        
        # Validate each octet is in range 0-255
        octets = prefix.split('.')
        return all(0 <= int(octet) <= 255 for octet in octets)

    def _parse_ips(self, ip_suffixes: List[str]) -> Tuple[List[str], List[str]]:
        """Parse and validate IP suffixes, return (valid_ips, errors)."""
        valid_ips = []
        errors = []
        seen = set()
        
        for ip_suffix in ip_suffixes:
            if not self._validate_ip_suffix(ip_suffix):
                errors.append(f"Invalid or disallowed IP suffix '{ip_suffix}'")
                continue
            
            if ip_suffix in seen:
                self.logger.warning(f"Skipping duplicate IP suffix '{ip_suffix}'")
                continue
            
            seen.add(ip_suffix)
            valid_ips.append(f"{self.ip_prefix}.{ip_suffix}")
        
        return valid_ips, errors

    def _check_ssh(self) -> bool:
        """Verify SSH client availability."""
        try:
            subprocess.run(['ssh', '-V'], stdout=subprocess.DEVNULL, 
                          stderr=subprocess.DEVNULL, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _execute_ssh_command(self, user: str, ip: str, command: str) -> Tuple[bool, str]:
        """Execute a single SSH command with proper error handling."""
        client_num = ip.split('.')[-1]
        label = f"[Client {client_num} | {ip}]"
        
        if self.shutdown_event.is_set():
            return False, f"{label} Aborted due to shutdown"
        
        # Test SSH connection first
        test_cmd = ['ssh'] + self.ssh_options + [f'{user}@{ip}', 'exit', '0']
        try:
            result = subprocess.run(
                test_cmd, 
                timeout=self.connection_timeout,
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL,
                check=True
            )
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            return False, f"{label} Error: Could not establish SSH connection to {user}@{ip}"
        
        # Execute the actual command
        self.logger.info(f"{label} Running '{command}' on {user}@{ip}")
        
        actual_cmd = ['ssh'] + self.ssh_options + [f'{user}@{ip}', command]
        try:
            result = subprocess.run(
                actual_cmd,
                timeout=self.connection_timeout,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Format output with label prefix
            output_lines = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    output_lines.append(f"{label} {line}")
            
            return True, '\n'.join(output_lines)
            
        except subprocess.TimeoutExpired:
            return False, f"{label} Error: Command timed out"
        except subprocess.CalledProcessError as e:
            error_output = e.stderr.strip() if e.stderr else "Unknown error"
            return False, f"{label} Error: Command failed with status {e.returncode}\n{label} Output: {error_output}"

    def _substitute_variables(self, text: str, client_num: str) -> str:
        """Substitute $CLIENT_NUM variables in text."""
        return text.replace('$CLIENT_NUM', client_num)

    def execute_commands(self, primary_ips: List[str], secondary_ips: List[str], 
                        primary_user: str, secondary_user: str, command: str):
        """Execute commands on all specified IPs with parallel processing."""
        if not primary_ips and not secondary_ips:
            self.logger.warning("No IP addresses specified")
            return
        
        if not command:
            self.logger.warning("No command specified")
            return
        
        # Prepare task list
        tasks = []
        
        # Add primary tasks
        for ip in primary_ips:
            client_num = ip.split('.')[-1]
            user = self._substitute_variables(primary_user, client_num)
            cmd = self._substitute_variables(command, client_num)
            tasks.append((user, ip, cmd))
        
        # Add secondary tasks
        for ip in secondary_ips:
            client_num = ip.split('.')[-1]
            user = self._substitute_variables(secondary_user, client_num)
            cmd = self._substitute_variables(command, client_num)
            tasks.append((user, ip, cmd))
        
        # Execute tasks in parallel
        with ThreadPoolExecutor(max_workers=self.max_parallel_connections) as executor:
            # Submit all tasks
            future_to_task = {
                executor.submit(self._execute_ssh_command, user, ip, cmd): (user, ip, cmd)
                for user, ip, cmd in tasks
            }
            
            # Process results as they complete
            for future in as_completed(future_to_task, timeout=self.global_timeout):
                if self.shutdown_event.is_set():
                    break
                
                try:
                    success, output = future.result(timeout=1)
                    if output:
                        self.logger.info(output)
                except Exception as e:
                    user, ip, cmd = future_to_task[future]
                    client_num = ip.split('.')[-1]
                    label = f"[Client {client_num} | {ip}]"
                    self.logger.error(f"{label} Unexpected error: {e}")

    def run(self, args):
        """Main execution method."""
        # Check SSH availability
        if not self._check_ssh():
            self.logger.error("Error: SSH client is not installed")
            sys.exit(1)
        
        # Parse arguments
        parser = self._create_parser()
        parsed_args = parser.parse_args(args)
        
        # Process IP prefix if provided
        if parsed_args.ip_prefix:
            prefix = parsed_args.ip_prefix.rstrip('.')
            if not self._validate_ip_prefix(prefix):
                self.logger.error("Error: Invalid IP prefix format. Use format: XXX.XXX.XXX (0-255)")
                sys.exit(1)
            self.ip_prefix = prefix
        
        # Process primary IPs
        primary_ips = []
        if parsed_args.primary:
            valid_ips, errors = self._parse_ips(parsed_args.primary)
            for error in errors:
                self.logger.error(f"Error: {error}")
            primary_ips = valid_ips
        
        # Process secondary IPs
        secondary_ips = []
        if parsed_args.secondary:
            valid_ips, errors = self._parse_ips(parsed_args.secondary)
            for error in errors:
                self.logger.error(f"Error: {error}")
            secondary_ips = valid_ips
        
        # Validate inputs
        if not primary_ips and not secondary_ips:
            self.logger.error("Error: No valid IP addresses found")
            sys.exit(1)
        
        if not parsed_args.cmd:
            self.logger.error("Error: No command specified")
            sys.exit(1)
        
        # Execute commands
        self.execute_commands(
            primary_ips=primary_ips,
            secondary_ips=secondary_ips,
            primary_user=parsed_args.puser,
            secondary_user=parsed_args.suser,
            command=parsed_args.cmd
        )

    def _create_parser(self) -> argparse.ArgumentParser:
        """Create argument parser with all supported options."""
        parser = argparse.ArgumentParser(
            description="SSH Operations Hub - Execute commands on multiple servers via SSH",
            epilog="For more information, see the documentation at https://umd-uroc.github.io/docs/SSH Operations Hub"
        )
        
        # Primary/IP arguments (mutually exclusive names)
        primary_group = parser.add_mutually_exclusive_group()
        primary_group.add_argument(
            '-primary', '--primary',
            nargs='+',
            metavar='IP_SUFFIX',
            help='List of IP suffixes for primary group'
        )
        primary_group.add_argument(
            '-ip', '--ip',
            nargs='+',
            metavar='IP_SUFFIX',
            dest='primary',  # Same destination as -primary
            help='List of IP suffixes (alias for -primary)'
        )
        
        # Secondary IPs
        parser.add_argument(
            '-secondary', '--secondary',
            nargs='+',
            metavar='IP_SUFFIX',
            help='List of IP suffixes for secondary group'
        )
        
        # User arguments
        parser.add_argument(
            '-puser', '-user', '--puser', '--user',
            default='root',
            dest='puser',
            metavar='USERNAME',
            help='Username for primary group (default: root)'
        )
        parser.add_argument(
            '-suser', '--suser',
            default='admin',
            metavar='USERNAME',
            help='Username for secondary group (default: admin)'
        )
        
        # Command and IP prefix
        parser.add_argument(
            '-cmd', '--cmd',
            required=True,
            metavar='COMMAND',
            help='Command to execute on all clients'
        )
        parser.add_argument(
            '-ip-prefix', '--ip-prefix',
            metavar='PREFIX',
            help='Custom IP prefix (e.g., 192.168.1)'
        )
        
        return parser


def main():
    """Main entry point."""
    if len(sys.argv) == 1:
        print("Error: No arguments provided")
        print(f"Usage: {sys.argv[0]} [-primary|-ip ip_list] [-ip-prefix 192.168.1] [-puser|-user username] [-secondary ip_list] [-suser username] [-cmd command]")
        print("To change Allowed IPs, modify the variable in the config file")
        print("For more information, see the documentation at https://umd-uroc.github.io/docs/SSH Operations Hub")
        sys.exit(1)
    
    hub = SSHOperationsHub()
    hub.run(sys.argv[1:])


if __name__ == "__main__":
    main()