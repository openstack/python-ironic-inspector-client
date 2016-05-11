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

"""Shorthand client functions using V1 API."""

from ironic_inspector_client.common import http
from ironic_inspector_client import v1


DEFAULT_API_VERSION = (1, 0)
MAX_API_VERSION = (1, 5)


# Reimport for backward compatibility
ClientError = http.ClientError
VersionNotSupported = http.VersionNotSupported


def introspect(uuid, base_url=None, auth_token=None,
               new_ipmi_password=None, new_ipmi_username=None,
               api_version=DEFAULT_API_VERSION, session=None, **kwargs):
    """Start introspection for a node.

    :param uuid: node uuid
    :param base_url: *Ironic Inspector* URL in form: http://host:port[/ver],
                     defaults to ``http://<current host>:5050/v1``.
    :param auth_token: deprecated, use session instead.
    :param new_ipmi_password: if set, *Ironic Inspector* will update IPMI
                              password to this value.
    :param new_ipmi_username: if new_ipmi_password is set, this values sets
                              new IPMI user name. Defaults to one in
                              driver_info.
    :param api_version: requested Ironic Inspector API version, defaults to
                        ``DEFAULT_API_VERSION`` attribute.
    :param session: keystone session.
    :param kwargs: keyword arguments to pass to the ClientV1 constructor.
    :raises: ClientError on error reported from a server
    :raises: VersionNotSupported if requested api_version is not supported
    :raises: *requests* library exception on connection problems.
    """
    c = v1.ClientV1(api_version=api_version, auth_token=auth_token,
                    inspector_url=base_url, session=session, **kwargs)
    return c.introspect(uuid, new_ipmi_username=new_ipmi_username,
                        new_ipmi_password=new_ipmi_password)


def get_status(uuid, base_url=None, auth_token=None,
               api_version=DEFAULT_API_VERSION, session=None, **kwargs):
    """Get introspection status for a node.

    New in Ironic Inspector version 1.0.0.
    :param uuid: node uuid.
    :param base_url: *Ironic Inspector* URL in form: http://host:port[/ver],
                     defaults to ``http://<current host>:5050/v1``.
    :param auth_token: deprecated, use session instead.
    :param api_version: requested Ironic Inspector API version, defaults to
                        ``DEFAULT_API_VERSION`` attribute.
    :param session: keystone session.
    :param kwargs: keyword arguments to pass to the ClientV1 constructor.
    :raises: ClientError on error reported from a server
    :raises: VersionNotSupported if requested api_version is not supported
    :raises: *requests* library exception on connection problems.
    """
    c = v1.ClientV1(api_version=api_version, auth_token=auth_token,
                    inspector_url=base_url, session=session, **kwargs)
    return c.get_status(uuid)


def server_api_versions(base_url=None, session=None, **kwargs):
    """Get minimum and maximum supported API versions from a server.

    :param base_url: *Ironic Inspector* URL in form: http://host:port[/ver],
                     defaults to ``http://<current host>:5050/v1``.
    :param session: keystone session (authentication is not required).
    :param kwargs: keyword arguments to pass to the BaseClient constructor.
    :return: tuple (minimum version, maximum version) each version is returned
             as a tuple (X, Y)
    :raises: *requests* library exception on connection problems.
    :raises: ValueError if returned version cannot be parsed
    """
    c = http.BaseClient(1, inspector_url=base_url, session=session, **kwargs)
    return c.server_api_versions()


__all__ = ['DEFAULT_API_VERSION', 'MAX_API_VERSION', 'ClientError',
           'VersionNotSupported', 'introspect', 'get_status',
           'server_api_versions']
