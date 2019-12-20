consul {
  address = "consul:8500"
}

template {
  source = "/config/kamailio.ctmpl"
  destination  = "/etc/kamailio/dispatcher.list"
  command = "/config/reload.sh"
}
