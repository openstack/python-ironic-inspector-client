# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import eventlet
eventlet.monkey_patch()

import copy
import json
import mock
import os
import sys
import tempfile
import unittest

from ironic_inspector.common import swift
from ironic_inspector import introspection_state as istate
from ironic_inspector.test import functional
from oslo_concurrency import processutils

import ironic_inspector_client as client
from ironic_inspector_client.common import http
from ironic_inspector_client import shell


class TestV1PythonAPI(functional.Base):
    def setUp(self):
        super(TestV1PythonAPI, self).setUp()
        self.client = client.ClientV1()
        functional.cfg.CONF.set_override('store_data', 'none', 'processing')

    def my_status_index(self, statuses):
        my_status = self._fake_status()
        return statuses.index(my_status)

    def test_introspect_get_status(self):
        self.client.introspect(self.uuid)
        eventlet.greenthread.sleep(functional.DEFAULT_SLEEP)
        self.cli.node.set_power_state.assert_called_once_with(self.uuid,
                                                              'reboot')

        status = self.client.get_status(self.uuid)
        self.check_status(status, finished=False, state=istate.States.waiting)

        res = self.call_continue(self.data)
        self.assertEqual({'uuid': self.uuid}, res)
        eventlet.greenthread.sleep(functional.DEFAULT_SLEEP)

        self.assertCalledWithPatch(self.patch, self.cli.node.update)
        self.cli.port.create.assert_called_once_with(
            node_uuid=self.uuid, address='11:22:33:44:55:66',
            pxe_enabled=True, extra={})

        status = self.client.get_status(self.uuid)
        self.check_status(status, finished=True, state=istate.States.finished)

    def test_introspect_list_statuses(self):
        self.client.introspect(self.uuid)
        eventlet.greenthread.sleep(functional.DEFAULT_SLEEP)
        self.cli.node.set_power_state.assert_called_once_with(self.uuid,
                                                              'reboot')

        statuses = self.client.list_statuses()
        my_status = statuses[self.my_status_index(statuses)]
        self.check_status(my_status, finished=False,
                          state=istate.States.waiting)

        res = self.call_continue(self.data)
        self.assertEqual({'uuid': self.uuid}, res)
        eventlet.greenthread.sleep(functional.DEFAULT_SLEEP)

        self.assertCalledWithPatch(self.patch, self.cli.node.update)
        self.cli.port.create.assert_called_once_with(
            node_uuid=self.uuid, address='11:22:33:44:55:66',
            pxe_enabled=True, extra={})

        statuses = self.client.list_statuses()
        my_status = statuses[self.my_status_index(statuses)]
        self.check_status(my_status, finished=True,
                          state=istate.States.finished)

    def test_wait_for_finish(self):
        shared = [0]  # mutable structure to hold number of retries

        def fake_waiter(delay):
            shared[0] += 1
            if shared[0] == 2:
                # On the second wait simulate data arriving
                res = self.call_continue(self.data)
                self.assertEqual({'uuid': self.uuid}, res)
            elif shared[0] > 2:
                # Just wait afterwards
                eventlet.greenthread.sleep(delay)

        self.client.introspect(self.uuid)
        eventlet.greenthread.sleep(functional.DEFAULT_SLEEP)

        status = self.client.get_status(self.uuid)
        self.check_status(status, finished=False, state=istate.States.waiting)

        self.client.wait_for_finish([self.uuid], sleep_function=fake_waiter,
                                    retry_interval=functional.DEFAULT_SLEEP)

        status = self.client.get_status(self.uuid)
        self.check_status(status, finished=True, state=istate.States.finished)

    @mock.patch.object(swift, 'store_introspection_data', autospec=True)
    @mock.patch.object(swift, 'get_introspection_data', autospec=True)
    def test_reprocess_stored_introspection_data(self, get_mock,
                                                 store_mock):
        functional.cfg.CONF.set_override('store_data', 'swift', 'processing')
        port_create_call = mock.call(node_uuid=self.uuid,
                                     address='11:22:33:44:55:66',
                                     pxe_enabled=True, extra={})
        get_mock.return_value = json.dumps(self.data)

        # assert reprocessing doesn't work before introspection
        self.assertRaises(client.ClientError, self.client.reprocess,
                          self.uuid)

        self.client.introspect(self.uuid)
        eventlet.greenthread.sleep(functional.DEFAULT_SLEEP)
        self.cli.node.set_power_state.assert_called_once_with(self.uuid,
                                                              'reboot')
        status = self.client.get_status(self.uuid)
        self.check_status(status, finished=False, state=istate.States.waiting)

        res = self.call_continue(self.data)
        self.assertEqual({'uuid': self.uuid}, res)
        eventlet.greenthread.sleep(functional.DEFAULT_SLEEP)

        status = self.client.get_status(self.uuid)
        self.check_status(status, finished=True, state=istate.States.finished)
        self.cli.port.create.assert_has_calls([port_create_call],
                                              any_order=True)
        self.assertFalse(get_mock.called)
        self.assertTrue(store_mock.called)

        res = self.client.reprocess(self.uuid)
        self.assertEqual(202, res.status_code)
        self.assertEqual('', res.text)
        eventlet.greenthread.sleep(functional.DEFAULT_SLEEP)
        self.check_status(status, finished=True, state=istate.States.finished)

        self.cli.port.create.assert_has_calls([port_create_call,
                                               port_create_call],
                                              any_order=True)
        self.assertTrue(get_mock.called)
        # incoming, processing, reapplying data
        self.assertEqual(3, store_mock.call_count)

    def test_abort_introspection(self):
        # assert abort doesn't work before introspect request
        self.assertRaises(client.ClientError, self.client.abort,
                          self.uuid)

        self.client.introspect(self.uuid)
        eventlet.greenthread.sleep(functional.DEFAULT_SLEEP)
        self.cli.node.set_power_state.assert_called_once_with(self.uuid,
                                                              'reboot')

        status = self.client.get_status(self.uuid)
        self.check_status(status, finished=False, state=istate.States.waiting)

        res = self.client.abort(self.uuid)
        eventlet.greenthread.sleep(functional.DEFAULT_SLEEP)

        self.assertEqual(202, res.status_code)
        self.assertEqual('', res.text)

        status = self.client.get_status(self.uuid)
        self.check_status(status, finished=True, state=istate.States.error,
                          error='Canceled by operator')

        # assert continue doesn't work after abort
        self.call_continue(self.data, expect_error=400)

    def test_setup_ipmi(self):
        self.node.provision_state = 'enroll'
        self.client.introspect(self.uuid, new_ipmi_username='admin',
                               new_ipmi_password='pwd')
        eventlet.greenthread.sleep(functional.DEFAULT_SLEEP)
        self.assertFalse(self.cli.node.set_power_state.called)

        res = self.call_continue(self.data)
        self.assertEqual('admin', res['ipmi_username'])
        self.assertEqual('pwd', res['ipmi_password'])
        self.assertTrue(res['ipmi_setup_credentials'])

    def test_api_versions(self):
        minv, maxv = self.client.server_api_versions()
        self.assertEqual((1, 0), minv)
        self.assertGreaterEqual(maxv, (1, 0))
        self.assertLess(maxv, (2, 0))

    def test_client_init(self):
        self.assertRaises(client.VersionNotSupported,
                          client.ClientV1, api_version=(1, 999))
        self.assertRaises(client.VersionNotSupported,
                          client.ClientV1, api_version=2)

        self.assertTrue(client.ClientV1(api_version=1).server_api_versions())
        self.assertTrue(client.ClientV1(api_version='1.0')
                        .server_api_versions())
        self.assertTrue(client.ClientV1(api_version=(1, 0))
                        .server_api_versions())

        self.assertTrue(
            client.ClientV1(inspector_url='http://127.0.0.1:5050')
            .server_api_versions())
        self.assertTrue(
            client.ClientV1(inspector_url='http://127.0.0.1:5050/v1')
            .server_api_versions())

        self.assertTrue(client.ClientV1(auth_token='some token')
                        .server_api_versions())

    def test_rules_api(self):
        res = self.client.rules.get_all()
        self.assertEqual([], res)

        rule = {'conditions': [],
                'actions': [{'action': 'fail', 'message': 'boom'}],
                'description': 'Cool actions',
                'uuid': self.uuid}
        res = self.client.rules.from_json(rule)
        self.assertEqual(self.uuid, res['uuid'])
        rule['links'] = res['links']
        self.assertEqual(rule, res)

        res = self.client.rules.get(self.uuid)
        self.assertEqual(rule, res)

        res = self.client.rules.get_all()
        self.assertEqual(rule['links'], res[0].pop('links'))
        self.assertEqual([{'uuid': self.uuid,
                           'description': 'Cool actions'}],
                         res)

        self.client.rules.delete(self.uuid)
        res = self.client.rules.get_all()
        self.assertEqual([], res)

        for _ in range(3):
            res = self.client.rules.create(conditions=rule['conditions'],
                                           actions=rule['actions'],
                                           description=rule['description'])
            self.assertTrue(res['uuid'])
            for key in ('conditions', 'actions', 'description'):
                self.assertEqual(rule[key], res[key])

        res = self.client.rules.get_all()
        self.assertEqual(3, len(res))

        self.client.rules.delete_all()
        res = self.client.rules.get_all()
        self.assertEqual([], res)

        self.assertRaises(client.ClientError, self.client.rules.get,
                          self.uuid)
        self.assertRaises(client.ClientError, self.client.rules.delete,
                          self.uuid)


class TestSimplePythonAPI(functional.Base):
    def test_introspect_get_status(self):
        client.introspect(self.uuid)
        eventlet.greenthread.sleep(functional.DEFAULT_SLEEP)
        self.cli.node.set_power_state.assert_called_once_with(self.uuid,
                                                              'reboot')

        status = client.get_status(self.uuid)
        self.check_status(status, finished=False, state=istate.States.waiting)

        res = self.call_continue(self.data)
        self.assertEqual({'uuid': self.uuid}, res)
        eventlet.greenthread.sleep(functional.DEFAULT_SLEEP)

        self.assertCalledWithPatch(self.patch, self.cli.node.update)
        self.cli.port.create.assert_called_once_with(
            node_uuid=self.uuid, address='11:22:33:44:55:66',
            pxe_enabled=True, extra={})

        status = client.get_status(self.uuid)
        self.check_status(status, finished=True, state=istate.States.finished)

    def test_api_versions(self):
        minv, maxv = client.server_api_versions()
        self.assertEqual((1, 0), minv)
        self.assertGreaterEqual(maxv, (1, 0))
        self.assertLess(maxv, (2, 0))

        self.assertRaises(client.VersionNotSupported,
                          client.introspect, self.uuid, api_version=(1, 999))
        self.assertRaises(client.VersionNotSupported,
                          client.get_status, self.uuid, api_version=(1, 999))
        # Error 404
        self.assertRaises(client.ClientError,
                          client.get_status, self.uuid, api_version=(1, 0))


BASE_CMD = [os.path.join(sys.prefix, 'bin', 'openstack'),
            '--os-auth-type', 'token_endpoint', '--os-token', 'fake',
            '--os-url', 'http://127.0.0.1:5050']


class BaseCLITest(functional.Base):
    def openstack(self, cmd, expect_error=False, parse_json=False):
        real_cmd = BASE_CMD + cmd
        if parse_json:
            real_cmd += ['-f', 'json']
        try:
            out, _err = processutils.execute(*real_cmd)
        except processutils.ProcessExecutionError as exc:
            if expect_error:
                return exc.stderr
            else:
                raise
        else:
            if expect_error:
                raise AssertionError('Command %s returned unexpected success' %
                                     cmd)
            elif parse_json:
                return json.loads(out)
            else:
                return out

    def run_cli(self, *cmd, **kwargs):
        return self.openstack(['baremetal', 'introspection'] + list(cmd),
                              **kwargs)


class TestCLI(BaseCLITest):
    def setup_lldp(self):
        functional.cfg.CONF.set_override('store_data', 'swift', 'processing')

        self.all_interfaces = {
            'eth1': {'mac': self.macs[0], 'ip': self.ips[0],
                     'client_id': None, 'lldp_processed':
                         {'switch_chassis_id': "11:22:33:aa:bb:cc",
                          'switch_port_vlans':
                          [{"name": "vlan101", "id": 101},
                           {"name": "vlan102", "id": 102},
                           {"name": "vlan104", "id": 104},
                           {"name": "vlan201", "id": 201},
                           {"name": "vlan203", "id": 203}],
                          'switch_port_id': "554",
                          'switch_port_mtu': 1514}},
            'eth3': {'mac': self.macs[1], 'ip': None,
                     'client_id': None, 'lldp_processed':
                         {'switch_chassis_id': "11:22:33:aa:bb:cc",
                          'switch_port_vlans':
                          [{"name": "vlan101", "id": 101},
                           {"name": "vlan102", "id": 102},
                           {"name": "vlan104", "id": 106}],
                          'switch_port_id': "557",
                          'switch_port_mtu': 9216}}
        }

        self.data['all_interfaces'] = self.all_interfaces

    def _fake_status(self, **kwargs):
        # to remove the hidden fields
        hidden_status_items = shell.StatusCommand.hidden_status_items
        fake_status = super(TestCLI, self)._fake_status(**kwargs)
        fake_status = dict(item for item in fake_status.items()
                           if item[0] not in hidden_status_items)
        return fake_status

    def test_cli_negative(self):
        err = self.run_cli('start', expect_error=True)
        self.assertIn('too few arguments', err)
        err = self.run_cli('status', expect_error=True)
        self.assertIn('too few arguments', err)
        err = self.run_cli('start', 'uuid', '--new-ipmi-username', 'user',
                           expect_error=True)
        self.assertIn('requires a new password', err)
        err = self.run_cli('rule', 'show', 'uuid', expect_error=True)
        self.assertIn('not found', err)
        err = self.run_cli('rule', 'delete', 'uuid', expect_error=True)
        self.assertIn('not found', err)

        err = self.run_cli('interface', 'list', expect_error=True)
        self.assertIn('too few arguments', err)

    def test_introspect_get_status(self):
        self.run_cli('start', self.uuid)
        eventlet.greenthread.sleep(functional.DEFAULT_SLEEP)
        self.cli.node.set_power_state.assert_called_once_with(self.uuid,
                                                              'reboot')

        status = self.run_cli('status', self.uuid, parse_json=True)
        self.check_status(status, finished=False, state=istate.States.waiting)

        res = self.call_continue(self.data)
        self.assertEqual({'uuid': self.uuid}, res)
        eventlet.greenthread.sleep(functional.DEFAULT_SLEEP)

        self.assertCalledWithPatch(self.patch, self.cli.node.update)
        self.cli.port.create.assert_called_once_with(
            node_uuid=self.uuid, address='11:22:33:44:55:66',
            pxe_enabled=True, extra={})

        status = self.run_cli('status', self.uuid, parse_json=True)
        self.check_status(status, finished=True, state=istate.States.finished)

    def test_rules_api(self):
        res = self.run_cli('rule', 'list', parse_json=True)
        self.assertEqual([], res)

        rule = {'conditions': [],
                'actions': [{'action': 'fail', 'message': 'boom'}],
                'description': 'Cool actions',
                'uuid': self.uuid}
        with tempfile.NamedTemporaryFile() as fp:
            json.dump(rule, fp)
            fp.flush()
            res = self.run_cli('rule', 'import', fp.name, parse_json=True)

        self.assertEqual([{'UUID': self.uuid, 'Description': 'Cool actions'}],
                         res)

        res = self.run_cli('rule', 'show', self.uuid, parse_json=True)
        self.assertEqual(rule, res)

        res = self.run_cli('rule', 'list', parse_json=True)
        self.assertEqual([{'UUID': self.uuid,
                           'Description': 'Cool actions'}],
                         res)

        self.run_cli('rule', 'delete', self.uuid)
        res = self.run_cli('rule', 'list', parse_json=True)
        self.assertEqual([], res)

        with tempfile.NamedTemporaryFile() as fp:
            rule.pop('uuid')
            json.dump([rule, rule], fp)
            fp.flush()
            res = self.run_cli('rule', 'import', fp.name, parse_json=True)

        self.run_cli('rule', 'purge')
        res = self.run_cli('rule', 'list', parse_json=True)
        self.assertEqual([], res)

    @mock.patch.object(swift, 'get_introspection_data', autospec=True)
    def test_interface_list(self, get_mock):
        self.setup_lldp()
        get_mock.return_value = json.dumps(copy.deepcopy(self.data))

        expected_eth1 = {u'Interface': u'eth1',
                         u'MAC Address': u'11:22:33:44:55:66',
                         u'Switch Chassis ID': u'11:22:33:aa:bb:cc',
                         u'Switch Port ID': u'554',
                         u'Switch Port VLAN IDs': [101, 102, 104, 201, 203]}
        expected_eth3 = {u'Interface': u'eth3',
                         u'MAC Address': u'66:55:44:33:22:11',
                         u'Switch Chassis ID': u'11:22:33:aa:bb:cc',
                         u'Switch Port ID': u'557',
                         u'Switch Port VLAN IDs': [101, 102, 106]}

        res = self.run_cli('interface', 'list', self.uuid, parse_json=True)
        res.sort()
        self.assertEqual(expected_eth1, res[0])
        self.assertEqual(expected_eth3, res[1])

        # Filter on vlan
        res = self.run_cli('interface', 'list', self.uuid, '--vlan', '106',
                           parse_json=True)
        res.sort()
        self.assertEqual(expected_eth3, res[0])

        # Select fields
        res = self.run_cli('interface', 'list', self.uuid, '--fields',
                           'switch_port_mtu',
                           parse_json=True)
        res.sort()
        self.assertEqual({u'Switch Port MTU': 1514}, res[0])
        self.assertEqual({u'Switch Port MTU': 9216}, res[1])

    @mock.patch.object(swift, 'get_introspection_data', autospec=True)
    def test_interface_show(self, get_mock):
        self.setup_lldp()
        get_mock.return_value = json.dumps(copy.deepcopy(self.data))

        res = self.run_cli('interface', 'show', self.uuid, "eth1",
                           parse_json=True)

        expected = {u'interface': u'eth1',
                    u'mac': u'11:22:33:44:55:66',
                    u'switch_chassis_id': u'11:22:33:aa:bb:cc',
                    u'switch_port_id': u'554',
                    u'switch_port_mtu': 1514,
                    u'switch_port_vlan_ids': [101, 102, 104, 201, 203],
                    u'switch_port_vlans': [{u'id': 101, u'name': u'vlan101'},
                                           {u'id': 102, u'name': u'vlan102'},
                                           {u'id': 104, u'name': u'vlan104'},
                                           {u'id': 201, u'name': u'vlan201'},
                                           {u'id': 203, u'name': u'vlan203'}]}

        self.assertDictContainsSubset(expected, res)

if __name__ == '__main__':
    with functional.mocked_server():
        # Make links predictable
        http._DEFAULT_URL = 'http://127.0.0.1:5050'
        unittest.main(verbosity=2)
