#!/bin/bash

[[ "$UID" -ne 0 ]] && {
    echo "Script must be run as root."
    exit 1
}

install_packages() {
    local distro
    distro=$(awk -F= '/^NAME/{print $2}' /etc/os-release)
    distro=${distro//\"/}
    
    case "$distro" in
        *"Ubuntu"* | *"Debian"*)
            apt-get update
            apt-get install -y curl tor jq
            ;;
        *"Fedora"* | *"CentOS"* | *"Red Hat"* | *"Amazon Linux"*)
            yum update
            yum install -y curl tor jq
            ;;
        *"Arch"*)
            pacman -S --noconfirm curl tor jq
            ;;
        *)
            echo "Unsupported distribution: $distro. Please install curl, tor and jq manually."
            exit 1
            ;;
    esac
}

if ! command -v curl &> /dev/null || ! command -v tor &> /dev/null || ! command -v jq &> /dev/null; then
    echo "Installing curl, tor and jq"
    install_packages
fi

if ! systemctl --quiet is-active tor.service; then
    echo "Starting tor service"
    systemctl start tor.service
fi

get_ip() {
    local url get_ip ip
    url="https://checkip.amazonaws.com"
    get_ip=$(curl -s -x socks5h://127.0.0.1:9050 "$url")
    ip=$(echo "$get_ip" | grep -oP '\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}')
    echo "$ip"
}

get_country() {
    local ip=$1
    local country_info
    country_info=$(curl -s -x socks5h://127.0.0.1:9050 "https://ipinfo.io/$ip/country")
    if [ -n "$country_info" ]; then
        echo "$country_info"
    else
        echo "Unknown"
    fi
}

change_ip() {
    echo "Reloading tor service"
    systemctl reload tor.service
    
    local ip
    ip=$(get_ip)
    local country
    country=$(get_country "$ip")
    
    # Array kata-kata random
    phrases=("Aku sekarang bukan aku. Aku adalah..." "Selamat, Geger anda sudah berpindah" 
             "Koneksi diamankan. Dipagari kawat berduri, ditambah satpam galak" "GPS jaringan nyasar, tapi tenang... sekarang lewat jalan tikus digital!" "He ASSUUU Pindah lagi ke" 
             "Sudah tidak dapat di track " "Ngopi sek" "Sopo iki")
    
    # Pilih random phrase
    local random_phrase
    random_phrase=${phrases[$RANDOM % ${#phrases[@]}]}
    
    echo -e "\033[34m$random_phrase : $ip\033[0m"
    echo -e "\033[34mCountry of origin : $country\033[0m"
    echo ""
}

clear
cat << EOF
██╗██████╗      ██████╗██╗  ██╗ █████╗ ███╗   ██╗ ██████╗ ███████╗██████╗              
██║██╔══██╗    ██╔════╝██║  ██║██╔══██╗████╗  ██║██╔════╝ ██╔════╝██╔══██╗             
██║██████╔╝    ██║     ███████║███████║██╔██╗ ██║██║  ███╗█████╗  ██████╔╝             
██║██╔═══╝     ██║     ██╔══██║██╔══██║██║╚██╗██║██║   ██║██╔══╝  ██╔══██╗             
██║██║         ╚██████╗██║  ██║██║  ██║██║ ╚████║╚██████╔╝███████╗██║  ██║             
╚═╝╚═╝          ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝
by :             
                                                                                       
██╗    ██╗██╗  ██╗██╗████████╗███████╗    ██╗  ██╗ ██████╗  ██████╗ ██████╗ ██╗███████╗
██║    ██║██║  ██║██║╚══██╔══╝██╔════╝    ██║  ██║██╔═══██╗██╔═══██╗██╔══██╗██║██╔════╝
██║ █╗ ██║███████║██║   ██║   █████╗      ███████║██║   ██║██║   ██║██║  ██║██║█████╗  
██║███╗██║██╔══██║██║   ██║   ██╔══╝      ██╔══██║██║   ██║██║   ██║██║  ██║██║██╔══╝  
╚███╔███╔╝██║  ██║██║   ██║   ███████╗    ██║  ██║╚██████╔╝╚██████╔╝██████╔╝██║███████╗
 ╚══╝╚══╝ ╚═╝  ╚═╝╚═╝   ╚═╝   ╚══════╝    ╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚═════╝ ╚═╝╚══════╝
 the emptiness machine
                                                                                       
                                                                                           
EOF

while true; do
    read -rp $'\033[34mSelect interval mode: (1) Fixed, (2) Random: \033[0m' interval_mode
    
    if [ "$interval_mode" -eq 1 ]; then
        read -rp $'\033[34mEnter time interval in seconds: \033[0m' interval
        break
    elif [ "$interval_mode" -eq 2 ]; then
        read -rp $'\033[34mEnter minimum time interval in seconds: \033[0m' min_interval
        read -rp $'\033[34mEnter maximum time interval in seconds: \033[0m' max_interval
        
        if [ "$min_interval" -gt "$max_interval" ]; then
            echo "Minimum interval cannot be greater than maximum interval. Please try again."
        else
            break
        fi
    else
        echo "Invalid selection. Please choose 1 or 2."
    fi
done

read -rp $'\033[34mEnter number of times to change IP address (type 0 for infinite IP changes): \033[0m' times

if [ "$times" -eq 0 ]; then
    echo "Starting infinite IP changes"
    while true; do
        change_ip
        
        if [ "$interval_mode" -eq 1 ]; then
            sleep_duration="$interval"
        else
            sleep_duration=$(shuf -i "$min_interval-$max_interval" -n 1)
        fi
        
        sleep "$sleep_duration"
    done
else
    for ((i=0; i< times; i++)); do
        change_ip
        
        if [ "$i" -lt $((times-1)) ]; then
            if [ "$interval_mode" -eq 1 ]; then
                sleep_duration="$interval"
            else
                sleep_duration=$(shuf -i "$min_interval-$max_interval" -n 1)
            fi
            
            sleep "$sleep_duration"
        fi
    done
fi