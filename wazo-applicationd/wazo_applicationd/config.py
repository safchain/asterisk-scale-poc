# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import os
import yaml


class Config:

    host: str
    port: int

    api_endpoint: str
    api_username: str
    api_password: str

    amqp_host: str
    amqp_port: int
    amqp_username: str
    amqp_password: str
    amqp_exchange: str
    amqp_reconnection_rate: int

    consul_host: str
    consul_port: int

    def __init__(self) -> None:
        self.host = os.environ.get('APP_HOST', '127.0.0.1')
        self.port = int(os.environ.get('APP_PORT', '8000'))

        self.api_endpoint = os.environ.get(
            'API_ENDPOINT', 'http://localhost:8088')
        self.api_username = os.environ.get('API_USERNAME', 'wazo')
        self.api_password = os.environ.get('API_PASSWORD', 'wazo')

        self.amqp_host = os.environ.get('AMQP_HOST', '127.0.0.1')
        self.amqp_port = int(os.environ.get('AMQP_PORT', '5672'))
        self.amqp_username = os.environ.get('AMQP_USERNAME', 'guest')
        self.amqp_password = os.environ.get('AMQP_PASSWORD', 'guest')
        self.amqp_exchange = os.environ.get('AMQP_EXCHANGE', 'wazo')
        self.amqp_reconnection_rate = int(
            os.environ.get('AMQP_RECONNECTION_RATE', '1'))

        self.consul_host = os.environ.get('CONSUL_HOST', '127.0.0.1')
        self.consul_port = int(os.environ.get('CONSUL_PORT', '8500'))

    def from_file(self, file: str = "app.yml") -> None:
        doc = {}
        if os.path.isfile(file):
            with open(file) as f:
                doc = yaml.load(f, Loader=yaml.FullLoader)

        self.host = doc.get('address', self.host)
        self.port = doc.get('port', self.port)

        amqp = doc.get('amqp')
        if amqp:
            self.amqp_host = amqp.get('host')
            self.amqp_port = amqp.get('port')
            self.amqp_username = amqp.get('username')
            self.amqp_password = amqp.get('password')
            self.amqp_exchange = amqp.get('exchange')

        consul = doc.get('consul')
        if consul:
            self.consul_host = consul.get('host')
            self.consul_port = consul.get('port')
