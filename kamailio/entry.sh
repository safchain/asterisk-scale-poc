#!/bin/sh	

/usr/sbin/kamailio

consul-template -log-level debug -config /config/template.hcl