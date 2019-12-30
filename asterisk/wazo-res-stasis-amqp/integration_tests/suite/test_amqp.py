# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import ari as ari_client
import logging
import os
import pytest
from hamcrest import (
    assert_that,
    calling,
    empty,
    has_entry,
    has_item,
    is_not,
    not_,
    only_contains,
)
from xivo_test_helpers import until
from xivo_test_helpers.bus import BusClient
from xivo_test_helpers.asset_launching_test_case import AssetLaunchingTestCase
from xivo_test_helpers.hamcrest.raises import raises

log_level = logging.DEBUG if os.environ.get('TEST_LOGS') == 'verbose' else logging.INFO
logging.basicConfig(level=log_level)

app_name_key = 'applicationName'

subscribe_args = {app_name_key: 'newstasisapplication'}


class AssetLauncher(AssetLaunchingTestCase):

    assets_root = os.path.join(os.path.dirname(__file__), '..', 'assets')
    asset = 'amqp'
    service = 'ari_amqp'


@pytest.fixture()
def ari():
    AssetLauncher.kill_containers()
    AssetLauncher.rm_containers()
    AssetLauncher.launch_service_with_asset()
    ari_url = 'http://localhost:{port}'.format(port=AssetLauncher.service_port(5039, 'ari_amqp'))
    client = until.return_(ari_client.connect, ari_url, 'wazo', 'wazo', timeout=5, interval=0.1)

    # necessary because RabbitMQ starts much more slowly, so module fails to load automatically
    AssetLauncher.docker_exec(
        ['asterisk', '-rx', 'module load res_stasis_amqp.so'], service_name='ari_amqp',
    )
    AssetLauncher.docker_exec(
        ['asterisk', '-rx', 'module load res_ari_amqp.so'], service_name='ari_amqp',
    )

    yield client
    AssetLauncher.kill_containers()


def test_stasis_amqp_events(ari):
    real_app = 'A'
    parasite_app = 'B'
    ari.amqp.stasisSubscribe(applicationName=real_app)
    ari.amqp.stasisSubscribe(applicationName=parasite_app)

    assert_that(ari.applications.list(), has_item(has_entry('name', real_app)))
    assert_that(ari.applications.list(), has_item(has_entry('name', parasite_app)))

    bus_client = BusClient.from_connection_fields(port=AssetLauncher.service_port(5672, 'rabbitmq'))

    assert bus_client.is_up()

    events = bus_client.accumulator("stasis.app." + real_app.lower())
    parasite_events = bus_client.accumulator("stasis.app." + parasite_app.lower())

    ari.channels.originate(endpoint='local/3000@default', app=real_app)
    ari.channels.originate(endpoint='local/3000@default', app=parasite_app)

    def event_received(events, app):
        assert_that(events.accumulate(), only_contains(
            has_entry('application', app)
        ))

        assert_that(parasite_events.accumulate(), only_contains(
            has_entry('application', is_not(app))
        ))

    until.assert_(event_received, events, real_app, timeout=5)

    def event_received(events, app):
        assert_that(events.accumulate(), only_contains(
            has_entry('application', app)
        ))

        assert_that(parasite_events.accumulate(), only_contains(
            has_entry('application', is_not(app))
        ))

    until.assert_(event_received, events, real_app, timeout=5)


def test_stasis_amqp_events_bad_routing(ari):
    real_app = 'A'
    parasite_app = 'B'
    ari.amqp.stasisSubscribe(applicationName=real_app)
    ari.amqp.stasisSubscribe(applicationName=parasite_app)

    bus_client = BusClient.from_connection_fields(port=AssetLauncher.service_port(5672, 'rabbitmq'))

    assert bus_client.is_up()

    events = bus_client.accumulator("stasis.app." + parasite_app.lower())

    ari.channels.originate(endpoint='local/3000@default', app=real_app.lower())

    def event_received(events, app):
        assert_that(events.accumulate(), empty())

    until.assert_(event_received, events, subscribe_args[app_name_key], timeout=5)


def test_app_subscribe(ari):
    assert_that(
        calling(ari.amqp.stasisSubscribe).with_args(**subscribe_args),
        not_(raises(Exception))
    )

    assert_that(ari.applications.list(), has_item(has_entry('name', subscribe_args[app_name_key])))


@pytest.mark.skip(reason='not implemented')
def test_app_unsubscribe(ari):
    """
    Test passes, but operation does not work for now; a tiny Asterisk patch is required.
    """
    ari.amqp.stasisSubscribe(**subscribe_args)
    assert_that(
        calling(ari.amqp.stasisUnsubscribe).with_args(**subscribe_args),
        not_(raises(Exception))
    )
