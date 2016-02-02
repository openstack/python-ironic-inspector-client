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

from keystoneclient import session as ks_session
import mock
from oslo_utils import uuidutils

import ironic_inspector_client
from ironic_inspector_client import client
from ironic_inspector_client.common import http
from ironic_inspector_client import v1


class BaseTest(unittest.TestCase):
    uuid = uuidutils.generate_uuid()
    token = "token"
    session = mock.Mock(spec=ks_session.Session)


@mock.patch.object(v1, 'ClientV1', autospec=True)
class TestIntrospect(BaseTest):
    def test(self, mock_v1):
        client.introspect(self.uuid, base_url="http://host:port",
                          session=self.session)
        mock_v1.assert_called_once_with(auth_token=None,
                                        session=self.session,
                                        inspector_url="http://host:port",
                                        api_version=client.DEFAULT_API_VERSION)
        mock_v1.return_value.introspect.assert_called_once_with(
            self.uuid, new_ipmi_username=None, new_ipmi_password=None)

    def test_token(self, mock_v1):
        client.introspect(self.uuid, base_url="http://host:port",
                          auth_token=self.token)
        mock_v1.assert_called_once_with(auth_token=self.token,
                                        session=None,
                                        inspector_url="http://host:port",
                                        api_version=client.DEFAULT_API_VERSION)
        mock_v1.return_value.introspect.assert_called_once_with(
            self.uuid, new_ipmi_username=None, new_ipmi_password=None)

    def test_full_url(self, mock_v1):
        client.introspect(self.uuid, base_url="http://host:port/v1/",
                          session=self.session)
        mock_v1.assert_called_once_with(auth_token=None,
                                        session=self.session,
                                        inspector_url="http://host:port/v1/",
                                        api_version=client.DEFAULT_API_VERSION)
        mock_v1.return_value.introspect.assert_called_once_with(
            self.uuid, new_ipmi_username=None, new_ipmi_password=None)

    def test_set_ipmi_credentials(self, mock_v1):
        client.introspect(self.uuid, base_url="http://host:port",
                          session=self.session, new_ipmi_password='p',
                          new_ipmi_username='u')
        mock_v1.assert_called_once_with(auth_token=None,
                                        session=self.session,
                                        inspector_url="http://host:port",
                                        api_version=client.DEFAULT_API_VERSION)
        mock_v1.return_value.introspect.assert_called_once_with(
            self.uuid, new_ipmi_username='u', new_ipmi_password='p')


@mock.patch.object(v1, 'ClientV1', autospec=True)
class TestGetStatus(BaseTest):
    def test(self, mock_v1):
        mock_v1.return_value.get_status.return_value = 'json'

        self.assertEqual('json',
                         client.get_status(self.uuid, session=self.session))

        mock_v1.assert_called_once_with(auth_token=None,
                                        session=self.session,
                                        inspector_url=None,
                                        api_version=client.DEFAULT_API_VERSION)
        mock_v1.return_value.get_status.assert_called_once_with(self.uuid)


@mock.patch.object(http, 'BaseClient', autospec=True)
class TestServerApiVersions(BaseTest):
    def test(self, mock_cli):
        mock_cli.return_value.server_api_versions.return_value = (1, 0), (1, 1)

        minv, maxv = client.server_api_versions()

        self.assertEqual((1, 0), minv)
        self.assertEqual((1, 1), maxv)

    def test_with_session(self, mock_cli):
        mock_cli.return_value.server_api_versions.return_value = (1, 0), (1, 1)

        minv, maxv = client.server_api_versions(session=self.session)

        self.assertEqual((1, 0), minv)
        self.assertEqual((1, 1), maxv)


class TestExposedAPI(unittest.TestCase):
    def test_only_client_all_exposed(self):
        exposed = {x for x in dir(ironic_inspector_client)
                   if not x.startswith('__') and
                   not isinstance(getattr(ironic_inspector_client, x),
                                  types.ModuleType)}
        self.assertEqual(set(client.__all__) | {'ClientV1'}, exposed)

    def test_client_exposes_everything(self):
        actual = {x for x in dir(client)
                  if not x.startswith('_') and x != 'LOG' and
                  not isinstance(getattr(client, x),
                                 types.ModuleType)}
        self.assertEqual(actual, set(client.__all__))
