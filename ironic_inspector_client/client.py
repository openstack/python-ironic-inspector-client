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
import logging

from oslo_utils import netutils
import requests
import six

from ironic_inspector_client.common.i18n import _


_DEFAULT_URL = 'http://' + netutils.get_my_ipv4() + ':5050/v1'
_ERROR_ENCODING = 'utf-8'
LOG = logging.getLogger('ironic_inspector_client')


DEFAULT_API_VERSION = (1, 0)
MAX_API_VERSION = (1, 0)
_MIN_VERSION_HEADER = 'X-OpenStack-Ironic-Inspector-API-Minimum-Version'
_MAX_VERSION_HEADER = 'X-OpenStack-Ironic-Inspector-API-Maximum-Version'
_VERSION_HEADER = 'X-OpenStack-Ironic-Inspector-API-Version'


def _prepare(base_url, auth_token, api_version=None):
    base_url = (base_url or _DEFAULT_URL).rstrip('/')
    if not base_url.endswith('v1'):
        base_url += '/v1'
    headers = {'X-Auth-Token': auth_token} if auth_token else {}
    if api_version:
        api_version = _check_api_version(api_version, base_url)
        headers[_VERSION_HEADER] = '%d.%d' % api_version
    return base_url, headers


def _parse_version(api_version):
    try:
        return tuple(int(x) for x in api_version.split('.'))
    except (ValueError, TypeError):
        raise ValueError(_("Malformed API version: expect tuple, string "
                           "in form of X.Y or integer"))


def _check_api_version(api_version, base_url=None):
    if isinstance(api_version, int):
        api_version = (api_version, 0)
    if isinstance(api_version, six.string_types):
        api_version = _parse_version(api_version)
    api_version = tuple(api_version)
    if not all(isinstance(x, int) for x in api_version):
        raise TypeError(_("All API version components should be integers"))
    if len(api_version) == 1:
        api_version += (0,)
    elif len(api_version) > 2:
        raise ValueError(_("API version should be of length 1 or 2"))

    minv, maxv = server_api_versions(base_url=base_url)
    if api_version < minv or api_version > maxv:
        raise VersionNotSupported(api_version, (minv, maxv))

    return api_version


class ClientError(requests.HTTPError):
    """Error returned from a server."""
    def __init__(self, response):
        # inspector returns error message in body
        msg = response.content.decode(_ERROR_ENCODING)
        try:
            msg = json.loads(msg)['error']['message']
        except ValueError:
            LOG.debug('Old style error response returned, assuming '
                      'ironic-discoverd')
        except (KeyError, TypeError):
            LOG.exception('Bad error response from Ironic Inspector')
        super(ClientError, self).__init__(msg, response=response)

    @classmethod
    def raise_if_needed(cls, response):
        """Raise exception if response contains error."""
        if response.status_code >= 400:
            raise cls(response)


class VersionNotSupported(Exception):
    """Denotes that requested API versions is not supported by the server."""
    def __init__(self, expected, supported):
        msg = (_('Version %(expected)s is supported not by the server, '
                 'supported range is %(supported)s') %
               {'expected': expected, 'supported': supported})
        self.expected_version = expected
        self.supported_versions = supported
        super(Exception, self).__init__(msg)


def introspect(uuid, base_url=None, auth_token=None,
               new_ipmi_password=None, new_ipmi_username=None,
               api_version=DEFAULT_API_VERSION):
    """Start introspection for a node.

    :param uuid: node uuid
    :param base_url: *Ironic Inspector* URL in form: http://host:port[/ver],
                     defaults to ``http://<current host>:5050/v1``.
    :param auth_token: Keystone authentication token.
    :param new_ipmi_password: if set, *Ironic Inspector* will update IPMI
                              password to this value.
    :param new_ipmi_username: if new_ipmi_password is set, this values sets
                              new IPMI user name. Defaults to one in
                              driver_info.
    :param api_version: requested Ironic Inspector API version, defaults to
                        ``DEFAULT_API_VERSION`` attribute.
    :raises: ClientError on error reported from a server
    :raises: VersionNotSupported if requested api_version is not supported
    :raises: *requests* library exception on connection problems.
    """
    if not isinstance(uuid, six.string_types):
        raise TypeError(_("Expected string for uuid argument, got %r") % uuid)
    if new_ipmi_username and not new_ipmi_password:
        raise ValueError(_("Setting IPMI user name requires a new password"))

    base_url, headers = _prepare(base_url, auth_token, api_version=api_version)

    params = {'new_ipmi_username': new_ipmi_username,
              'new_ipmi_password': new_ipmi_password}
    res = requests.post("%s/introspection/%s" % (base_url, uuid),
                        headers=headers, params=params)
    ClientError.raise_if_needed(res)


def get_status(uuid, base_url=None, auth_token=None,
               api_version=DEFAULT_API_VERSION):
    """Get introspection status for a node.

    New in Ironic Inspector version 1.0.0.
    :param uuid: node uuid.
    :param base_url: *Ironic Inspector* URL in form: http://host:port[/ver],
                     defaults to ``http://<current host>:5050/v1``.
    :param auth_token: Keystone authentication token.
    :param api_version: requested Ironic Inspector API version, defaults to
                        ``DEFAULT_API_VERSION`` attribute.
    :raises: ClientError on error reported from a server
    :raises: VersionNotSupported if requested api_version is not supported
    :raises: *requests* library exception on connection problems.
    """
    if not isinstance(uuid, six.string_types):
        raise TypeError(_("Expected string for uuid argument, got %r") % uuid)

    base_url, headers = _prepare(base_url, auth_token, api_version=api_version)

    res = requests.get("%s/introspection/%s" % (base_url, uuid),
                       headers=headers)
    ClientError.raise_if_needed(res)
    return res.json()


def server_api_versions(base_url=None):
    """Get minimum and maximum supported API versions from a server.

    :param base_url: *Ironic Inspector* URL in form: http://host:port[/ver],
                     defaults to ``http://<current host>:5050/v1``.
    :return: tuple (minimum version, maximum version) each version is returned
             as a tuple (X, Y)
    :raises: *requests* library exception on connection problems.
    :raises: ValueError if returned version cannot be parsed
    """
    base_url, _headers = _prepare(base_url, auth_token=None)
    res = requests.get(base_url)
    # HTTP Not Found is a valid response for older (2.0.0) servers
    if res.status_code >= 400 and res.status_code != 404:
        ClientError.raise_if_needed(res)
    return (_parse_version(res.headers.get(_MIN_VERSION_HEADER, '1.0')),
            _parse_version(res.headers.get(_MAX_VERSION_HEADER, '1.0')))
