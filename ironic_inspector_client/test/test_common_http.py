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

import mock

from ironic_inspector_client.common import http


class TestCheckVersion(unittest.TestCase):
    @mock.patch.object(http.BaseClient, 'server_api_versions',
                       lambda *args, **kwargs: ((1, 0), (1, 99)))
    def _check(self, version):
        cli = http.BaseClient(1)
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


@mock.patch.object(http.requests, 'get', autospec=True,
                   **{'return_value.status_code': 200,
                      'return_value.headers': FAKE_HEADERS})
class TestServerApiVersions(unittest.TestCase):
    def _check(self, current=1):
        return http.BaseClient(api_version=current).server_api_versions()

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


@mock.patch.object(http.requests, 'get', autospec=True,
                   **{'return_value.status_code': 200})
class TestRequest(unittest.TestCase):
    base_url = http._DEFAULT_URL + '/v1'
    token = 'token'

    def setUp(self):
        super(TestRequest, self).setUp()
        self.headers = {http._VERSION_HEADER: '1.0',
                        'X-Auth-Token': self.token}

    @mock.patch.object(http.BaseClient, 'server_api_versions',
                       lambda self: ((1, 0), (1, 42)))
    def get_client(self, version=1, auth_token='token', inspector_url=None):
        return http.BaseClient(version, auth_token=auth_token,
                               inspector_url=inspector_url)

    def test_ok(self, mock_req):
        res = self.get_client().request('get', '/foo/bar')

        self.assertIs(mock_req.return_value, res)
        mock_req.assert_called_once_with(self.base_url + '/foo/bar',
                                         headers=self.headers)

    def test_no_auth(self, mock_req):
        res = self.get_client(auth_token=None).request('get', '/foo/bar')

        self.assertIs(mock_req.return_value, res)
        del self.headers['X-Auth-Token']
        mock_req.assert_called_once_with(self.base_url + '/foo/bar',
                                         headers=self.headers)

    def test_explicit_version(self, mock_req):
        res = self.get_client(version='1.2').request('get', '/foo/bar')

        self.assertIs(mock_req.return_value, res)
        self.headers[http._VERSION_HEADER] = '1.2'
        mock_req.assert_called_once_with(self.base_url + '/foo/bar',
                                         headers=self.headers)

    def test_explicit_url(self, mock_req):
        res = self.get_client(inspector_url='http://host').request(
            'get', '/foo/bar')

        self.assertIs(mock_req.return_value, res)
        mock_req.assert_called_once_with('http://host/v1/foo/bar',
                                         headers=self.headers)

    def test_explicit_url_with_version(self, mock_req):
        res = self.get_client(inspector_url='http://host/v1').request(
            'get', '/foo/bar')

        self.assertIs(mock_req.return_value, res)
        mock_req.assert_called_once_with('http://host/v1/foo/bar',
                                         headers=self.headers)

    def test_error(self, mock_req):
        mock_req.return_value.status_code = 400
        mock_req.return_value.content = json.dumps(
            {'error': {'message': 'boom'}}).encode('utf-8')

        self.assertRaisesRegexp(http.ClientError, 'boom',
                                self.get_client().request, 'get', 'url')

    def test_error_discoverd_style(self, mock_req):
        mock_req.return_value.status_code = 400
        mock_req.return_value.content = b'boom'

        self.assertRaisesRegexp(http.ClientError, 'boom',
                                self.get_client().request, 'get', 'url')
