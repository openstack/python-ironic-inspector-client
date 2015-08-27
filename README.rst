Ironic Inspector Client
=======================

This is a client library and tool for `Ironic Inspector`_.

* Free software: Apache license
* Source: http://git.openstack.org/cgit/openstack/python-ironic-inspector-client
* Bugs: http://bugs.launchpad.net/python-ironic-inspector-client
* Downloads: https://pypi.python.org/pypi/python-ironic-inspector-client

Please follow usual OpenStack `Gerrit Workflow`_ to submit a patch, see
`Inspector contributing guide`_ for more detail.

Usage
-----

CLI tool is based on OpenStackClient_ with prefix
``openstack baremetal introspection``. Accepts optional argument
``--inspector-url`` with the **Ironic Inspector** API endpoint.

* **Start introspection on a node**:

  ``ironic_inspector_client.introspect(uuid, new_ipmi_username=None,
  new_ipmi_password=None)``

  ::

    $ openstack baremetal introspection start UUID [--new-ipmi-password=PWD [--new-ipmi-username=USER]]

  * ``uuid`` - Ironic node UUID;
  * ``new_ipmi_username`` and ``new_ipmi_password`` - if these are set,
    **Ironic Inspector** will switch to manual power on and assigning IPMI
    credentials on introspection. See `Setting IPMI Credentials`_ for details.

* **Query introspection status**:

  ``ironic_inspector_client.get_status(uuid)``

  ::

    $ openstack baremetal introspection status UUID

  * ``uuid`` - Ironic node UUID.

Every call accepts additional optional arguments:

* ``base_url`` **Ironic Inspector** API endpoint, defaults to
  ``127.0.0.1:5050``,
* ``auth_token`` Keystone authentication token.
* ``api_version`` requested API version; can be a tuple (MAJ, MIN), string
  "MAJ.MIN" or integer (only major). Defaults to ``DEFAULT_API_VERSION``.

Refer to HTTP-API.rst_ for information on the **Ironic Inspector** HTTP API.

API Versioning
~~~~~~~~~~~~~~

Starting with version 2.1.0 **Ironic Inspector** supports optional API
versioning. Version is a tuple (X, Y), where X is always 1 for now.

The server has maximum and minimum supported versions. If no version is
requested, the server assumes (1, 0).

* There is a helper function to figure out the current server API versions
  range:

  ``ironic_inspector_client.server_api_versions()``

  Returns a tuple (minimum version, maximum version).
  Supports optional argument:

  * ``base_url`` **Ironic Inspector** API endpoint, defaults to
    ``127.0.0.1:5050``,

Two constants are exposed by the client:

* ``DEFAULT_API_VERSION`` server API version used by default, always (1, 0)
  for now.

* ``MAX_API_VERSION`` maximum API version this client was designed to work
  with. This does not mean that other versions won't work at all - the server
  might still support them.


.. _Gerrit Workflow: http://docs.openstack.org/infra/manual/developers.html#development-workflow
.. _Ironic Inspector: https://pypi.python.org/pypi/ironic-inspector
.. _Inspector contributing guide: https://github.com/openstack/ironic-inspector/blob/master/CONTRIBUTING.rst
.. _OpenStackClient: http://docs.openstack.org/developer/python-openstackclient/
.. _Setting IPMI Credentials: https://github.com/openstack/ironic-inspector#setting-ipmi-credentials
.. _HTTP-API.rst: https://github.com/openstack/ironic-inspector/blob/master/HTTP-API.rst
