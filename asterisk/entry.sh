#!/bin/sh	

# wait until consul ready
until curl -s http://consul:8500/v1/status/leader | jq -es .[0] 2>/dev/null; do
    sleep 1
done

/usr/sbin/asterisk -f