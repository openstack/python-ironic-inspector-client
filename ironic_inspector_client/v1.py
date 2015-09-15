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

"""Client for V1 API."""

import six

from ironic_inspector_client.common import http
from ironic_inspector_client.common.i18n import _


DEFAULT_API_VERSION = (1, 0)
MAX_API_VERSION = (1, 0)


class ClientV1(http.BaseClient):
    """Client for API v1."""

    def __init__(self, **kwargs):
        """Create a client.

        :param kwargs: arguments to pass to the BaseClient constructor.
                       api_version is set to DEFAULT_API_VERSION by default.
        """
        kwargs.setdefault('api_version', DEFAULT_API_VERSION)
        super(ClientV1, self).__init__(**kwargs)

    def introspect(self, uuid, new_ipmi_password=None, new_ipmi_username=None):
        """Start introspection for a node.

        :param uuid: node uuid
        :param new_ipmi_password: if set, *Ironic Inspector* will update IPMI
                                  password to this value.
        :param new_ipmi_username: if new_ipmi_password is set, this values sets
                                  new IPMI user name. Defaults to one in
                                  driver_info.
        :raises: ClientError on error reported from a server
        :raises: VersionNotSupported if requested api_version is not supported
        :raises: *requests* library exception on connection problems.
        """
        if not isinstance(uuid, six.string_types):
            raise TypeError(
                _("Expected string for uuid argument, got %r") % uuid)
        if new_ipmi_username and not new_ipmi_password:
            raise ValueError(
                _("Setting IPMI user name requires a new password"))

        params = {'new_ipmi_username': new_ipmi_username,
                  'new_ipmi_password': new_ipmi_password}
        self.request('post', '/introspection/%s' % uuid, params=params)

    def get_status(self, uuid):
        """Get introspection status for a node.

        :param uuid: node uuid.
        :raises: ClientError on error reported from a server
        :raises: VersionNotSupported if requested api_version is not supported
        :raises: *requests* library exception on connection problems.
        """
        if not isinstance(uuid, six.string_types):
            raise TypeError(
                _("Expected string for uuid argument, got %r") % uuid)

        return self.request('get', '/introspection/%s' % uuid).json()
