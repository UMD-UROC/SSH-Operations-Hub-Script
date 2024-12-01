# Initialize an array to store allowed inputs
allowed_ips=(1 3 4 5 6 7 8 9 10 15 17 20 21 22 23 24 25) # Store allowed inputs
ips_inputed=() # Store raw input
ips_parsed=() # Store parsed input

# Parse options
while [[ $# -gt 0 ]]; do
    case $1 in
    -ip)
        shift
        while [[ $# -gt 0 && $1 != -* ]]; do
            if [[ " ${allowed_ips[@]} " =~ " $1 " ]]; then
                ip="10.200.142.$1"
                # Add remove duplicate IPs
                if [[ ! " ${ips_parsed[@]} " =~ " $ip " ]]; then
                    ips_parsed+=("$ip")
                fi
            else
                echo "Error: IP address 10.200.142.$1 isn't allowed"
                exit 1
            fi
            shift
        done
        ;;
    *)
        echo "Unknown option: $1"
        exit 1
        ;;
    esac
done

# Output the collected IPs
echo "Collected IPs: ${ips_parsed[@]}"