# UMD UAS Lab Drone Data Management App

A bash-based utility for managing multiple drones in the University of Maryland's Unmanned Aerial System Lab.

## Features

- Manage multiple drone connections simultaneously
- Execute commands across primary and companion drones
- IP address validation and deduplication
- Flexible command execution with drone number substitution

## Usage

```bash
./main.bash [-ip ip_list] [-cip ip_list] [-cmd command] [-ccmd command]
```

### Arguments

- `-ip`: List of IP suffixes for primary drones
- `-cip`: List of IP suffixes for companion drones
- `-cmd`: Command to execute on primary drones
- `-ccmd`: Command to execute on companion drones

### Examples

```bash
# Execute a command on primary drones 1, 2, and 3
./main.bash -ip 1 2 3 -cmd "echo Hello from drone \$DRONE_NUM"

# Execute different commands on primary and companion drones
./main.bash -ip 1 2 -cip 3 4 -cmd "start_primary" -ccmd "start_companion"
```

## IP Address Configuration

The script uses the base IP address `10.200.142.X`, where X is the provided IP suffix.
Currently allowed IP suffixes:
- 1 through 10
- 15
- 17
- 20 through 25

To modify allowed IP ranges, edit the `allowed_ips` array in the script.

## Error Handling

The script includes comprehensive error checking for:
- Invalid IP addresses
- Duplicate IP addresses
- Missing command arguments
- Invalid command-line options

## Requirements

- Bash shell
- SSH access to drones
- Proper network configuration

## Notes

- Commands using `\$DRONE_NUM` will have the value replaced with the actual drone number
- SSH commands are currently commented out for testing purposes
