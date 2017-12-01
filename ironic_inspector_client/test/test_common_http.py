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

import json
import unittest

from keystoneauth1 import exceptions
from keystoneauth1 import session
import mock

from ironic_inspector_client.common import http


class TestCheckVersion(unittest.TestCase):
    @mock.patch.object(http.BaseClient, 'server_api_versions',
                       lambda *args, **kwargs: ((1, 0), (1, 99)))
    def _check(self, version):
        cli = http.BaseClient(1, inspector_url='http://127.0.0.1:5050')
        return cli._check_api_version(version)

    def test_tuple(self):
        self.assertEqual((1, 0), self._check((1, 0)))

    def test_small_tuple(self):
        self.assertEqual((1, 0), self._check((1,)))

    def test_int(self):
        self.assertEqual((1, 0), self._check(1))

    def test_str(self):
        self.assertEqual((1, 0), self._check("1.0"))

    def test_invalid_tuple(self):
        self.assertRaises(TypeError, self._check, (1, "x"))
        self.assertRaises(ValueError, self._check, (1, 2, 3))

    def test_invalid_str(self):
        self.assertRaises(ValueError, self._check, "a.b")
        self.assertRaises(ValueError, self._check, "1.2.3")
        self.assertRaises(ValueError, self._check, "foo")

    def test_unsupported(self):
        self.assertRaises(http.VersionNotSupported, self._check, (99, 42))


FAKE_HEADERS = {
    http._MIN_VERSION_HEADER: '1.0',
    http._MAX_VERSION_HEADER: '1.9'
}


@mock.patch.object(session.Session, 'get', autospec=True,
                   **{'return_value.status_code': 200,
                      'return_value.headers': FAKE_HEADERS})
class TestServerApiVersions(unittest.TestCase):
    def _check(self, current=1):
        return http.BaseClient(
            api_version=current,
            inspector_url='http://127.0.0.1:5050').server_api_versions()

    def test_no_headers(self, mock_get):
        mock_get.return_value.headers = {}

        minv, maxv = self._check()

        self.assertEqual((1, 0), minv)
        self.assertEqual((1, 0), maxv)

    def test_with_headers(self, mock_get):
        mock_get.return_value.headers = {
            'X-OpenStack-Ironic-Inspector-API-Minimum-Version': '1.1',
            'X-OpenStack-Ironic-Inspector-API-Maximum-Version': '1.42',
        }

        minv, maxv = self._check(current=(1, 2))

        self.assertEqual((1, 1), minv)
        self.assertEqual((1, 42), maxv)

    def test_with_404(self, mock_get):
        mock_get.return_value.status_code = 404
        mock_get.return_value.headers = {}

        minv, maxv = self._check()

        self.assertEqual((1, 0), minv)
        self.assertEqual((1, 0), maxv)

    def test_with_other_error(self, mock_get):
        mock_get.return_value.status_code = 500
        mock_get.return_value.headers = {}

        self.assertRaises(http.ClientError, self._check)


class TestRequest(unittest.TestCase):
    base_url = 'http://127.0.0.1:5050/v1'

    def setUp(self):
        super(TestRequest, self).setUp()
        self.headers = {http._VERSION_HEADER: '1.0'}
        self.session = mock.Mock(spec=session.Session)
        self.session.get_endpoint.return_value = self.base_url
        self.req = self.session.request
        self.req.return_value.status_code = 200

    @mock.patch.object(http.BaseClient, 'server_api_versions',
                       lambda self: ((1, 0), (1, 42)))
    def get_client(self, version=1, inspector_url=None, use_session=True):
        if use_session:
            return http.BaseClient(version, session=self.session,
                                   inspector_url=inspector_url)
        else:
            return http.BaseClient(version, inspector_url=inspector_url)

    def test_ok(self):
        res = self.get_client().request('get', '/foo/bar')

        self.assertIs(self.req.return_value, res)
        self.req.assert_called_once_with(self.base_url + '/foo/bar', 'get',
                                         raise_exc=False, headers=self.headers)
        self.session.get_endpoint.assert_called_once_with(
            service_type='baremetal-introspection',
            interface=None, region_name=None)

    def test_no_endpoint(self):
        self.session.get_endpoint.return_value = None
        self.assertRaises(http.EndpointNotFound, self.get_client)

        self.session.get_endpoint.assert_called_once_with(
            service_type='baremetal-introspection',
            interface=None, region_name=None)

    def test_endpoint_not_found(self):
        self.session.get_endpoint.side_effect = exceptions.EndpointNotFound()
        self.assertRaises(http.EndpointNotFound, self.get_client)

        self.session.get_endpoint.assert_called_once_with(
            service_type='baremetal-introspection',
            interface=None, region_name=None)

    @mock.patch.object(session.Session, 'request', autospec=True,
                       **{'return_value.status_code': 200})
    def test_ok_no_auth(self, mock_req):
        res = self.get_client(
            use_session=False,
            inspector_url='http://some/host').request('get', '/foo/bar')

        self.assertIs(mock_req.return_value, res)
        mock_req.assert_called_once_with(mock.ANY,
                                         'http://some/host/v1/foo/bar', 'get',
                                         raise_exc=False, headers=self.headers)

    def test_ok_with_session_and_url(self):
        res = self.get_client(
            use_session=True,
            inspector_url='http://some/host').request('get', '/foo/bar')

        self.assertIs(self.req.return_value, res)
        self.req.assert_called_once_with('http://some/host/v1/foo/bar', 'get',
                                         raise_exc=False, headers=self.headers)

    def test_explicit_version(self):
        res = self.get_client(version='1.2').request('get', '/foo/bar')

        self.assertIs(self.req.return_value, res)
        self.headers[http._VERSION_HEADER] = '1.2'
        self.req.assert_called_once_with(self.base_url + '/foo/bar', 'get',
                                         raise_exc=False, headers=self.headers)

    def test_error(self):
        self.req.return_value.status_code = 400
        self.req.return_value.content = json.dumps(
            {'error': {'message': 'boom'}}).encode('utf-8')

        self.assertRaisesRegexp(http.ClientError, 'boom',
                                self.get_client().request, 'get', 'url')

    def test_error_discoverd_style(self):
        self.req.return_value.status_code = 400
        self.req.return_value.content = b'boom'

        self.assertRaisesRegexp(http.ClientError, 'boom',
                                self.get_client().request, 'get', 'url')
