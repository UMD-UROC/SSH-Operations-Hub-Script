# SSH Operations Hub

A powerful Python tool for executing commands on multiple SSH servers concurrently with advanced features for network operations management.

## Features

### Core Functionality
- **Parallel SSH Execution**: Execute commands on multiple servers simultaneously with configurable connection limits
- **IP Validation & Whitelisting**: Security features to restrict access to authorized IP addresses only
- **Dual Server Groups**: Support for primary and secondary server groups with different user credentials
- **Variable Substitution**: Dynamic variable replacement (`$CLIENT_NUM`) in commands and usernames
- **Configuration Management**: Flexible configuration via files in multiple locations
- **IP Range Support**: Expand IP ranges (e.g., "1-5", "150-154") automatically
- **Enhanced Security**: Strict SSH options and secure connection handling
- **Signal Handling**: Clean shutdown on interruption (Ctrl+C)
- **Timeout Management**: Both per-connection and global timeout protection
- **Error Handling**: Comprehensive error reporting and formatted output

### Installation Features
- **Multiple Installation Modes**: System-wide (`/usr/local/bin`) or user-only (`~/.local/bin`)
- **Update Capability**: Version checking and seamless updates
- **Uninstall Support**: Clean removal with optional configuration preservation
- **Backup Protection**: Automatic backup of existing installations
- **Version Tracking**: Proper version management and status reporting

## Installation

### Quick Install (User Mode)
```bash
python3 install.py install --user
```

### System-wide Install (requires sudo)
```bash
sudo python3 install.py install --system
```

### Installation Commands
- `python3 install.py install [--user|--system] [--force]` - Install the tool
- `python3 install.py update [--user|--system]` - Update existing installation
- `python3 install.py uninstall [--user|--system]` - Remove installation
- `python3 install.py status` - Show installation status

## Usage

### Basic Usage
```bash
ssh-operations-hub --ips 1 2 3 --primary-user root --command "uptime"
```

### Advanced Examples

#### Primary and Secondary Groups
```bash
ssh-operations-hub \
  --primary-ips 1 2 3 --primary-user root \
  --secondary-ips 10 11 12 --secondary-user admin \
  --command "systemctl status nginx"
```

#### Custom IP Prefix
```bash
ssh-operations-hub --ip-prefix 192.168.1 --ips 10 20 30 --primary-user admin --command "df -h"
```

#### Variable Substitution
```bash
ssh-operations-hub --ips 1 2 3 --primary-user "user\$CLIENT_NUM" --command "echo 'I am client \$CLIENT_NUM'"
```

### Command-Line Options

- `--primary-ips`, `--ips`: List of IP suffixes for primary group
- `--secondary-ips`: List of IP suffixes for secondary group  
- `--primary-user`: Username for primary group (default: root)
- `--secondary-user`: Username for secondary group (default: admin)
- `--command`: Command to execute on all clients (required)
- `--ip-prefix`: Custom IP prefix (e.g., 192.168.1)

## Configuration

### Configuration Locations (in order of preference)
1. `$HOME/.config/ssh-operations-hub/defaults.json` (User config)
2. `<script_dir>/config/defaults.json` (Development)
3. `/etc/ssh-operations-hub/defaults.json` (System config)

### Configuration Format
```json
{
    "ip_prefix": "10.200.142",
    "allowed_ips": ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "15", "17", "20", "21", "22", "23", "24", "25", "150-154"]
}
```

### IP Range Format
- Individual IPs: `["1", "2", "3"]`
- Ranges: `["1-5"]` (expands to 1 2 3 4 5)
- Mixed: `["1", "2", "5-7", "10"]` (expands to 1 2 5 6 7 10)

## Technical Details

### Performance Improvements (vs. Bash version)
- **Better Parallel Control**: Uses `concurrent.futures.ThreadPoolExecutor` for optimal thread management
- **Efficient IP Validation**: Uses Python's built-in data structures for faster lookups
- **Improved Error Handling**: Exception-based error handling with proper cleanup
- **Better Resource Management**: Automatic cleanup of connections and threads
- **Enhanced Configuration**: More robust configuration parsing and validation

### Security Features
- **IP Whitelisting**: Only allowed IP suffixes can be targeted
- **SSH Security Options**: 
  - `BatchMode=yes` (no interactive prompts)
  - `ConnectTimeout=5` (connection timeout)
  - `StrictHostKeyChecking=accept-new` (accept new host keys)
  - `ControlMaster=no` (no connection sharing)
- **Input Validation**: Comprehensive validation of all inputs
- **Configuration Protection**: Secure file permissions for configuration files

### Architecture
- **Main Class**: `SSHOperationsHub` - Core functionality
- **Installer Class**: `SSHOperationsHubInstaller` - Installation management
- **Thread Pool**: Configurable parallel execution (default: 10 concurrent connections)
- **Signal Handling**: Clean shutdown on SIGINT/SIGTERM
- **Logging**: Structured logging with proper formatting

## Migration from Bash Version

The Python version has been modernized with a new, more intuitive interface:

### Key Changes
- 🔄 **Modern CLI Arguments**: Updated from short flags (`-ip`, `-cmd`, `-suser`) to descriptive long options (`--ips`, `--command`, `--secondary-user`)
- 📄 **JSON Configuration**: Migrated from bash-style config to standard JSON format
- 🗑️ **Removed Legacy**: Old bash scripts have been removed for cleaner codebase
- 🧹 **Enhanced Uninstaller**: Automatically removes old bash installations

### Migration Steps
1. **Update CLI Commands**: Replace old arguments:
   - `-ip` → `--ips` or `--primary-ips`
   - `-cmd` → `--command`
   - `-user`/`-puser` → `--primary-user`
   - `-suser` → `--secondary-user`
   - `-primary` → `--primary-ips`
   - `-secondary` → `--secondary-ips`

2. **Convert Configuration**: Update config files from bash format to JSON:
   ```bash
   # Old format (defaults.conf)
   IP_PREFIX="10.200.142"
   ALLOWED_IPS="1 2 3 150-154"
   ```
   ```json
   // New format (defaults.json)
   {
       "ip_prefix": "10.200.142", 
       "allowed_ips": ["1", "2", "3", "150-154"]
   }
   ```

3. **Uninstall Old Version**: The uninstaller will automatically remove old bash files

### Core Features Preserved
- ✅ Same IP validation and whitelisting rules
- ✅ Same variable substitution (`$CLIENT_NUM`)
- ✅ Same dual server group functionality  
- ✅ Same parallel execution capabilities
- ✅ Same output formatting and error messages

## Testing

Run the test suite:
```bash
python3 test_ssh_operations_hub.py
python3 test_installer.py
```

## Requirements

- Python 3.6 or later
- SSH client (`ssh` command)
- Standard Linux/Unix environment

## Version History

### v2.0.0 (Python Rewrite)
- Complete rewrite in Python for better performance and maintainability
- Enhanced installer with update/uninstall capabilities
- Improved parallel processing with ThreadPoolExecutor
- Comprehensive test coverage
- Better error handling and logging
- Full backward compatibility with v1.x configuration and CLI

### v1.x (Bash Original)
- Original Bash implementation
- Basic installation support
- Parallel SSH execution
- Configuration file support

## Support

For complete documentation and support:
- Documentation: https://umd-uroc.github.io/docs/SSH Operations Hub
- Issues: Use the GitHub issue tracker
- Configuration: Check the config file examples in the `config/` directory

## License

See LICENSE file for details.