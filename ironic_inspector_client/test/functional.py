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

import unittest

from ironic_inspector.test import functional

import ironic_inspector_client as client


class TestV1PythonAPI(functional.Base):
    def setUp(self):
        super(TestV1PythonAPI, self).setUp()
        self.client = client.ClientV1()

    def test_introspect_get_status(self):
        self.client.introspect(self.uuid)
        eventlet.greenthread.sleep(functional.DEFAULT_SLEEP)
        self.cli.node.set_power_state.assert_called_once_with(self.uuid,
                                                              'reboot')

        status = self.client.get_status(self.uuid)
        self.assertEqual({'finished': False, 'error': None}, status)

        res = self.call_continue(self.data)
        self.assertEqual({'uuid': self.uuid}, res)
        eventlet.greenthread.sleep(functional.DEFAULT_SLEEP)

        self.assertCalledWithPatch(self.patch, self.cli.node.update)
        self.cli.port.create.assert_called_once_with(
            node_uuid=self.uuid, address='11:22:33:44:55:66')

        status = self.client.get_status(self.uuid)
        self.assertEqual({'finished': True, 'error': None}, status)

    def test_setup_ipmi(self):
        self.node.maintenance = True
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
        self.assertEqual({'finished': False, 'error': None}, status)

        res = self.call_continue(self.data)
        self.assertEqual({'uuid': self.uuid}, res)
        eventlet.greenthread.sleep(functional.DEFAULT_SLEEP)

        self.assertCalledWithPatch(self.patch, self.cli.node.update)
        self.cli.port.create.assert_called_once_with(
            node_uuid=self.uuid, address='11:22:33:44:55:66')

        status = client.get_status(self.uuid)
        self.assertEqual({'finished': True, 'error': None}, status)

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


if __name__ == '__main__':
    with functional.mocked_server():
        unittest.main()
