#!/bin/bash

################################################################################
# SSH Operations Hub
#
# TECHNICAL DETAILS:
# - Uses bash built-in arrays and associative arrays for IP management
# - Implements concurrent execution with job control
# - Handles SIGINT/SIGTERM for clean process termination
# - Uses enhanced SSH options for security and reliability
#
# SECURITY FEATURES:
# - IP validation against whitelist
# - Strict SSH options (StrictHostKeyChecking, BatchMode)
# - Protected configuration files
# - Sanitized command handling
#
# CONFIGURATION FILES:
# 1. User config: $HOME/.config/ssh-operations-hub/defaults.conf
# 2. System config: $SCRIPT_DIR/../config/defaults.conf
#
# For complete documentation:
# https://cdenihan.gitbook.io/ssh-operations-hub-script-docs
################################################################################

#===== INITIALIZATION ==========================================================#

# Determine script location and config paths
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DEFAULT_IP_PREFIX="10.200.142"

# Try multiple config locations in order of preference
CONFIG_LOCATIONS=(
    "$HOME/.config/ssh-operations-hub/defaults.conf" # User config
    "$SCRIPT_DIR/../config/defaults.conf"           # Running from project
)

# Load first available config file
IP_PREFIX="$DEFAULT_IP_PREFIX"
ALLOWED_IPS="1 2 3 4 5 6 7 8 9 10 15 17 20 21 22 23 24 25"  # Default if not in config
for config_file in "${CONFIG_LOCATIONS[@]}"; do
    if [ -f "$config_file" ]; then
        source "$config_file"
        break
    fi
done

# Convert ALLOWED_IPS string to array
IFS=' ' read -ra allowed_ips <<< "$ALLOWED_IPS"

# Enable CTRL+C handling for cleanup
trap 'echo "Interrupted! Stopping all SSH connections..."; pkill -P "$$"; wait; exit 1' SIGINT SIGTERM

# Configuration
MAX_PARALLEL_CONNECTIONS=10

# Enhanced SSH options for better security
SSH_OPTS="-o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new -o ControlMaster=no"

#===== UTILITY FUNCTIONS =====================================================#

# Expand IP ranges into an array
# Examples: 
# - "1-5" expands to "1 2 3 4 5"
# - "7" remains "7"
# - "1-3 7-9" expands to "1 2 3 7 8 9"
expand_range() {
    local range=$1
    if [[ $range =~ ^([0-9]+)-([0-9]+)$ ]]; then
        local start="${BASH_REMATCH[1]}"
        local end="${BASH_REMATCH[2]}"
        if (( start <= end )); then
            seq "$start" "$end"
        fi
    else
        echo "$range"
    fi
}

# Parse and validate the ALLOWED_IPS configuration
# Converts string ranges into a complete array of allowed IP suffixes
# Example: "1-3 5 7-9" becomes [1,2,3,5,7,8,9]
parse_allowed_ips() {
    local ranges
    IFS=' ' read -ra ranges <<< "$ALLOWED_IPS"
    allowed_ips=()
    
    for range in "${ranges[@]}"; do
        while IFS= read -r num; do
            allowed_ips+=("$num")
        done < <(expand_range "$range")
    done
}

# Validates an IP suffix against the allowed list
# Security check to prevent unauthorized access attempts
# Returns: 0 if valid, 1 if invalid
validate_ip_suffix() {
    local ip_suffix=$1

    [[ "$ip_suffix" =~ ^[0-9]+$ ]] || return 1
    
    # Check if IP is in allowed list
    for allowed in "${allowed_ips[@]}"; do
        if [[ "$ip_suffix" == "$allowed" ]]; then
            return 0
        fi
    done
    
    return 1
}

# Validates IP prefix format and range
# Ensures the prefix follows IPv4 format and valid ranges
# Example valid formats: "192.168.1" or "10.0.0"
validate_ip_prefix() {
    local prefix="$1"
    # Remove trailing dot if present
    prefix="${prefix%%.}"
    
    # Match X.X.X format where X is 1-3 digits
    if [[ ! "$prefix" =~ ^([0-9]{1,3}\.){2}[0-9]{1,3}$ ]]; then
        return 1
    fi
    
    # Validate each octet is in range 0-255
    local IFS='.'
    read -ra octets <<< "$prefix"
    for octet in "${octets[@]}"; do
        if [ "$octet" -gt 255 ] || [ "$octet" -lt 0 ]; then
            return 1
        fi
    done
    return 0
}

# Process and validate a list of IP addresses
# Handles deduplication and validation against allowed IPs
# Args:
#   $1: Name of array to store results
#   $@: List of IP suffixes to process
# Returns: 0 on success, 1 on failure
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
        output_array+=("$IP_PREFIX.$ip_suffix")
        ((valid_count++))
    done

    [[ $valid_count -eq 0 ]] && { echo "Error: No valid IP addresses found"; return 1; }
    return 0
}

# Verify SSH client availability
# Essential check before attempting any connections
check_ssh() {
    command -v ssh >/dev/null 2>&1 || { echo "Error: SSH client is not installed"; exit 1; }
}

# Execute a single SSH command with proper error handling
# Implements timeout protection and formatted output
# Args:
#   $1: Username
#   $2: IP address
#   $3: Command to execute
# Returns: Command execution status
execute_ssh_command() {
    local user="$1"
    local ip="$2"
    local cmd="$3"
    local timeout=10
    local output
    local status
    local client_num="${ip##*.}"
    local label="[Client $client_num | $ip]"

    # Test SSH connection first with enhanced options
    if ! timeout "$timeout" ssh $SSH_OPTS "$user@$ip" exit 0 2>/dev/null; then
        echo "$label Error: Could not establish SSH connection to $user@$ip"
        return 1
    fi

    echo "$label Running '$cmd' on $user@$ip"
    if ! output=$(ssh $SSH_OPTS "$user@$ip" "$cmd" 2>&1); then
        status=$?
        echo "$label Error: Command failed with status $status"
        echo "$label Output: $output"
        return "$status"
    fi
    while IFS= read -r line; do
        echo "$label $line"
    done <<< "$output"
}

#===== CORE FUNCTIONS =======================================================#

# Process command line arguments and validate inputs
# Sets up global variables for execution phase
# Handles all supported flags and their validation
process_arguments() {
    if [ $# -eq 0 ]; then
        echo "Error: No arguments provided"
        echo "Usage: $0 [-primary|-ip ip_list] [-ip-prefix 192.168.1] [-puser|-user username] [-secondary ip_list] [-suser username] [-cmd command]"
        echo "To change Allowed IPs, modify the variable in the config file"
        echo "For more information, see the documentation at https://cdenihan.gitbook.io/ssh-operations-hub-script-docs"
        exit 1
    fi

    # Initialize variables
    primary_ips=()
    secondary_ips=()
    main_command=""
    primary_user="root"    # Set default user to root
    secondary_user="admin"  # Set default user to root

    while [[ $# -gt 0 ]]; do
        case "$1" in
        -primary | -ip) 
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
        -puser | -user) 
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
        -ip-prefix)
            if [ -z "$2" ]; then
                echo "Error: -ip-prefix flag requires an argument (e.g., 192.168.1)"
                exit 1
            fi
            # Remove any trailing dot and validate
            local new_prefix="${2%%.}"
            if ! validate_ip_prefix "$new_prefix"; then
                echo "Error: Invalid IP prefix format. Use format: XXX.XXX.XXX (0-255)"
                exit 1
            fi
            IP_PREFIX="$new_prefix"
            shift 2
            ;;
        *) 
            echo "Error: Unknown option '$1'"
            echo "Available options:"
            echo "  -primary, -ip  : List of IP addresses for primary group"
            echo "  -ip-prefix     : Custom IP prefix (e.g., 192.168.1)"
            echo "  -puser, -user  : Username for primary group"
            echo "  -secondary     : List of IP addresses for secondary group"
            echo "  -suser         : Username for secondary group"
            echo "  -cmd           : Command to execute on all clients"
            exit 1
            ;; 
        esac
    done
}

# Main execution controller
# Manages parallel execution of commands across all targets
# Implements global timeout and proper process cleanup
execute_commands() {
    local timeout=3600  # 1 hour timeout
    
    # Start timeout monitor in background
    (
        sleep $timeout
        echo "Error: Global execution timeout reached. Terminating..."
        pkill -P $$
    ) & 
    local timeout_pid=$!

    [[ ${#primary_ips[@]} -eq 0 && ${#secondary_ips[@]} -eq 0 ]] && { echo "Warning: No IP addresses specified"; return; }
    [[ -z "$main_command" ]] && { echo "Warning: No command specified"; return; }

    local running=0
    declare -A pids

    # Function to wait for available slot
    wait_for_slot() {
        while : ; do
            local current_running=0
            for pid in "${!pids[@]}"; do
                if kill -0 "$pid" 2>/dev/null; then
                    ((current_running++))
                else
                    wait "$pid" 2>/dev/null
                    unset pids[$pid]
                fi
            done
            [[ $current_running -lt $MAX_PARALLEL_CONNECTIONS ]] && break
            sleep 0.1
        done
    }

    # Process primary group
    for ip in "${primary_ips[@]}"; do
        wait_for_slot
        CLIENT_NUM="${ip##*.}"
        user="${primary_user//\$CLIENT_NUM/$CLIENT_NUM}"
        command="${main_command//\$CLIENT_NUM/$CLIENT_NUM}"
        execute_ssh_command "$user" "$ip" "$command" &
        pid=$!
        pids[$pid]=$ip
        ((running++))
    done

    # Process secondary group
    if [[ ${#secondary_ips[@]} -gt 0 && -n "$secondary_user" ]]; then
        for ip in "${secondary_ips[@]}"; do
            wait_for_slot
            CLIENT_NUM="${ip##*.}"
            user="${secondary_user//\$CLIENT_NUM/$CLIENT_NUM}"
            command="${main_command//\$CLIENT_NUM/$CLIENT_NUM}"
            execute_ssh_command "$user" "$ip" "$command" &
            pid=$!
            pids[$pid]=$ip
            ((running++))
        done
    fi

    # Wait for all remaining processes and cleanup
    while [[ ${#pids[@]} -gt 0 ]]; do
        for pid in "${!pids[@]}"; do
            if ! kill -0 "$pid" 2>/dev/null; then
                wait "$pid" 2>/dev/null
                unset pids[$pid]
                ((running--))
            fi
        done
        sleep 0.1
    done

    # Clean up timeout monitor
    kill $timeout_pid 2>/dev/null
    wait $timeout_pid 2>/dev/null

    # Final cleanup of any remaining processes
    jobs -p | xargs -r kill 2>/dev/null
    wait 2>/dev/null
}

#===== MAIN EXECUTION =======================================================#

# Check for SSH availability
check_ssh

# Parse allowed IPs before processing arguments
parse_allowed_ips

process_arguments "$@"
execute_commands

exit $?  # Return actual exit status
