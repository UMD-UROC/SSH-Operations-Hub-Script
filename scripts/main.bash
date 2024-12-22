#!/bin/bash
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

    # Iterate over IP suffixes passed as arguments
    for ip_suffix in "$@"; do
        # Check if IP suffix is allowed and not duplicated
        if [[ "${allowed_ips[*]}" =~ (^|[[:space:]])"$ip_suffix"($|[[:space:]]) ]] && [[ -z "${unique_ips[$ip_suffix]}" ]]; then
            unique_ips[$ip_suffix]=1
            output_array+=("10.200.142.$ip_suffix")
            valid_ip_found=true
        else
            echo "Duplicated or Invalid IP suffix: $ip_suffix"
        fi
    done

    if ! $valid_ip_found; then
        return 1
    fi
}

# Function to process flags passed to script
process_arguments() {
    # Initialize arrays to store IP addresses
    ips=()
    main_command=""
    cips=()
    cmain_command=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            -ip)
                shift
                while [[ $1 && $1 != -* ]]; do
                    ip_args+=("$1")
                    shift
                done
                parse_ips ips "${ip_args[@]}"
                ;;
            -cip)
                shift
                while [[ $1 && $1 != -* ]]; do
                    cip_args+=("$1")
                    shift
                done
                parse_ips cips "${cip_args[@]}"
                ;;
            -cmd)
                [ -z "$2" ] && echo "Error: No command" && exit 1
                main_command="$2"
                shift 2
                ;;
            -ccmd)
                [ -z "$2" ] && echo "Error: No command" && exit 1
                cmain_command="$2"
                shift 2
                ;;
            *)
                echo "Unknown option: $1"
                exit 1
                ;;
        esac
    done
}

# Function that executes commands
execute_commands() {
    for ip in "${ips[@]}"; do
        drone_num="${ip##*.}" # Store last part of IP in accessible variable to dynamically run commands
        command="${main_command//\$drone_num/$drone_num}"
        echo "Running '$command' on $ip"
        # ssh root@"$ip" "$command"
        # Debug Command
        # - echo $drone_num
    done

    for cip in "${cips[@]}"; do
        drone_num="${cip##*.}"
        command="${cmain_command//\$drone_num/$drone_num}"
        echo "Running '$command' on $cip"
        # ssh root@"$cip" "$command"
        # Debug Command
        # - echo $drone_num
    done
}

# Main script execution
process_arguments "$@"
execute_commands

# Indicate success
exit 0
