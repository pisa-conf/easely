#! /bin/bash

for x in $@
do
    ip=$((100 + x))
    echo "setting timezone on ppm$x"
    ssh pi@192.168.30.$ip "sudo timedatectl set-timezone Europe/Rome; date";
done
