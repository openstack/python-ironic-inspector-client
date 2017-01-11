
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


class InterfaceResource(object):
    """InterfaceResource class

    This class is used to manage the fields including Link Layer Discovery
    Protocols (LLDP) fields, that an interface contains.  An individual
    field consists of a 'field_id' (key) and a 'label' (value).
    """

    FIELDS = {
        'interface': 'Interface',
        'mac': 'MAC Address',
        'node_ident': 'Node',
        'switch_capabilities_enabled': 'Switch Capabilities Enabled',
        'switch_capabilities_support': 'Switch Capabilities Supported',
        'switch_chassis_id': 'Switch Chassis ID',
        'switch_port_autonegotiation_enabled':
            'Switch Port Autonegotiation Enabled',
        'switch_port_autonegotiation_support':
            'Switch Port Autonegotiation Supported',
        'switch_port_description': 'Switch Port Description',
        'switch_port_id': 'Switch Port ID',
        'switch_port_link_aggregation_enabled':
            'Switch Port Link Aggregation Enabled',
        'switch_port_link_aggregation_support':
            'Switch Port Link Aggregation Supported',
        'switch_port_link_aggregation_id': 'Switch Port Link Aggregation ID',
        'switch_port_management_vlan_id': 'Switch Port Mgmt VLAN ID',
        'switch_port_mau_type': 'Switch Port Mau Type',
        'switch_port_mtu': 'Switch Port MTU',
        'switch_port_physical_capabilities':
            'Switch Port Physical Capabilities',
        'switch_port_protocol_vlan_enabled':
            'Switch Port Protocol VLAN Enabled',
        'switch_port_protocol_vlan_support':
            'Switch Port Protocol VLAN Supported',
        'switch_port_protocol_vlan_ids': 'Switch Port Protocol VLAN IDs',
        'switch_port_untagged_vlan_id': 'Switch Port Untagged VLAN',
        'switch_port_vlans': 'Switch Port VLANs',
        'switch_port_vlan_ids': 'Switch Port VLAN IDs',
        'switch_protocol_identities': 'Switch Protocol Identities',
        'switch_system_name': 'Switch System Name'
    }

    DEFAULT_FIELD_IDS = ['interface',
                         'mac',
                         'switch_port_vlan_ids',
                         'switch_chassis_id',
                         'switch_port_id']

    def __init__(self, field_ids=None, detailed=False):
        """Create an InterfaceResource object

        :param field_ids:  A list of strings that the Resource object will
                           contain.  Each string must match an existing key in
                           FIELDS.
        :param detailed:   If True, use the all of the keys in FIELDS instead
                           of input field_ids
        """
        if field_ids is None:
            # Default field set in logical format, so don't sort
            field_ids = self.DEFAULT_FIELD_IDS

        if detailed:
            field_ids = sorted(self.FIELDS.keys())

        self._fields = tuple(field_ids)
        self._labels = tuple(self.FIELDS[x] for x in field_ids)

    @property
    def fields(self):
        return self._fields

    @property
    def labels(self):
        return self._labels


INTERFACE_DEFAULT = InterfaceResource()
