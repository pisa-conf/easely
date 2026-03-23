#! /bin/bash

for x in $@
do
    ip=$((100 + x))
    echo "copying file to ppm$x"

    scp scp.sh pi@192.168.30.$ip:
done



