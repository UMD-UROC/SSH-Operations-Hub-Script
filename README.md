# UMD UAS Drone Data Management Application

A bash script for managing and executing commands across multiple drones in the UMD UAS Lab network.

## Features

- IP address validation and deduplication
- Support for primary and secondary drone groups
- Variable substitution in commands using `$DRONE_NUM`
- Comprehensive error handling
- Configurable allowed IP ranges

## Usage

```bash
./main.bash [-primary|-ip ip_list] [-puser|-user username] [-secondary ip_list] [-suser username] [-cmd command]
```

### Arguments

- `-primary`, `-ip`: List of IP addresses for primary group
- `-puser`, `-user`: Username for primary group
- `-secondary`: List of IP addresses for secondary group
- `-suser`: Username for secondary group
- `-cmd`: Command to execute on all drones

### IP Address Format

- IP addresses are specified using the last octet only (1-255)
- Allowed IP ranges are configured in the script
- Current allowed IPs: 1-10, 15, 17, 20-25

### Examples

Execute a command on primary drones:
```bash
./main.bash -primary 1 2 3 -user pilot -cmd "echo Drone \$DRONE_NUM ready"
```

Execute on both primary and secondary groups:
```bash
./main.bash -primary 1 2 -user pilot1 -secondary 3 4 -suser pilot2 -cmd "status"
```

## Error Handling

The script includes comprehensive error checking for:
- Invalid IP addresses
- Duplicate IPs
- Missing arguments
- Unauthorized IP ranges
- Invalid command format

## Return Values

- 0: Success
- 1: Error (with descriptive message)