#!/bin/bash

################################################################################
# Drone Data Management Application
#
# This script manages SSH connections and command execution across multiple drones
# in a network. It supports two groups of drones (primary and secondary) and can
# execute commands with variable substitution.
#
# Usage:
#   ./main.bash [-primary|-ip ip_list] [-puser|-user username] 
#               [-secondary ip_list] [-suser username] [-cmd command]
#
# Arguments:
#   -primary, -ip  : List of IP suffixes for primary drone group
#   -puser, -user  : Username for primary group (supports $DRONE_NUM substitution)
#   -secondary     : List of IP suffixes for secondary drone group
#   -suser         : Username for secondary group (supports $DRONE_NUM substitution)
#   -cmd          : Command to execute (supports $DRONE_NUM substitution)
#
# Returns:
#   0 on success, 1 on error
################################################################################

#===== INITIALIZATION ==========================================================#

# Enable CTRL+C handling for cleanup
trap 'echo "Interrupted! Stopping all SSH connections..."; kill 0; exit 1' SIGINT

# Configuration
allowed_ips=($(seq 1 10) 15 17 $(seq 20 25))  # Supported IP address ranges

# Add max parallel SSH connections
MAX_PARALLEL_CONNECTIONS=10

#===== UTILITY FUNCTIONS =====================================================#

# Validate a single IP suffix
# Args:
#   $1: IP suffix to validate
# Returns:
#   0 if valid, 1 if invalid
validate_ip_suffix() {
    local ip_suffix=$1
    
    [[ "$ip_suffix" =~ ^[0-9]+$ ]] || return 1
    [[ "${allowed_ips[*]}" =~ (^|[[:space:]])"$ip_suffix"($|[[:space:]]) ]] || return 1
    
    return 0
}

# Process IP addresses more efficiently
# Args:
#   $1: Name of output array to store processed IPs
#   $@: List of IP suffixes to process
parse_ips() {
    declare -n output_array="$1"
    shift
    
    local -A seen=()
    local valid_count=0
    
    [[ $# -eq 0 ]] && { echo "Error: No IP addresses provided"; return 1; }
    
    for ip_suffix in "$@"; do
        if ! validate_ip_suffix "$ip_suffix"; then
            echo "Error: Invalid or disallowed IP suffix '$ip_suffix'"
            continue
        fi
        
        if [[ -n "${seen[$ip_suffix]}" ]]; then
            echo "Warning: Skipping duplicate IP suffix '$ip_suffix'"
            continue
        fi
        
        seen[$ip_suffix]=1
        output_array+=("10.200.142.$ip_suffix")
        ((valid_count++))
    done
    
    [[ $valid_count -eq 0 ]] && { echo "Error: No valid IP addresses found"; return 1; }
    return 0
}

# Execute SSH command with timeout and error handling
# Args:
#   $1: username
#   $2: IP address
#   $3: command
execute_ssh_command() {
    local user=$1
    local ip=$2
    local cmd=$3
    local timeout=10
    
    echo "Running '$cmd' on $user@$ip"
    if ! ssh -o ConnectTimeout=$timeout "$user@$ip" "$cmd" 2>/dev/null; then
        echo "Error: Failed to execute command on $user@$ip"
        return 1
    fi
}

#===== CORE FUNCTIONS =======================================================#

# Process and validate command line arguments
# Sets global variables: primary_ips, secondary_ips, main_command, 
#                       primary_user, secondary_user
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

# Optimized command execution with parallel control
execute_commands() {
    [[ ${#primary_ips[@]} -eq 0 && ${#secondary_ips[@]} -eq 0 ]] && { echo "Warning: No IP addresses specified"; return; }
    [[ -z "$main_command" ]] && { echo "Warning: No command specified"; return; }

    local running=0
    local pids=()

    # Function to wait for available slot
    wait_for_slot() {
        while [[ $running -ge $MAX_PARALLEL_CONNECTIONS ]]; do
            for pid in "${!pids[@]}"; do
                if ! kill -0 "$pid" 2>/dev/null; then
                    unset pids[$pid]
                    ((running--))
                fi
            done
            sleep 0.1
        done
    }

    # Process primary group
    for ip in "${primary_ips[@]}"; do
        wait_for_slot
        DRONE_NUM="${ip##*.}"
        user="${primary_user//\$DRONE_NUM/$DRONE_NUM}"
        command="${main_command//\$DRONE_NUM/$DRONE_NUM}"
        execute_ssh_command "$user" "$ip" "$command" &
        pids[$!]=1
        ((running++))
    done

    # Process secondary group
    if [[ ${#secondary_ips[@]} -gt 0 && -n "$secondary_user" ]]; then
        for ip in "${secondary_ips[@]}"; do
            wait_for_slot
            DRONE_NUM="${ip##*.}"
            user="${secondary_user//\$DRONE_NUM/$DRONE_NUM}"
            command="${main_command//\$DRONE_NUM/$DRONE_NUM}"
            execute_ssh_command "$user" "$ip" "$command" &
            pids[$!]=1
            ((running++))
        done
    fi

    # Wait for all remaining processes
    wait
}

#===== MAIN EXECUTION =======================================================#

process_arguments "$@"
execute_commands
wait

exit 0
