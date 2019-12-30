consul {
  address = "consul:8500"
}

template {
  source = "/config/kamailio.ctmpl"
  destination  = "/etc/kamailio/dispatcher.list"
  command = "/bin/bash -c 'for i in 1 2 3 4 5; do if kamctl dispatcher reload | jq .error | grep code > /dev/null; then sleep 1; else exit 0; fi; done'"
}
