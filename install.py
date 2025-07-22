#!/usr/bin/env python3
"""
Enhanced SSH Operations Hub Installer

INSTALLATION MODES:
1. System-wide installation (requires sudo) - installs to /usr/local/bin
2. User installation (no sudo required) - installs to ~/.local/bin

FEATURES:
- Install, update, and uninstall capabilities
- Version checking and management
- Configurable installation locations
- Backup of existing installations
- Proper cleanup on uninstall

For complete documentation:
https://umd-uroc.github.io/docs/SSH Operations Hub
"""

import argparse
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple


class SSHOperationsHubInstaller:
    """Enhanced installer for SSH Operations Hub."""
    
    VERSION = "2.0.0"
    SCRIPT_NAME = "ssh-operations-hub"
    PYTHON_SCRIPT = "ssh_operations_hub.py"
    
    def __init__(self):
        self.script_dir = Path(__file__).parent
        self.source_script = self.script_dir / self.PYTHON_SCRIPT
        
        # Installation paths
        self.system_bin_dir = Path("/usr/local/bin")
        self.system_config_dir = Path("/etc/ssh-operations-hub")
        self.user_bin_dir = Path.home() / ".local/bin"
        self.user_config_dir = Path.home() / ".config/ssh-operations-hub"
        
        # Version tracking
        self.system_version_file = self.system_config_dir / "version"
        self.user_version_file = self.user_config_dir / "version"

    def _check_sudo(self) -> bool:
        """Check if running with sudo privileges."""
        return os.geteuid() == 0

    def _get_current_version(self, system_wide: bool = True) -> Optional[str]:
        """Get currently installed version."""
        version_file = self.system_version_file if system_wide else self.user_version_file
        try:
            if version_file.exists():
                return version_file.read_text().strip()
        except Exception:
            pass
        return None

    def _set_version(self, system_wide: bool = True):
        """Set version in the appropriate version file."""
        version_file = self.system_version_file if system_wide else self.user_version_file
        version_file.parent.mkdir(parents=True, exist_ok=True)
        version_file.write_text(self.VERSION)

    def _create_executable(self, install_path: Path, system_wide: bool = True):
        """Create executable wrapper script."""
        wrapper_content = f'''#!/bin/bash
# SSH Operations Hub wrapper script
# Version: {self.VERSION}
# Installation type: {"System-wide" if system_wide else "User"}

SCRIPT_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
PYTHON_SCRIPT="{self.source_script}"

# Try to find the Python script in various locations
if [ -f "$PYTHON_SCRIPT" ]; then
    exec python3 "$PYTHON_SCRIPT" "$@"
elif [ -f "$SCRIPT_DIR/{self.PYTHON_SCRIPT}" ]; then
    exec python3 "$SCRIPT_DIR/{self.PYTHON_SCRIPT}" "$@"
elif [ -f "$SCRIPT_DIR/../lib/ssh-operations-hub/{self.PYTHON_SCRIPT}" ]; then
    exec python3 "$SCRIPT_DIR/../lib/ssh-operations-hub/{self.PYTHON_SCRIPT}" "$@"
else
    echo "Error: Could not find SSH Operations Hub Python script" >&2
    exit 1
fi
'''
        
        install_path.write_text(wrapper_content)
        install_path.chmod(0o755)

    def _backup_existing(self, target_path: Path) -> Optional[Path]:
        """Create backup of existing installation."""
        if target_path.exists():
            backup_path = target_path.with_suffix(f"{target_path.suffix}.backup")
            shutil.copy2(target_path, backup_path)
            return backup_path
        return None

    def _copy_config_files(self, target_dir: Path):
        """Copy configuration files to target directory."""
        config_source = self.script_dir / "config"
        if config_source.exists():
            target_dir.mkdir(parents=True, exist_ok=True)
            for config_file in config_source.iterdir():
                if config_file.is_file():
                    shutil.copy2(config_file, target_dir / config_file.name)
            
            # Set proper permissions for user config
            if not self._check_sudo():  # User installation
                target_dir.chmod(0o700)
                for config_file in target_dir.iterdir():
                    if config_file.is_file():
                        config_file.chmod(0o600)

    def install(self, system_wide: bool = True, force: bool = False) -> bool:
        """Install SSH Operations Hub."""
        if system_wide and not self._check_sudo():
            print("Error: System-wide installation requires sudo privileges")
            return False
        
        # Determine installation paths
        bin_dir = self.system_bin_dir if system_wide else self.user_bin_dir
        config_dir = self.system_config_dir if system_wide else self.user_config_dir
        target_script = bin_dir / self.SCRIPT_NAME
        
        # Check if source script exists
        if not self.source_script.exists():
            print(f"Error: Source script not found at {self.source_script}")
            return False
        
        # Check for existing installation
        current_version = self._get_current_version(system_wide)
        if current_version and not force:
            print(f"SSH Operations Hub v{current_version} is already installed")
            print("Use --force to reinstall or use update command")
            return False
        
        try:
            # Create directories
            bin_dir.mkdir(parents=True, exist_ok=True)
            
            # Backup existing installation
            backup_path = self._backup_existing(target_script)
            if backup_path:
                print(f"Backed up existing installation to {backup_path}")
            
            # Copy Python script to lib directory (for system) or keep in place (for user)
            if system_wide:
                lib_dir = Path("/usr/local/lib/ssh-operations-hub")
                lib_dir.mkdir(parents=True, exist_ok=True)
                target_python_script = lib_dir / self.PYTHON_SCRIPT
                shutil.copy2(self.source_script, target_python_script)
                target_python_script.chmod(0o755)
                
                # Update wrapper to point to lib location
                wrapper_content = f'''#!/bin/bash
# SSH Operations Hub wrapper script
# Version: {self.VERSION}
# Installation type: System-wide

exec python3 "{target_python_script}" "$@"
'''
                target_script.write_text(wrapper_content)
            else:
                # For user installation, create wrapper pointing to source location
                self._create_executable(target_script, system_wide)
            
            target_script.chmod(0o755)
            
            # Copy configuration files
            self._copy_config_files(config_dir)
            
            # Set version
            self._set_version(system_wide)
            
            # Create symlinks for system-wide installation
            if system_wide:
                usr_bin_link = Path("/usr/bin") / self.SCRIPT_NAME
                try:
                    if usr_bin_link.exists() or usr_bin_link.is_symlink():
                        usr_bin_link.unlink()
                    usr_bin_link.symlink_to(target_script)
                except Exception as e:
                    print(f"Warning: Failed to create symlink in /usr/bin: {e}")
            
            install_type = "system-wide" if system_wide else "user"
            print(f"Installation completed successfully! ({install_type})")
            print(f"SSH Operations Hub v{self.VERSION} is now available as '{self.SCRIPT_NAME}'")
            
            if not system_wide:
                print(f"Note: Make sure {bin_dir} is in your PATH")
                print(f"Add this to your shell profile: export PATH=\"{bin_dir}:$PATH\"")
            
            return True
            
        except Exception as e:
            print(f"Installation failed: {e}")
            return False

    def update(self, system_wide: bool = True) -> bool:
        """Update existing installation."""
        current_version = self._get_current_version(system_wide)
        if not current_version:
            print("No existing installation found. Use install command instead.")
            return False
        
        if current_version == self.VERSION:
            print(f"SSH Operations Hub is already up to date (v{self.VERSION})")
            return True
        
        print(f"Updating SSH Operations Hub from v{current_version} to v{self.VERSION}")
        return self.install(system_wide, force=True)

    def uninstall(self, system_wide: bool = True) -> bool:
        """Uninstall SSH Operations Hub."""
        if system_wide and not self._check_sudo():
            print("Error: System-wide uninstallation requires sudo privileges")
            return False
        
        # Determine installation paths
        bin_dir = self.system_bin_dir if system_wide else self.user_bin_dir
        config_dir = self.system_config_dir if system_wide else self.user_config_dir
        target_script = bin_dir / self.SCRIPT_NAME
        
        current_version = self._get_current_version(system_wide)
        if not current_version:
            print("No installation found to uninstall")
            return False
        
        try:
            # Remove executable
            if target_script.exists():
                target_script.unlink()
                print(f"Removed {target_script}")
            
            # Remove old bash files if they exist
            old_bash_files = [
                bin_dir / "ssh-operations-hub.bash",
                bin_dir / "ssh-operations-hub",  # Could be bash version
            ]
            for old_file in old_bash_files:
                if old_file.exists():
                    old_file.unlink()
                    print(f"Removed old file {old_file}")
            
            # Remove lib directory for system installation
            if system_wide:
                lib_dir = Path("/usr/local/lib/ssh-operations-hub")
                if lib_dir.exists():
                    shutil.rmtree(lib_dir)
                    print(f"Removed {lib_dir}")
                
                # Remove symlink
                usr_bin_link = Path("/usr/bin") / self.SCRIPT_NAME
                if usr_bin_link.exists() or usr_bin_link.is_symlink():
                    usr_bin_link.unlink()
                    print(f"Removed {usr_bin_link}")
            
            # Ask about config directory
            if config_dir.exists():
                response = input(f"Remove configuration directory {config_dir}? (y/N): ")
                if response.lower() in ('y', 'yes'):
                    shutil.rmtree(config_dir)
                    print(f"Removed {config_dir}")
                else:
                    # Just remove version file
                    version_file = config_dir / "version"
                    if version_file.exists():
                        version_file.unlink()
            
            install_type = "system-wide" if system_wide else "user"
            print(f"SSH Operations Hub v{current_version} uninstalled successfully ({install_type})")
            return True
            
        except Exception as e:
            print(f"Uninstallation failed: {e}")
            return False

    def status(self):
        """Show installation status."""
        print("SSH Operations Hub Installation Status:")
        print("=" * 40)
        
        # Check system-wide installation
        system_version = self._get_current_version(system_wide=True)
        system_script = self.system_bin_dir / self.SCRIPT_NAME
        
        print(f"System-wide: {'Installed' if system_version else 'Not installed'}")
        if system_version:
            print(f"  Version: {system_version}")
            print(f"  Executable: {system_script}")
            print(f"  Config: {self.system_config_dir}")
        
        # Check user installation
        user_version = self._get_current_version(system_wide=False)
        user_script = self.user_bin_dir / self.SCRIPT_NAME
        
        print(f"User: {'Installed' if user_version else 'Not installed'}")
        if user_version:
            print(f"  Version: {user_version}")
            print(f"  Executable: {user_script}")
            print(f"  Config: {self.user_config_dir}")
        
        # Show available version
        print(f"Available version: {self.VERSION}")


def main():
    """Main entry point for installer."""
    parser = argparse.ArgumentParser(
        description="SSH Operations Hub Enhanced Installer",
        epilog="For more information, see the documentation at https://umd-uroc.github.io/docs/SSH Operations Hub"
    )
    
    parser.add_argument(
        'action',
        choices=['install', 'update', 'uninstall', 'status'],
        help='Action to perform'
    )
    parser.add_argument(
        '--user',
        action='store_true',
        help='Install for current user only (no sudo required)'
    )
    parser.add_argument(
        '--system',
        action='store_true',
        help='Install system-wide (requires sudo, default)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force installation even if already installed'
    )
    parser.add_argument(
        '--version',
        action='version',
        version=f'SSH Operations Hub Installer v{SSHOperationsHubInstaller.VERSION}'
    )
    
    args = parser.parse_args()
    
    # Determine installation mode
    if args.user and args.system:
        print("Error: Cannot specify both --user and --system")
        sys.exit(1)
    
    system_wide = not args.user  # Default to system-wide unless --user is specified
    
    installer = SSHOperationsHubInstaller()
    
    if args.action == 'install':
        success = installer.install(system_wide, args.force)
    elif args.action == 'update':
        success = installer.update(system_wide)
    elif args.action == 'uninstall':
        success = installer.uninstall(system_wide)
    elif args.action == 'status':
        installer.status()
        success = True
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()