Ironic Inspector Client
=======================

This is a client library and tool for ironic-inspector_.

Install from PyPI::

    pip install python-ironic-inspector-client

Please follow usual OpenStack `Gerrit Workflow`_ to submit a patch, see
`Inspector contributing guide`_ for more detail.

Usage
-----

CLI tool is based on OpenStackClient_ with prefix
``openstack baremetal introspection``. Accepts optional argument
``--inspector-url`` with the **ironic-inspector** API endpoint.

* **Start introspection on a node**:

  ``ironic_inspector_client.introspect(uuid, new_ipmi_username=None,
  new_ipmi_password=None)``

  ::

    $ openstack baremetal introspection start UUID [--new-ipmi-password=PWD [--new-ipmi-username=USER]]

  * ``uuid`` - Ironic node UUID;
  * ``new_ipmi_username`` and ``new_ipmi_password`` - if these are set,
    **ironic-inspector** will switch to manual power on and assigning IPMI
    credentials on introspection. See `Setting IPMI Credentials`_ for details.

* **Query introspection status**:

  ``ironic_inspector_client.get_status(uuid)``

  ::

    $ openstack baremetal introspection status UUID

  * ``uuid`` - Ironic node UUID.

Every call accepts additional optional arguments:

* ``base_url`` **ironic-inspector** API endpoint, defaults to
  ``127.0.0.1:5050``,
* ``auth_token`` Keystone authentication token.
* ``api_version`` requested API version; can be a tuple (MAJ, MIN), string
  "MAJ.MIN" or integer (only major). Right now only (1, 0) is supported, other
  versions will raise an exception. Defaults to ``DEFAULT_API_VERSION``.

Two constants are exposed by the client:

* ``DEFAULT_API_VERSION`` server API version used by default.
* ``MAX_API_VERSION`` maximum API version this client was designed to work
  with. Right now providing bigger value for ``api_version`` argument raises
  on exception, this limitation may be lifted later.

Refer to HTTP-API.rst_ for information on the **ironic-inspector** HTTP API.


.. _Gerrit Workflow: http://docs.openstack.org/infra/manual/developers.html#development-workflow
.. _ironic-inspector: https://pypi.python.org/pypi/ironic-inspector
.. _Inspector contributing guide: https://github.com/openstack/ironic-inspector/blob/master/CONTRIBUTING.rst
.. _OpenStackClient: http://docs.openstack.org/developer/python-openstackclient/
.. _Setting IPMI Credentials: https://github.com/openstack/ironic-inspector#setting-ipmi-credentials
.. _HTTP-API.rst: https://github.com/openstack/ironic-inspector/blob/master/HTTP-API.rst
