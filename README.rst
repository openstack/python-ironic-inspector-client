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
    client = ironic_inspector_client.ClientV1(session=keystone_session)

This code creates a client with API version *1.0* and a given Keystone session.
The service URL is fetched from the service catalog in this case. Optional
arguments ``service_type``, ``interface`` and ``region_name`` can be provided
to modify how the URL is looked up.

If the catalog lookup fails, the local host with port 5050 is tried. However,
this behaviour is deprecated and should not be relied on.
Also an explicit ``inspector_url`` can be passed to bypass service catalog.

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

Refer to the `HTTP API reference`_ for information on the
**Ironic Inspector** HTTP API.

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

    $ openstack baremetal introspection start [--wait] [--new-ipmi-password=PWD [--new-ipmi-username=USER]] UUID [UUID ...]

Note that the CLI call accepts several UUID's and will stop on the first error.

.. note::
    This CLI call doesn't rely on Ironic, and the introspected node will be left in
    ``MANAGEABLE`` state. This means that the Ironic node is not protected from other
    operations being performed by Ironic, which could cause inconsistency in the
    node's state, and lead to operational errors.

With ``--wait`` flag it waits until introspection ends for all given nodes,
then displays the results as a table.

Query introspection status
~~~~~~~~~~~~~~~~~~~~~~~~~~

``client.get_status(uuid)``

* ``uuid`` - Ironic node UUID.

Returns a dict with keys:

* ``finished`` - whether introspection has finished for this node;
* ``error`` - last error, ``None`` if introspection ended without an error.

CLI::

    $ openstack baremetal introspection status UUID

Retrieving introspection data
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``client.get_data(uuid[, raw])``

* ``uuid`` - Ironic node UUID;
* ``raw`` - whether to return raw data or parsed JSON data (the default).

CLI::

    $ openstack baremetal introspection data save [--file=file_name] UUID

If file name is not provided, the data is dumped to stdout.

.. note::
    This feature requires Swift support to be enabled in **Ironic Inspector**
    by setting ``[processing]store_data`` configuration option to ``swift``.

Aborting introspection
~~~~~~~~~~~~~~~~~~~~~~

``client.abort(uuid)``

* ``uuid`` - Ironic node UUID.

CLI::

  $ openstack baremetal introspection abort UUID

Reprocess stored introspection data
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``client.reprocess(uuid)``

* ``uuid`` - Ironic node UUID.

CLI::

    $ openstack baremetal introspection reprocess UUID

.. note::
   This feature requires Swift store to be enabled for **Ironic Inspector**
   by setting ``[processing]store_data`` configuration option to ``swift``.

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

    ironic_inspector_client.introspect(uuid[, new_ipmi_password[, new_ipmi_username]][, base_url][, api_version] **)

* Getting introspection status::

    ironic_inspector_client.get_status(uuid[, base_url][, api_version] **)

* Getting API versions supported by a server::

    ironic_inspector_client.server_api_versions([base_url] **)

Here ``base_url`` argument is the same as ``inspector_url`` argument
to the ``ClientV1`` constructor. Keyword arguments are passed to the client
constructor intact. The first 2 functions also accept deprecated ``auth_token``
argument, which should not be used.

Using names instead of UUID
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Starting with baremetal introspection API 1.5 (provided by **Ironic Inspector**
3.3.0) it's possible to use node names instead of UUIDs in all Python and CLI
calls.


.. _Gerrit Workflow: http://docs.openstack.org/infra/manual/developers.html#development-workflow
.. _Ironic Inspector: https://pypi.python.org/pypi/ironic-inspector
.. _Inspector contributing guide: http://docs.openstack.org/developer/ironic-inspector/contributing.html
.. _OpenStackClient: http://docs.openstack.org/developer/python-openstackclient/
.. _Setting IPMI Credentials: http://docs.openstack.org/developer/ironic-inspector/usage.html#setting-ipmi-credentials
.. _HTTP API reference: http://docs.openstack.org/developer/ironic-inspector/http-api.html
.. _introspection rules documentation: http://docs.openstack.org/developer/ironic-inspector/usage.html#introspection-rules
