#!/bin/bash
sleep 3
# Delay to ensure the network is ready
# Set the display variable
export DISPLAY=:0
# Run the Python file
#/home/admin/Downloads/myTeacher/kiosk.sh &
lxterminal -e bash -c "/home/admin/Downloads/myTeacher/aidesktopmode/choose_mode.sh; exec bash" &

sleep 5

# Get the current IP address (using a delay to ensure network connection is stable)
IP_ADDRESS=$(hostname -I | awk '{print $1}')

# Check if the IP address was successfully retrieved
if [ -z "$IP_ADDRESS" ]; then
    echo "Could not retrieve IP address."
    exit 1
fi
pkill chromium-browser

# Open Chromium in kiosk mode with the URL
chromium --kiosk "http://$IP_ADDRESS:5010" &
