Ironic Inspector Client
=======================

This is a client library and tool for `Ironic Inspector`_.

* Free software: Apache license
* Source: http://git.openstack.org/cgit/openstack/python-ironic-inspector-client
* Bugs: http://bugs.launchpad.net/python-ironic-inspector-client
* Downloads: https://pypi.python.org/pypi/python-ironic-inspector-client

Please follow usual OpenStack `Gerrit Workflow`_ to submit a patch, see
`Inspector contributing guide`_ for more detail.

Python API
----------

To use Python API first create a ``ClientV1`` object::

    import ironic_inspector_client

    url = 'http://HOST:5050'
    client = ironic_inspector_client.ClientV1(auth_token=token, inspector_url=url)

This code creates a client with API version *1.0* and an authentication token.
If ``inspector_url`` is missing, local host is assumed for now. Service
catalog will be used in the future.

Optional ``api_version`` argument is a minimum API version that a server must
support. It can be a tuple (MAJ, MIN), string "MAJ.MIN" or integer
(only major, minimum supported minor version is assumed).

See `Usage`_ for the list of available calls.

API Versioning
~~~~~~~~~~~~~~

Starting with version 2.1.0 **Ironic Inspector** supports optional API
versioning. Version is a tuple (X, Y), where X is always 1 for now.

The server has maximum and minimum supported versions. If no version is
requested, the server assumes (1, 0).

Two constants are exposed for convenience:

* ``DEFAULT_API_VERSION`` server API version used by default, always (1, 0)
  for now.

* ``MAX_API_VERSION`` maximum API version this client was designed to work
  with. This does not mean that other versions won't work at all - the server
  might still support them.

Usage
-----

CLI tool is based on OpenStackClient_ with prefix
``openstack baremetal introspection``. Accepts optional argument
``--inspector-url`` with the **Ironic Inspector** API endpoint.

Refer to HTTP-API.rst_ for information on the **Ironic Inspector** HTTP API.

Detect server API versions
~~~~~~~~~~~~~~~~~~~~~~~~~~

``client.server_api_versions()``

Returns a tuple (minimum version, maximum version). See `API Versioning`_ for
details.

Start introspection on a node
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``client.introspect(uuid, new_ipmi_username=None, new_ipmi_password=None)``

* ``uuid`` - Ironic node UUID;
* ``new_ipmi_username`` and ``new_ipmi_password`` - if these are set,
  **Ironic Inspector** will switch to manual power on and assigning IPMI
  credentials on introspection. See `Setting IPMI Credentials`_ for details.

CLI::

    $ openstack baremetal introspection start UUID [--new-ipmi-password=PWD [--new-ipmi-username=USER]]

Query introspection status
~~~~~~~~~~~~~~~~~~~~~~~~~~

``client.get_status(uuid)``

* ``uuid`` - Ironic node UUID.

Returns a dict with keys:

* ``finished`` - whether introspection has finished for this node;
* ``error`` - last error, ``None`` if introspection ended without an error.

CLI::

    $ openstack baremetal introspection status UUID

Introspection Rules API
~~~~~~~~~~~~~~~~~~~~~~~

All functions related to introspection rules are grouped under ``rules``
attribute of the ``ClientV1`` object.

Creating a rule
^^^^^^^^^^^^^^^

``client.rules.create(conditions, actions[, uuid][, description])``

* ``conditions`` and ``actions`` are lists of dictionaries with rule
  conditions and actions accordingly. Please refer to the `introspection rules
  documentation`_ for details on.

* ``uuid`` rule UUID, will be generated, if missing.

* ``description`` optional rule description.

This call is not directly represented in CLI, use ``import`` below.

``client.rules.from_json(rule_json)``

* ``rule_json`` dictionary with a rule representation.

CLI::

    $ openstack baremetal introspection rule import <JSON FILE>

Listing all rules
^^^^^^^^^^^^^^^^^

``client.rules.list()``

Returns list of short rule representations, containing only description, UUID
and links.

CLI::

    $ openstack baremetal introspection rule list

Getting rule details
^^^^^^^^^^^^^^^^^^^^

``client.rules.get(uuid)``

* ``uuid`` rule UUID.

Returns a full rule representation as a dictionary.

This call is currently not represented in CLI.

Deleting all rules
^^^^^^^^^^^^^^^^^^

``client.rules.delete_all()``

CLI::

    $ openstack baremetal introspection rule purge

Deleting a rule
^^^^^^^^^^^^^^^

``client.rules.delete(uuid)``

* ``uuid`` rule UUID.

CLI::

    $ openstack baremetal introspection rule delete <UUID>

Shortcut Functions
~~~~~~~~~~~~~~~~~~

The following functions are available for simplified access to the most common
functionality:

* Starting introspection::

    ironic_inspector_client.introspect(uuid[, new_ipmi_password[, new_ipmi_username]][, auth_token][, base_url][, api_version])

* Getting introspection status::

    ironic_inspector_client.get_status(uuid[, auth_token][, base_url][, api_version])

* Getting API versions supported by a server::

    ironic_inspector_client.server_api_versions([base_url])

Here ``base_url`` argument is the same as ``inspector_url`` argument to
``ClientV1`` constructor.


.. _Gerrit Workflow: http://docs.openstack.org/infra/manual/developers.html#development-workflow
.. _Ironic Inspector: https://pypi.python.org/pypi/ironic-inspector
.. _Inspector contributing guide: https://github.com/openstack/ironic-inspector/blob/master/CONTRIBUTING.rst
.. _OpenStackClient: http://docs.openstack.org/developer/python-openstackclient/
.. _Setting IPMI Credentials: https://github.com/openstack/ironic-inspector#setting-ipmi-credentials
.. _HTTP-API.rst: https://github.com/openstack/ironic-inspector/blob/master/HTTP-API.rst
.. _introspection rules documentation: https://github.com/openstack/ironic-inspector#introspection-rules
