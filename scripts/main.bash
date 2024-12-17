# Define allowed ip suffixes
allowed_ips=(1 3 4 5 6 7 8 9 10 15 17 20 21 22 23 24 25)

parse_ips() {
    # Declare temporary arrays and take args
    declare -n output_array="$1"
    shift
    local -A unique_ips
    local temp_array=()

    # Remove diplicate arrays and add ip suffixes to ip prefixes
    for ip_suffix in "$@"; do
        if [[ $ip_suffix =~ ^[0-9]+$ ]] && [[ " ${allowed_ips[*]} " == *" $ip_suffix "* ]] && [[ -z "${unique_ips[$ip_suffix]}" ]]; then
            unique_ips["$ip_suffix"]=1
            temp_array+=("10.200.142.$ip_suffix")
        else
            [[ -z "${unique_ips[$ip_suffix]}" ]] && echo "Invalid or disallowed IP suffix: $ip_suffix"
        fi
    done

    output_array=("${temp_array[@]}")
}

# Main function that handles parameters passed to the script
process_arguments() {
    # Define variables
    ips=()
    main_command=""
    cips=()
    cmain_command=""

    # Take arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
        -ip | -cip)
            option="$1"
            shift
            ip_args=()
            while [[ $# -gt 0 && $1 != -* ]]; do
                ip_args+=("$1")
                shift
            done
            if [[ $option == "-ip" ]]; then
                parse_ips ips "${ip_args[@]}"
            else
                parse_ips cips "${ip_args[@]}"
            fi



            ;; 
        -cmd | -ccmd)
            if [[ -z $2 ]]; then
                echo "Error: No command provided after $1"
                exit 1
            fi
            [[ $1 == "-cmd" ]] && main_command="$2" || cmain_command="$2"
            shift 2



            ;; 
        *) 
            echo "Unknown option: $1"
            exit 1



            ;; 
        esac
    done
}

execute_commands() {
    for ip in "${ips[@]}"; do
        echo "Running '$main_command' on $ip"
        # ssh root@"$ip" "$main_command" # Uncomment to execute
    done
    for cip in "${cips[@]}"; do
        echo "Running '$cmain_command' on $cip"
        # ssh root@"$ip" "$cmain_command" # Uncomment to execute
    done
}

process_arguments "$@"
execute_commands