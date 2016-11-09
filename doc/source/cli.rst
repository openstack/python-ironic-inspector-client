Command Line Reference
======================

Common arguments
~~~~~~~~~~~~~~~~

All commands accept the following arguments:

* ``--inspector-url`` the **Ironic Inspector** API endpoint. If missing,
  the endpoint will be fetched from the service catalog.

* ``--inspector-api-version`` requested API version, see :ref:`api-versioning`
  for details.

Start introspection on a node
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    $ openstack baremetal introspection start [--wait] [--new-ipmi-password=PWD [--new-ipmi-username=USER]] UUID [UUID ...]

* ``UUID`` - Ironic node UUID;
* ``new-ipmi-username`` and ``new-ipmi-password`` - if these are set,
  **Ironic Inspector** will switch to manual power on and assigning IPMI
  credentials on introspection. See `Setting IPMI Credentials`_ for details.

Note that the CLI call accepts several UUID's and will stop on the first error.

.. note::
    This CLI call doesn't rely on Ironic, and the introspected node will be
    left in ``MANAGEABLE`` state. This means that the Ironic node is not
    protected from other operations being performed by Ironic, which could
    cause inconsistency in the node's state, and lead to operational errors.

With ``--wait`` flag it waits until introspection ends for all given nodes,
then displays the results as a table.

Query introspection status
~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    $ openstack baremetal introspection status UUID

* ``UUID`` - Ironic node UUID.

Returns following information about a node introspection status:

* ``error``: an error string or ``None``
* ``finished``: ``True/False``
* ``finished_at``: an ISO8601 timestamp or ``None`` if not finished
* ``started_at``: an ISO8601 timestamp
* ``uuid``: node UUID

Retrieving introspection data
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    $ openstack baremetal introspection data save [--file=file_name] UUID

* ``UUID`` - Ironic node UUID;
* ``file_name`` - file name to save data to. If file name is not provided,
  the data is dumped to stdout.

.. note::
    This feature requires Swift support to be enabled in **Ironic Inspector**
    by setting ``[processing]store_data`` configuration option to ``swift``.

Aborting introspection
~~~~~~~~~~~~~~~~~~~~~~

::

  $ openstack baremetal introspection abort UUID

* ``UUID`` - Ironic node UUID.

Reprocess stored introspection data
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    $ openstack baremetal introspection reprocess UUID

* ``UUID`` - Ironic node UUID.

.. note::
   This feature requires Swift store to be enabled for **Ironic Inspector**
   by setting ``[processing]store_data`` configuration option to ``swift``.

Introspection Rules API
~~~~~~~~~~~~~~~~~~~~~~~

Creating a rule
^^^^^^^^^^^^^^^

::

    $ openstack baremetal introspection rule import <JSON FILE>

* ``rule_json`` dictionary with a rule representation, see
  :py:meth:`ironic_inspector_client.RulesAPI.from_json` for details.

Listing all rules
^^^^^^^^^^^^^^^^^

::

    $ openstack baremetal introspection rule list

Returns list of short rule representations, containing only description, UUID
and links.

Deleting all rules
^^^^^^^^^^^^^^^^^^

::

    $ openstack baremetal introspection rule purge

Deleting a rule
^^^^^^^^^^^^^^^

::

    $ openstack baremetal introspection rule delete <UUID>

* ``UUID`` rule UUID.

Using names instead of UUID
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Starting with baremetal introspection API 1.5 (provided by **Ironic Inspector**
3.3.0) it's possible to use node names instead of UUIDs in all Python and CLI
calls.


.. _Setting IPMI Credentials: http://docs.openstack.org/developer/ironic-inspector/usage.html#setting-ipmi-credentials
.. _introspection rules documentation: http://docs.openstack.org/developer/ironic-inspector/usage.html#introspection-rules
