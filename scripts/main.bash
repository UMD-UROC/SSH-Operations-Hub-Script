#!/bin/bash

###############################################################################
# Script: Drone Data Management Application
# Returns:
#   0 on success, 1 on failure
###############################################################################

# Allowed IPs: add ip ranges with {ip_range_start..ip_range_end} ex) {1..10}
allowed_ips=({1..10} 15 17 {20..25})

# Function to parse IP addresses:
# - Removes duplicates
# - Checks if IP address is allowed
parse_ips() {
    # Check if output array is passed as argument
    declare -n output_array="$1"
    shift
    
    # Initialize associative array to store unique IPs
    local -A unique_ips=()
    local valid_ip_found=false

    if [ $# -eq 0 ]; then
        echo "Error: No IP addresses provided"
        return 1
    fi

    # Iterate over IP suffixes passed as arguments
    for ip_suffix in "$@"; do
        if ! [[ "$ip_suffix" =~ ^[0-9]+$ ]]; then
            echo "Error: Invalid IP suffix '$ip_suffix' - must be a number"
            continue
        fi
        
        if ! [[ "${allowed_ips[*]}" =~ (^|[[:space:]])"$ip_suffix"($|[[:space:]]) ]]; then
            echo "Error: IP suffix '$ip_suffix' is not in the allowed range"
            continue
        fi
        
        if [[ -n "${unique_ips[$ip_suffix]}" ]]; then
            echo "Warning: Duplicate IP suffix '$ip_suffix' ignored"
            continue
        fi
        
        unique_ips[$ip_suffix]=1
        output_array+=("10.200.142.$ip_suffix")
        valid_ip_found=true
    done

    if ! $valid_ip_found; then
        echo "Error: No valid IP addresses were provided"
        return 1
    fi
}

# Function to process flags passed to script
process_arguments() {
    if [ $# -eq 0 ]; then
        echo "Error: No arguments provided"
        echo "Usage: $0 [-ip ip_list] [-cip ip_list] [-cmd command] [-ccmd command]"
        exit 1
    fi

    # Initialize arrays to store IP addresses
    ips=()
    main_command=""
    cips=()
    cmain_command=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            -ip)
                shift
                if [[ ! $1 || $1 == -* ]]; then
                    echo "Error: -ip flag requires at least one IP address"
                    exit 1
                fi
                while [[ $1 && $1 != -* ]]; do
                    ip_args+=("$1")
                    shift
                done
                if ! parse_ips ips "${ip_args[@]}"; then
                    echo "Error: Failed to process IP addresses"
                    exit 1
                fi
                ;;
            -cip)
                shift
                if [[ ! $1 || $1 == -* ]]; then
                    echo "Error: -cip flag requires at least one IP address"
                    exit 1
                fi
                while [[ $1 && $1 != -* ]]; do
                    cip_args+=("$1")
                    shift
                done
                if ! parse_ips cips "${cip_args[@]}"; then
                    echo "Error: Failed to process companion IP addresses"
                    exit 1
                fi
                ;;
            -cmd)
                if [ -z "$2" ]; then
                    echo "Error: -cmd flag requires a command argument"
                    exit 1
                fi
                main_command="$2"
                shift 2
                ;;
            -ccmd)
                if [ -z "$2" ]; then
                    echo "Error: -ccmd flag requires a command argument"
                    exit 1
                fi
                cmain_command="$2"
                shift 2
                ;;
            *)
                echo "Error: Unknown option '$1'"
                echo "Available options:"
                echo "  -ip   : List of IP addresses for primary drones"
                echo "  -cip  : List of IP addresses for companion drones"
                echo "  -cmd  : Command to execute on primary drones"
                echo "  -ccmd : Command to execute on companion drones"
                exit 1
                ;;
        esac
    done
}

# Function that executes commands
execute_commands() {
    if [ ${#ips[@]} -eq 0 ] && [ -z "$main_command" ]; then
        echo "Warning: No primary drone IPs or commands specified"
    fi

    for ip in "${ips[@]}"; do
        DRONE_NUM="${ip##*.}" # Store last part of IP in accessible variable to dynamically run commands
        command="${main_command//\$DRONE_NUM/$DRONE_NUM}"
        echo "Running '$command' on $ip"
        # ssh root@"$ip" "$command"
        # Debug Command
        # - echo $DRONE_NUM
    done

    for cip in "${cips[@]}"; do
        DRONE_NUM="${cip##*.}"
        command="${cmain_command//\$DRONE_NUM/$DRONE_NUM}"
        echo "Running '$command' on $cip"
        # ssh root@"$cip" "$command"
        # Debug Command
        # - echo $DRONE_NUM
    done
}

# Main script execution
process_arguments "$@"
execute_commands

# Indicate success
exit 0
