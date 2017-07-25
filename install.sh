#!/bin/sh

locationOfScript=$(dirname "$(readlink -e "$0")")

sed -i "s|INSTDIR=.*|INSTDIR=$locationOfScript|" homematicBot.sh
sed -i "s|INSTDIR=.*|INSTDIR=$locationOfScript|" homematicBot

cp homematicBot /etc/init.d/homematicBot
chmod +x /etc/init.d/homematicBot
chown root:root /etc/init.d/homematicBot
update-rc.d homematicBot defaults
