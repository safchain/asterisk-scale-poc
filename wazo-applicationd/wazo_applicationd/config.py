# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import os
import yaml

from gila import Gila  # type: ignore


class Config(Gila):
    def __init__(self) -> None:
        super().__init__()

        self.set_env_prefix("WAZO")
        self.automatic_env()

        self.set_default("uuid", "1223456789")

        self.set_default("host", "127.0.0.1")
        self.set_default("port", "8000")

        self.set_default("healthcheck_url", "http://172.17.0.1:8000/status")

        self.set_default("api_endpoint", "http://localhost:8088")
        self.set_default("api_username", "wazo")
        self.set_default("api_password", "wazo")

        self.set_default("amqp_host", "127.0.0.1")
        self.set_default("amqp_port", "5672")
        self.set_default("amqp_username", "guest")
        self.set_default("amqp_password", "guest")
        self.set_default("amqp_exchange", "wazo")
        self.set_default("amqp_routing_key", "stasis.app.#")
        self.set_default("amqp_reconnection_rate", 1)

        self.set_default("consul_host", "127.0.0.1")
        self.set_default("consul_port", "8500")

        self.set_default("jwt_secret", "secret")

        self.set_default("debug", True)

    def load_file(self, filename: str) -> None:
        self.set_config_file(filename)
        self.read_in_config()

