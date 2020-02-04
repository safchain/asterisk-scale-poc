# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations


class Context:

    asterisk_id: str

    def __init__(self, asterisk_id: str) -> None:
        self.asterisk_id = asterisk_id
