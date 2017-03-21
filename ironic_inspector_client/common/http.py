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

"""Generic code for inspector client."""

import json
import logging

from keystoneauth1 import exceptions as ks_exc
from keystoneauth1 import session as ks_session
from keystoneauth1 import token_endpoint
from oslo_utils import netutils
import requests
import six

from ironic_inspector_client.common.i18n import _


_DEFAULT_URL = 'http://' + netutils.get_my_ipv4() + ':5050'
_ERROR_ENCODING = 'utf-8'
LOG = logging.getLogger('ironic_inspector_client')


_MIN_VERSION_HEADER = 'X-OpenStack-Ironic-Inspector-API-Minimum-Version'
_MAX_VERSION_HEADER = 'X-OpenStack-Ironic-Inspector-API-Maximum-Version'
_VERSION_HEADER = 'X-OpenStack-Ironic-Inspector-API-Version'
_AUTH_TOKEN_HEADER = 'X-Auth-Token'


def _parse_version(api_version):
    try:
        return tuple(int(x) for x in api_version.split('.'))
    except (ValueError, TypeError):
        raise ValueError(_("Malformed API version: expect tuple, string "
                           "in form of X.Y or integer"))


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

        LOG.debug('Inspector returned error "%(msg)s" (HTTP %(code)s)',
                  {'msg': msg, 'code': response.status_code})
        super(ClientError, self).__init__(msg, response=response)

    @classmethod
    def raise_if_needed(cls, response):
        """Raise exception if response contains error."""
        if response.status_code >= 400:
            raise cls(response)


class VersionNotSupported(Exception):
    """Denotes that requested API versions is not supported by the server.

    :ivar expected: requested version.
    :ivar supported: sequence with two items: minimum and maximum actually
        supported versions.
    """
    def __init__(self, expected, supported):
        msg = (_('Version %(expected)s is not supported by the server, '
                 'supported range is %(supported)s') %
               {'expected': expected,
                'supported': ' to '.join(str(x) for x in supported)})
        self.expected_version = expected
        self.supported_versions = supported
        super(Exception, self).__init__(msg)


class BaseClient(object):
    """Base class for clients, provides common HTTP code."""

    def __init__(self, api_version, inspector_url=None, auth_token=None,
                 session=None, service_type='baremetal-introspection',
                 interface=None, region_name=None):
        """Create a client.

        :param api_version: minimum API version that must be supported by
                            the server
        :param inspector_url: *Ironic Inspector* URL in form:
            http://host:port[/ver]. When session is provided, defaults to
            service URL from the catalog. As a last resort
            defaults to ``http://<current host>:5050/v<MAJOR>``.
        :param auth_token: authentication token (deprecated, use session)
        :param session: existing keystone session
        :param service_type: service type to use when looking up the URL
        :param interface: interface type (public, internal, etc) to use when
            looking up the URL
        :param region_name: region name to use when looking up the URL
        """
        self._base_url = inspector_url or _DEFAULT_URL
        self._auth_token = auth_token

        if session is None:
            if auth_token:
                LOG.warning('Passing auth_token to client objects '
                            'is deprecated, please pass session instead')
                auth = token_endpoint.Token(endpoint=self._base_url,
                                            token=auth_token)
            else:
                auth = None

            self._session = ks_session.Session(auth)
        else:
            self._session = session
            if not inspector_url:
                try:
                    self._base_url = session.get_endpoint(
                        service_type=service_type,
                        interface=interface,
                        region_name=region_name) or _DEFAULT_URL
                except ks_exc.EndpointNotFound:
                    LOG.warning('Endpoint for service %s was not found, '
                                'falling back to local host on port 5050',
                                service_type)

        self._base_url = self._base_url.rstrip('/')
        self._api_version = self._check_api_version(api_version)
        self._version_str = '%d.%d' % self._api_version
        ver_postfix = '/v%d' % self._api_version[0]

        if not self._base_url.endswith(ver_postfix):
            self._base_url += ver_postfix

    def _add_headers(self, headers):
        headers[_VERSION_HEADER] = self._version_str
        return headers

    def _check_api_version(self, api_version):
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

        minv, maxv = self.server_api_versions()
        if api_version < minv or api_version > maxv:
            raise VersionNotSupported(api_version, (minv, maxv))

        return api_version

    def request(self, method, url, **kwargs):
        """Make an HTTP request.

        :param method: HTTP method
        :param endpoint: relative endpoint
        :param kwargs: arguments to pass to 'requests' library
        """
        headers = self._add_headers(kwargs.pop('headers', {}))
        url = self._base_url + '/' + url.lstrip('/')
        LOG.debug('Requesting %(method)s %(url)s (API version %(ver)s) '
                  'with %(args)s',
                  {'method': method.upper(), 'url': url,
                   'ver': self._version_str, 'args': kwargs})
        res = self._session.request(url, method, headers=headers,
                                    raise_exc=False, **kwargs)
        LOG.debug('Got response for %(method)s %(url)s with status code '
                  '%(code)s', {'url': url, 'method': method.upper(),
                               'code': res.status_code})
        ClientError.raise_if_needed(res)
        return res

    def server_api_versions(self):
        """Get minimum and maximum supported API versions from a server.

        :return: tuple (minimum version, maximum version) each version
                 is returned as a tuple (X, Y)
        :raises: *requests* library exception on connection problems.
        :raises: ValueError if returned version cannot be parsed
        """
        res = self._session.get(self._base_url, authenticated=False,
                                raise_exc=False)
        # HTTP Not Found is a valid response for older (2.0.0) servers
        if res.status_code >= 400 and res.status_code != 404:
            ClientError.raise_if_needed(res)

        min_ver = res.headers.get(_MIN_VERSION_HEADER, '1.0')
        max_ver = res.headers.get(_MAX_VERSION_HEADER, '1.0')
        res = (_parse_version(min_ver), _parse_version(max_ver))
        LOG.debug('Supported API version range for %(url)s is '
                  '[%(min)s, %(max)s]',
                  {'url': self._base_url, 'min': min_ver, 'max': max_ver})
        return res
