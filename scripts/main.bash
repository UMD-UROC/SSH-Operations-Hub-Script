#!/bin/bash

allowed_ips=(1 3 4 5 6 7 8 9 10 15 17 20 21 22 23 24 25)

parse_ips() {
    local -n output_array="$1"
    shift
    for ip_suffix in "$@"; do
        # Ensure the provided suffix is numeric
        if [[ ! $ip_suffix =~ ^[0-9]+$ ]]; then
            echo "Invalid IP suffix: $ip_suffix"
            exit 1
        fi
        # Check if the suffix is in the allowed list
        if [[ " ${allowed_ips[*]} " =~ " $ip_suffix " ]]; then
            output_array+=("10.200.142.$ip_suffix")
        else
            echo "Invalid IP suffix: $ip_suffix"
            exit 1
        fi
    done
}

add_ips() {
    local -n output_list="$1"
    shift
    for ip in "$@"; do
        if [[ ! " ${output_list[*]} " =~ " $ip " ]]; then
            output_list+=("$ip")
        fi
    done
}

process_arguments() {
    ips=()
    main_command=""

    while [[ $# -gt 0 ]]; do
        case $1 in
        -ip) 
            shift
            local ip_args=()
            while [[ $# -gt 0 && $1 != -* ]]; do
                ip_args+=("$1")
                shift
            done
            parse_ips ips "${ip_args[@]}"

            ;; 
        -cmd) 
            main_command="$2"
            shift 2

            ;; 
        *) 
            echo "Unknown option: $1"
            exit 1

            ;; 
        esac
    done
}

run_command() {
    local ip="$1"
    local command="$2"
    echo "Running '$command' on $ip"
    # Uncomment the line below to execute the command
    # ssh "$ip" "$command"
}

execute_commands() {
    for ip in "${ips[@]}"; do
        run_command "$ip" "$main_command"
    done
}

process_arguments "$@"
execute_commands
