#!/bin/sh

echo "Start" >> /tmp/log
/usr/bin/pkill -9 kamailio

echo "Kamilio" >> /tmp/log
/usr/sbin/kamailio 2>>/tmp/log