Library User Reference
======================

To use Python API first create a ``ClientV1`` object::

    import ironic_inspector_client
    client = ironic_inspector_client.ClientV1(session=keystone_session)

This code creates a client with API version *1.0* and a given `Keystone
session`_.  The service URL is fetched from the service catalog in this case.
See :py:class:`ironic_inspector_client.ClientV1` documentation for details.

.. _api-versioning:

API Versioning
--------------

Starting with version 2.1.0 **Ironic Inspector** supports optional API
versioning. Version is a tuple (X, Y), where X is always 1 for now.

The server has maximum and minimum supported versions. If no version is
requested, the server assumes the maximum it's supported.

Two constants are exposed for convenience:

* :py:const:`ironic_inspector_client.DEFAULT_API_VERSION`
* :py:const:`ironic_inspector_client.MAX_API_VERSION`


API Reference
-------------

.. toctree::
   :maxdepth: 2

   api/ironic_inspector_client

.. toctree::
   :hidden:

   api/modules

.. _Keystone session: https://docs.openstack.org/keystoneauth/latest/using-sessions.html
