consul = "consul:8500"
token = "a2698ad707066238727de8d3eb7439a5adc459a6638d5b89135751232d34069d"

template {
  source = "/config/ha-proxy.ctmpl"
  destination  = "/usr/local/etc/haproxy/"
  command = "pkill -9 haproxy ; haproxy -f /usr/local/etc/haproxy/haproxy.cfg"
}
