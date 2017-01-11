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

from collections import OrderedDict
import six
import unittest

from keystoneauth1 import session
import mock
from oslo_utils import netutils
from oslo_utils import uuidutils

import ironic_inspector_client
from ironic_inspector_client.common import http
from ironic_inspector_client import v1


FAKE_HEADERS = {
    http._MIN_VERSION_HEADER: '1.0',
    http._MAX_VERSION_HEADER: '1.9'
}


@mock.patch.object(session.Session, 'get',
                   return_value=mock.Mock(headers=FAKE_HEADERS,
                                          status_code=200))
class TestInit(unittest.TestCase):
    my_ip = 'http://' + netutils.get_my_ipv4() + ':5050'
    token = "token"

    def get_client(self, **kwargs):
        return ironic_inspector_client.ClientV1(auth_token=self.token,
                                                **kwargs)

    def test_ok(self, mock_get):
        self.get_client()
        mock_get.assert_called_once_with(self.my_ip, authenticated=False,
                                         raise_exc=False)

    def test_explicit_version(self, mock_get):
        self.get_client(api_version=(1, 2))
        self.get_client(api_version=1)
        self.get_client(api_version='1.3')

    def test_unsupported_version(self, mock_get):
        self.assertRaises(ironic_inspector_client.VersionNotSupported,
                          self.get_client, api_version=(1, 99))
        self.assertRaises(ironic_inspector_client.VersionNotSupported,
                          self.get_client, api_version=2)
        self.assertRaises(ironic_inspector_client.VersionNotSupported,
                          self.get_client, api_version='1.42')

    def test_explicit_url(self, mock_get):
        self.get_client(inspector_url='http://host:port')
        mock_get.assert_called_once_with('http://host:port',
                                         authenticated=False,
                                         raise_exc=False)


class BaseTest(unittest.TestCase):
    def setUp(self):
        super(BaseTest, self).setUp()
        self.uuid = uuidutils.generate_uuid()
        self.my_ip = 'http://' + netutils.get_my_ipv4() + ':5050'
        self.token = "token"

    @mock.patch.object(http.BaseClient, 'server_api_versions',
                       lambda self: ((1, 0), (1, 99)))
    def get_client(self, **kwargs):
        return ironic_inspector_client.ClientV1(auth_token=self.token,
                                                **kwargs)


@mock.patch.object(http.BaseClient, 'request')
class TestIntrospect(BaseTest):
    def test(self, mock_req):
        self.get_client().introspect(self.uuid)
        mock_req.assert_called_once_with(
            'post', '/introspection/%s' % self.uuid,
            params={'new_ipmi_username': None, 'new_ipmi_password': None})

    def test_invalid_input(self, mock_req):
        self.assertRaises(TypeError, self.get_client().introspect, 42)
        self.assertRaises(ValueError, self.get_client().introspect, 'uuid',
                          new_ipmi_username='user')

    def test_set_ipmi_credentials(self, mock_req):
        self.get_client().introspect(self.uuid,
                                     new_ipmi_password='p',
                                     new_ipmi_username='u')
        mock_req.assert_called_once_with(
            'post', '/introspection/%s' % self.uuid,
            params={'new_ipmi_username': 'u', 'new_ipmi_password': 'p'})


@mock.patch.object(http.BaseClient, 'request')
class TestReprocess(BaseTest):
    def test(self, mock_req):
        self.get_client().reprocess(self.uuid)
        mock_req.assert_called_once_with(
            'post',
            '/introspection/%s/data/unprocessed' % self.uuid
        )

    def test_invalid_input(self, mock_req):
        self.assertRaises(TypeError, self.get_client().reprocess, 42)
        self.assertFalse(mock_req.called)


@mock.patch.object(http.BaseClient, 'request')
class TestGetStatus(BaseTest):
    def test(self, mock_req):
        mock_req.return_value.json.return_value = 'json'

        self.get_client().get_status(self.uuid)

        mock_req.assert_called_once_with(
            'get', '/introspection/%s' % self.uuid)

    def test_invalid_input(self, _):
        self.assertRaises(TypeError, self.get_client().get_status, 42)


@mock.patch.object(http.BaseClient, 'request')
class TestListStatuses(BaseTest):
    def test_default(self, mock_req):
        mock_req.return_value.json.return_value = {
            'introspection': None
        }
        params = {
            'marker': None,
            'limit': None
        }
        self.get_client().list_statuses()
        mock_req.assert_called_once_with('get', '/introspection',
                                         params=params)

    def test_nondefault(self, mock_req):
        mock_req.return_value.json.return_value = {
            'introspection': None
        }
        params = {
            'marker': 'uuid',
            'limit': 42
        }
        self.get_client().list_statuses(**params)
        mock_req.assert_called_once_with('get', '/introspection',
                                         params=params)

    def test_invalid_marker(self, _):
        six.assertRaisesRegex(self, TypeError, 'Expected a string value.*',
                              self.get_client().list_statuses, marker=42)

    def test_invalid_limit(self, _):
        six.assertRaisesRegex(self, TypeError, 'Expected an integer.*',
                              self.get_client().list_statuses, limit='42')


@mock.patch.object(ironic_inspector_client.ClientV1, 'get_status',
                   autospec=True)
class TestWaitForFinish(BaseTest):
    def setUp(self):
        super(TestWaitForFinish, self).setUp()
        self.sleep = mock.Mock(spec=[])

    def test_ok(self, mock_get_st):
        mock_get_st.side_effect = (
            [{'finished': False, 'error': None}] * 5
            + [{'finished': True, 'error': None}]
        )

        res = self.get_client().wait_for_finish(['uuid1'],
                                                sleep_function=self.sleep)
        self.assertEqual({'uuid1': {'finished': True, 'error': None}},
                         res)
        self.sleep.assert_called_with(v1.DEFAULT_RETRY_INTERVAL)
        self.assertEqual(5, self.sleep.call_count)

    def test_timeout(self, mock_get_st):
        mock_get_st.return_value = {'finished': False, 'error': None}

        self.assertRaises(v1.WaitTimeoutError,
                          self.get_client().wait_for_finish,
                          ['uuid1'], sleep_function=self.sleep)
        self.sleep.assert_called_with(v1.DEFAULT_RETRY_INTERVAL)
        self.assertEqual(v1.DEFAULT_MAX_RETRIES, self.sleep.call_count)

    def test_multiple(self, mock_get_st):
        mock_get_st.side_effect = [
            # attempt 1
            {'finished': False, 'error': None},
            {'finished': False, 'error': None},
            {'finished': False, 'error': None},
            # attempt 2
            {'finished': True, 'error': None},
            {'finished': False, 'error': None},
            {'finished': True, 'error': 'boom'},
            # attempt 3 (only uuid2)
            {'finished': True, 'error': None},
        ]

        res = self.get_client().wait_for_finish(['uuid1', 'uuid2', 'uuid3'],
                                                sleep_function=self.sleep)
        self.assertEqual({'uuid1': {'finished': True, 'error': None},
                          'uuid2': {'finished': True, 'error': None},
                          'uuid3': {'finished': True, 'error': 'boom'}},
                         res)
        self.sleep.assert_called_with(v1.DEFAULT_RETRY_INTERVAL)
        self.assertEqual(2, self.sleep.call_count)


@mock.patch.object(http.BaseClient, 'request')
class TestGetData(BaseTest):
    def test_json(self, mock_req):
        mock_req.return_value.json.return_value = 'json'

        self.assertEqual('json', self.get_client().get_data(self.uuid))

        mock_req.assert_called_once_with(
            'get', '/introspection/%s/data' % self.uuid)

    def test_raw(self, mock_req):
        mock_req.return_value.content = b'json'

        self.assertEqual(b'json', self.get_client().get_data(self.uuid,
                                                             raw=True))

        mock_req.assert_called_once_with(
            'get', '/introspection/%s/data' % self.uuid)

    def test_invalid_input(self, _):
        self.assertRaises(TypeError, self.get_client().get_data, 42)


@mock.patch.object(http.BaseClient, 'request')
class TestRules(BaseTest):
    def get_rules(self, **kwargs):
        return self.get_client(**kwargs).rules

    def test_create(self, mock_req):
        self.get_rules().create([{'cond': 'cond'}], [{'act': 'act'}])

        mock_req.assert_called_once_with(
            'post', '/rules', json={'conditions': [{'cond': 'cond'}],
                                    'actions': [{'act': 'act'}],
                                    'uuid': None,
                                    'description': None})

    def test_create_all_fields(self, mock_req):
        self.get_rules().create([{'cond': 'cond'}], [{'act': 'act'}],
                                uuid='u', description='d')

        mock_req.assert_called_once_with(
            'post', '/rules', json={'conditions': [{'cond': 'cond'}],
                                    'actions': [{'act': 'act'}],
                                    'uuid': 'u',
                                    'description': 'd'})

    def test_create_invalid_input(self, mock_req):
        self.assertRaises(TypeError, self.get_rules().create,
                          {}, [{'act': 'act'}])
        self.assertRaises(TypeError, self.get_rules().create,
                          [{'cond': 'cond'}], {})
        self.assertRaises(TypeError, self.get_rules().create,
                          [{'cond': 'cond'}], [{'act': 'act'}],
                          uuid=42)
        self.assertFalse(mock_req.called)

    def test_from_json(self, mock_req):
        self.get_rules().from_json({'foo': 'bar'})

        mock_req.assert_called_once_with(
            'post', '/rules', json={'foo': 'bar'})

    def test_get_all(self, mock_req):
        mock_req.return_value.json.return_value = {'rules': ['rules']}

        res = self.get_rules().get_all()
        self.assertEqual(['rules'], res)

        mock_req.assert_called_once_with('get', '/rules')

    def test_get(self, mock_req):
        mock_req.return_value.json.return_value = {'answer': 42}

        res = self.get_rules().get('uuid1')
        self.assertEqual({'answer': 42}, res)

        mock_req.assert_called_once_with('get', '/rules/uuid1')

    def test_get_invalid_input(self, mock_req):
        self.assertRaises(TypeError, self.get_rules().get, 42)
        self.assertFalse(mock_req.called)

    def test_delete(self, mock_req):
        self.get_rules().delete('uuid1')

        mock_req.assert_called_once_with('delete', '/rules/uuid1')

    def test_delete_invalid_input(self, mock_req):
        self.assertRaises(TypeError, self.get_rules().delete, 42)
        self.assertFalse(mock_req.called)

    def test_delete_all(self, mock_req):
        self.get_rules().delete_all()

        mock_req.assert_called_once_with('delete', '/rules')


@mock.patch.object(http.BaseClient, 'request')
class TestAbort(BaseTest):
    def test(self, mock_req):
        self.get_client().abort(self.uuid)
        mock_req.assert_called_once_with('post',
                                         '/introspection/%s/abort' % self.uuid)

    def test_invalid_input(self, _):
        self.assertRaises(TypeError, self.get_client().abort, 42)


@mock.patch.object(http.BaseClient, 'request')
class TestInterfaceApi(BaseTest):
    def setUp(self):
        super(TestInterfaceApi, self).setUp()

        self.inspector_db = {
            "all_interfaces": {
                'em1': {'mac': "00:11:22:33:44:55", 'ip': "10.10.1.1",
                        "lldp_processed": {
                            "switch_chassis_id": "99:aa:bb:cc:dd:ff",
                            "switch_port_id": "555",
                            "switch_port_vlans":
                                [{"id": 101, "name": "vlan101"},
                                 {"id": 102, "name": "vlan102"},
                                 {"id": 104, "name": "vlan104"},
                                 {"id": 201, "name": "vlan201"},
                                 {"id": 203, "name": "vlan203"}],
                            "switch_port_mtu": 1514}
                        },
                'em2': {'mac': "00:11:22:66:77:88", 'ip': "10.10.1.2",
                        "lldp_processed": {
                            "switch_chassis_id": "99:aa:bb:cc:dd:ff",
                            "switch_port_id": "777",
                            "switch_port_vlans":
                                [{"id": 201, "name": "vlan201"},
                                 {"id": 203, "name": "vlan203"}],
                            "switch_port_mtu": 9216}
                        },
                'em3': {'mac': "00:11:22:aa:bb:cc", 'ip': "10.10.1.2"}
            }
        }

    def test_all_interfaces(self, mock_req):
        mock_req.return_value.json.return_value = self.inspector_db

        fields = ['interface', 'mac', 'switch_chassis_id', 'switch_port_id',
                  'switch_port_vlans']
        expected = [['em1', '00:11:22:33:44:55', '99:aa:bb:cc:dd:ff', '555',
                     [{"id": 101, "name": "vlan101"},
                      {"id": 102, "name": "vlan102"},
                      {"id": 104, "name": "vlan104"},
                      {"id": 201, "name": "vlan201"},
                      {"id": 203, "name": "vlan203"}]],
                    ['em2', '00:11:22:66:77:88', '99:aa:bb:cc:dd:ff', '777',
                     [{"id": 201, "name": "vlan201"},
                      {"id": 203, "name": "vlan203"}]],
                    ['em3', '00:11:22:aa:bb:cc', None, None, None]]

        actual = self.get_client().get_all_interface_data(self.uuid,
                                                          fields)

        self.assertEqual(sorted(expected), sorted(actual))

        # Change fields
        fields = ['interface', 'switch_port_mtu']
        expected = [
            ['em1', 1514],
            ['em2', 9216],
            ['em3', None]]

        actual = self.get_client().get_all_interface_data(self.uuid, fields)
        self.assertEqual(expected, sorted(actual))

    def test_all_interfaces_filtered(self, mock_req):
        mock_req.return_value.json.return_value = self.inspector_db

        fields = ['interface', 'mac', 'switch_chassis_id', 'switch_port_id',
                  'switch_port_vlan_ids']
        expected = [['em1', '00:11:22:33:44:55', '99:aa:bb:cc:dd:ff', '555',
                     [101, 102, 104, 201, 203]]]

        # Filter on expected VLAN
        vlan = [104]
        actual = self.get_client().get_all_interface_data(self.uuid,
                                                          fields, vlan=vlan)
        self.assertEqual(expected, actual)

        # VLANs don't match existing vlans
        vlan = [111, 555]
        actual = self.get_client().get_all_interface_data(self.uuid,
                                                          fields, vlan=vlan)
        self.assertEqual([], actual)

    def test_one_interface(self, mock_req):
        mock_req.return_value.json.return_value = self.inspector_db

        # Note that a value for 'switch_foo' will not be found
        fields = ["node_ident", "interface", "mac", "switch_port_vlan_ids",
                  "switch_chassis_id", "switch_port_id",
                  "switch_port_mtu", "switch_port_vlans", "switch_foo"]

        expected_values = OrderedDict(
            [('node_ident', self.uuid),
             ('interface', "em1"),
             ('mac', "00:11:22:33:44:55"),
             ('switch_port_vlan_ids',
             [101, 102, 104, 201, 203]),
             ('switch_chassis_id', "99:aa:bb:cc:dd:ff"),
             ('switch_port_id', "555"),
             ('switch_port_mtu', 1514),
             ('switch_port_vlans',
             [{"id": 101, "name": "vlan101"},
              {"id": 102, "name": "vlan102"},
              {"id": 104, "name": "vlan104"},
              {"id": 201, "name": "vlan201"},
              {"id": 203, "name": "vlan203"}]),
             ("switch_foo", None)])

        iface_dict = self.get_client().get_interface_data(
            self.uuid, "em1", fields)
        self.assertEqual(expected_values, iface_dict)

        # Test interface name not in 'all_interfaces'
        expected_values = OrderedDict()
        iface_dict = self.get_client().get_interface_data(
            self.uuid, "em55", fields)
        self.assertEqual(expected_values, iface_dict)
