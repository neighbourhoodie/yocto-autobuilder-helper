#!/bin/bash
{
if [ -f /mnt/tank/yocto/sstate-clean.lock ]; then
    echo "Already running a clean up. Exiting."
    exit 0
fi
}

touch /mnt/tank/yocto/sstate-clean.lock

# Track how much we delete and long it takes to do it on any given day
/usr/bin/time -ao /mnt/tank/yocto/sstate-matime.log du -chs /mnt/tank/yocto/sstate-to-remove/sstate >> /mnt/tank/yocto/sstate-matime.log
/usr/bin/time -ao /mnt/tank/yocto/sstate-matime.log rm -R /mnt/tank/yocto/sstate-to-remove/sstate

mv /mnt/tank/yocto/sstate-matime.log /mnt/tank/yocto/$(date +%Y%m%d)-sstate-matime.log

cd /mnt/tank/yocto
/usr/bin/find /mnt/tank/yocto/autobuilder/autobuilder.yoctoproject.org/pub/sstate \( -mtime +15 -a -atime +15 \) -type f \( -name '*.tar*' -o -name '*.tgz*' \) -print > /mnt/tank/yocto/sstate-matime.log

# Call out to a python program to move file while preserving the directory structure 
/usr/local/bin/python3 sstate-clean.py

# Exit and wait until next run for deletion
rm /mnt/tank/yocto/sstate-clean.lock
