#!/bin/sh	

/usr/sbin/kamailio -DDD

# wait until dispatcher ready
until kamctl dispatcher dump 2>/dev/null; do
    sleep 1
done

consul-template -log-level debug -config /config/template.hcl