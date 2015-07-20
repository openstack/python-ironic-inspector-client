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

from ironic_inspector_client import client


class TestPythonAPI(functional.Base):
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

        self.cli.node.update.assert_any_call(self.uuid, self.patch)
        self.cli.port.create.assert_called_once_with(
            node_uuid=self.uuid, address='11:22:33:44:55:66')

        status = client.get_status(self.uuid)
        self.assertEqual({'finished': True, 'error': None}, status)

    def test_setup_ipmi(self):
        self.node.maintenance = True
        client.introspect(self.uuid, new_ipmi_username='admin',
                          new_ipmi_password='pwd')
        eventlet.greenthread.sleep(functional.DEFAULT_SLEEP)
        self.assertFalse(self.cli.node.set_power_state.called)

        res = self.call_continue(self.data)
        self.assertEqual('admin', res['ipmi_username'])
        self.assertEqual('pwd', res['ipmi_password'])
        self.assertTrue(res['ipmi_setup_credentials'])

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
