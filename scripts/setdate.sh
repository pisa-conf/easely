#! /bin/bash

for x in $@
do
    ip=$((100 + x))
    echo "setting date on on ppm$x"
    ssh pi@192.168.30.$ip "sudo date -s '2022-05-22 08:01:30'; exit;";
done



