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

import types
import unittest

import mock
from oslo_utils import netutils
from oslo_utils import uuidutils

import ironic_inspector_client
from ironic_inspector_client import client


class BaseTest(unittest.TestCase):
    def setUp(self):
        super(BaseTest, self).setUp()
        self.uuid = uuidutils.generate_uuid()
        self.my_ip = 'http://' + netutils.get_my_ipv4() + ':5050/v1'
        self.token = "token"
        self.headers = {'X-OpenStack-Ironic-Inspector-API-Version': '1.0',
                        'X-Auth-Token': self.token}


@mock.patch.object(client, 'server_api_versions',
                   lambda *args, **kwargs: ((1, 0), (1, 99)))
@mock.patch.object(client.requests, 'post', autospec=True,
                   **{'return_value.status_code': 200})
class TestIntrospect(BaseTest):
    def test(self, mock_post):
        client.introspect(self.uuid, base_url="http://host:port",
                          auth_token=self.token)
        mock_post.assert_called_once_with(
            "http://host:port/v1/introspection/%s" % self.uuid,
            headers=self.headers,
            params={'new_ipmi_username': None, 'new_ipmi_password': None}
        )

    def test_invalid_input(self, _):
        self.assertRaises(TypeError, client.introspect, 42)
        self.assertRaises(ValueError, client.introspect, 'uuid',
                          new_ipmi_username='user')

    def test_full_url(self, mock_post):
        client.introspect(self.uuid, base_url="http://host:port/v1/",
                          auth_token=self.token)
        mock_post.assert_called_once_with(
            "http://host:port/v1/introspection/%s" % self.uuid,
            headers=self.headers,
            params={'new_ipmi_username': None, 'new_ipmi_password': None}
        )

    def test_default_url(self, mock_post):
        client.introspect(self.uuid, auth_token=self.token)
        mock_post.assert_called_once_with(
            "%(my_ip)s/introspection/%(uuid)s" %
            {'my_ip': self.my_ip, 'uuid': self.uuid},
            headers=self.headers,
            params={'new_ipmi_username': None, 'new_ipmi_password': None}
        )

    def test_set_ipmi_credentials(self, mock_post):
        client.introspect(self.uuid, base_url="http://host:port",
                          auth_token=self.token, new_ipmi_password='p',
                          new_ipmi_username='u')
        mock_post.assert_called_once_with(
            "http://host:port/v1/introspection/%s" % self.uuid,
            headers=self.headers,
            params={'new_ipmi_username': 'u', 'new_ipmi_password': 'p'}
        )

    def test_none_ok(self, mock_post):
        client.introspect(self.uuid)
        del self.headers['X-Auth-Token']
        mock_post.assert_called_once_with(
            "%(my_ip)s/introspection/%(uuid)s" %
            {'my_ip': self.my_ip, 'uuid': self.uuid},
            headers=self.headers,
            params={'new_ipmi_username': None, 'new_ipmi_password': None}
        )

    def test_failed(self, mock_post):
        mock_post.return_value.status_code = 404
        mock_post.return_value.content = b'{"error":{"message":"boom"}}'
        self.assertRaisesRegexp(client.ClientError, "boom",
                                client.introspect, self.uuid)

    def test_failed_discoverd_style(self, mock_post):
        mock_post.return_value.status_code = 404
        mock_post.return_value.content = b"boom"
        self.assertRaisesRegexp(client.ClientError, "boom",
                                client.introspect, self.uuid)

    def test_failed_bad_json(self, mock_post):
        mock_post.return_value.status_code = 404
        mock_post.return_value.content = b'42'
        self.assertRaisesRegexp(client.ClientError, "42",
                                client.introspect, self.uuid)


@mock.patch.object(client, 'server_api_versions',
                   lambda *args, **kwargs: ((1, 0), (1, 99)))
@mock.patch.object(client.requests, 'get', autospec=True,
                   **{'return_value.status_code': 200})
class TestGetStatus(BaseTest):
    def test(self, mock_get):
        mock_get.return_value.json.return_value = 'json'

        client.get_status(self.uuid, auth_token=self.token)

        mock_get.assert_called_once_with(
            "%(my_ip)s/introspection/%(uuid)s" %
            {'my_ip': self.my_ip, 'uuid': self.uuid},
            headers=self.headers
        )

    def test_invalid_input(self, _):
        self.assertRaises(TypeError, client.get_status, 42)

    def test_failed(self, mock_post):
        mock_post.return_value.status_code = 404
        mock_post.return_value.content = b'{"error":{"message":"boom"}}'
        self.assertRaisesRegexp(client.ClientError, "boom",
                                client.get_status, self.uuid)

    def test_failed_discoverd_style(self, mock_post):
        mock_post.return_value.status_code = 404
        mock_post.return_value.content = b"boom"
        self.assertRaisesRegexp(client.ClientError, "boom",
                                client.get_status, self.uuid)

    def test_failed_bad_json(self, mock_post):
        mock_post.return_value.status_code = 404
        mock_post.return_value.content = b'42'
        self.assertRaisesRegexp(client.ClientError, "42",
                                client.get_status, self.uuid)


@mock.patch.object(client, 'server_api_versions',
                   lambda *args, **kwargs: ((1, 0), (1, 99)))
class TestCheckVesion(unittest.TestCase):
    def test_tuple(self):
        self.assertEqual((1, 0), client._check_api_version((1, 0)))

    def test_small_tuple(self):
        self.assertEqual((1, 0), client._check_api_version((1,)))

    def test_int(self):
        self.assertEqual((1, 0), client._check_api_version(1))

    def test_str(self):
        self.assertEqual((1, 0), client._check_api_version("1.0"))

    def test_invalid_tuple(self):
        self.assertRaises(TypeError, client._check_api_version, (1, "x"))
        self.assertRaises(ValueError, client._check_api_version, (1, 2, 3))

    def test_invalid_str(self):
        self.assertRaises(ValueError, client._check_api_version, "a.b")
        self.assertRaises(ValueError, client._check_api_version, "1.2.3")
        self.assertRaises(ValueError, client._check_api_version, "foo")

    def test_unsupported(self):
        self.assertRaises(client.VersionNotSupported,
                          client._check_api_version, (99, 42))


@mock.patch.object(client.requests, 'get', autospec=True,
                   **{'return_value.status_code': 200})
class TestServerApiVersions(BaseTest):
    def test_no_headers(self, mock_get):
        mock_get.return_value.headers = {}

        minv, maxv = client.server_api_versions()

        self.assertEqual((1, 0), minv)
        self.assertEqual((1, 0), maxv)
        mock_get.assert_called_once_with(self.my_ip)

    def test_with_headers(self, mock_get):
        mock_get.return_value.headers = {
            'X-OpenStack-Ironic-Inspector-API-Minimum-Version': '1.1',
            'X-OpenStack-Ironic-Inspector-API-Maximum-Version': '1.42',
        }

        minv, maxv = client.server_api_versions()

        self.assertEqual((1, 1), minv)
        self.assertEqual((1, 42), maxv)
        mock_get.assert_called_once_with(self.my_ip)

    def test_with_404(self, mock_get):
        mock_get.return_value.status_code = 404
        mock_get.return_value.headers = {}

        minv, maxv = client.server_api_versions()

        self.assertEqual((1, 0), minv)
        self.assertEqual((1, 0), maxv)
        mock_get.assert_called_once_with(self.my_ip)

    def test_with_other_error(self, mock_get):
        mock_get.return_value.status_code = 500
        mock_get.return_value.headers = {}

        self.assertRaises(client.ClientError, client.server_api_versions)

        mock_get.assert_called_once_with(self.my_ip)


class TestExposedAPI(unittest.TestCase):
    def test_only_client_all_exposed(self):
        exposed = {x for x in dir(ironic_inspector_client)
                   if not x.startswith('__') and
                   not isinstance(getattr(ironic_inspector_client, x),
                                  types.ModuleType)}
        self.assertEqual(set(client.__all__), exposed)

    def test_client_exposes_everything(self):
        actual = {x for x in dir(client)
                  if not x.startswith('_') and x != 'LOG' and
                  not isinstance(getattr(client, x),
                                 types.ModuleType)}
        self.assertEqual(actual, set(client.__all__))
