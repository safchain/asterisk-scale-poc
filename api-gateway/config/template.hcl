consul {
  address = "consul:8500"
}

template {
  source = "/config/nginx.ctmpl"
  destination  = "/etc/nginx/conf.d/lb.conf"
  perms = 0600
  command = "nginx -s reload"
}
