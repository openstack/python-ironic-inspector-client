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
        self.rules = _RulesAPI(self.request)

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


class _RulesAPI(object):
    """Introspection rules API."""

    def __init__(self, requester):
        self._request = requester

    def create(self, conditions, actions, uuid=None, description=None):
        """Create a new introspection rule.

        :conditions: list of rule conditions
        :actions: list of rule actions
        :uuid: rule UUID, will be generated if not specified
        :description: optional rule description
        :returns: rule representation
        """
        if uuid is not None and not isinstance(uuid, six.string_types):
            raise TypeError(
                _("Expected string for uuid argument, got %r") % uuid)
        for name, arg in [('conditions', conditions), ('actions', actions)]:
            if not isinstance(arg, list) or not all(isinstance(x, dict)
                                                    for x in arg):
                raise TypeError(_("Expected list of dicts for %(arg)s "
                                  "argument, got %(real)r"),
                                {'arg': name, 'real': arg})

        body = {'uuid': uuid, 'conditions': conditions, 'actions': actions,
                'description': description}
        return self.from_json(body)

    def from_json(self, json_rule):
        """Import an introspection rule from JSON data.

        :param json_rule: rule information as a dict
        :returns: rule representation
        """
        return self._request('post', '/rules', json=json_rule).json()

    def get_all(self):
        """List all introspection rules.

        :returns: list of short rule representations (uuid, description
                  and links)
        """
        return self._request('get', '/rules').json()['rules']

    def get(self, uuid):
        """Get detailed information about an introspection rule.

        :param uuid: rule UUID
        :returns: rule representation
        """
        if not isinstance(uuid, six.string_types):
            raise TypeError(
                _("Expected string for uuid argument, got %r") % uuid)
        return self._request('get', '/rules/%s' % uuid).json()

    def delete(self, uuid):
        """Delete an introspection rule.

        :param uuid: rule UUID
        """
        if not isinstance(uuid, six.string_types):
            raise TypeError(
                _("Expected string for uuid argument, got %r") % uuid)
        self._request('delete', '/rules/%s' % uuid)

    def delete_all(self):
        """Delete all introspection rules."""
        self._request('delete', '/rules')
