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
        echo "Usage: $0 [-primary|-ip ip_list] [-puser|-user username] [-secondary ip_list] [-suser username] [-cmd command]"
        exit 1
    fi

    # Initialize variables
    primary_ips=()
    secondary_ips=()
    main_command=""
    primary_user=""
    secondary_user=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            -primary|-ip)
                shift
                if [[ ! $1 || $1 == -* ]]; then
                    echo "Error: -primary/-ip flag requires at least one IP address"
                    exit 1
                fi
                ip_args=()
                while [[ $1 && $1 != -* ]]; do
                    ip_args+=("$1")
                    shift
                done
                if ! parse_ips primary_ips "${ip_args[@]}"; then
                    echo "Error: Failed to process primary IP addresses"
                    exit 1
                fi
                ;;
            -secondary)
                shift
                if [[ ! $1 || $1 == -* ]]; then
                    echo "Error: -secondary flag requires at least one IP address"
                    exit 1
                fi
                ip_args=()
                while [[ $1 && $1 != -* ]]; do
                    ip_args+=("$1")
                    shift
                done
                if ! parse_ips secondary_ips "${ip_args[@]}"; then
                    echo "Error: Failed to process secondary IP addresses"
                    exit 1
                fi
                ;;
            -puser|-user)
                if [ -z "$2" ]; then
                    echo "Error: -puser/-user flag requires a username argument"
                    exit 1
                fi
                primary_user="$2"
                shift 2
                ;;
            -suser)
                if [ -z "$2" ]; then
                    echo "Error: -suser flag requires a username argument"
                    exit 1
                fi
                secondary_user="$2"
                shift 2
                ;;
            -cmd)
                if [ -z "$2" ]; then
                    echo "Error: -cmd flag requires a command argument"
                    exit 1
                fi
                main_command="$2"
                shift 2
                ;;
            *)
                echo "Error: Unknown option '$1'"
                echo "Available options:"
                echo "  -primary, -ip  : List of IP addresses for primary group"
                echo "  -puser, -user  : Username for primary group"
                echo "  -secondary     : List of IP addresses for secondary group"
                echo "  -suser         : Username for secondary group"
                echo "  -cmd           : Command to execute on all drones"
                exit 1
                ;;
        esac
    done
}

# Function that executes commands
execute_commands() {
    if [ ${#primary_ips[@]} -eq 0 ] && [ ${#secondary_ips[@]} -eq 0 ]; then
        echo "Warning: No IP addresses specified"
        return
    fi

    if [ -z "$main_command" ]; then
        echo "Warning: No command specified"
        return
    fi

    # Execute for primary group
    for ip in "${primary_ips[@]}"; do
        DRONE_NUM="${ip##*.}"
        command="${main_command//\$DRONE_NUM/$DRONE_NUM}"
        echo "Running '$command' on $primary_user@$ip"
        #ssh "$primary_user@$ip" "$command"
    done

    # Execute for secondary group
    if [ ${#secondary_ips[@]} -gt 0 ] && [ -n "$secondary_user" ]; then
        for ip in "${secondary_ips[@]}"; do
            DRONE_NUM="${ip##*.}"
            command="${main_command//\$DRONE_NUM/$DRONE_NUM}"
            echo "Running '$command' on $secondary_user@$ip"
            ssh "$secondary_user@$ip" "$command"
        done
    fi
}

# Main script execution
process_arguments "$@"
execute_commands

# Indicate success
exit 0
