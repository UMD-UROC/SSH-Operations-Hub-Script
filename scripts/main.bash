# Allow script to run with errors
set +e

# Initialize arrays
allowed_ips=(1 3 4 5 6 7 8 9 10 15 17 20 21 22 23 24 25)
custom_ips_parsed=()
ips_parsed=()

run_command() {
    local host="$1"
    local command="$2"
    echo "Running command '$command' on: $host"
    ssh user@"$host" "$command" || echo "Failed to execute $command on $host"
}

parse_ips() {
    local ips_var="$1[@]"
    shift
    local ip_list=()

    while [[ $# -gt 0 && $1 != -* ]]; do
        if [[ " ${allowed_ips[*]} " == *" $1 "* ]]; then
            ip="10.200.142.$1"
            [[ ! " ${!ips_var} " == *" $ip "* ]] && ip_list+=("$ip")
        else
            echo "Error: IP address 10.200.142.$1 isn't valid"
            exit 1
        fi
        shift
    done
    printf -v "$1" '%s' "${ip_list[@]}"
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -ip) # IP Adress
            shift
            parse_ips ips_parsed "$@"
            shift $(( $# - ${#ips_parsed[@]} ))
            ;;
        -cmd) # Pass command through
            shift
            command_provided="$1"
            shift
            ;;
        -cipcmd) # Custom IP adress command
            shift
            parse_ips custom_ips_parsed "$@"
            shift $(( $# - ${#custom_ips_parsed[@]} ))
            custom_command_provided="$1"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

for ip in "${ips_parsed[@]}"; do
    run_command "$ip" "$command_provided"
done

for ip in "${custom_ips_parsed[@]}"; do
    run_command "$ip" "$custom_command_provided"
done