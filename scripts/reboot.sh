#! /bin/bash

for x in $@
do
    ip=$((100 + x))
    echo "rebooting ppm$x"
    ssh pi@192.168.30.$ip "sudo reboot now";
done



