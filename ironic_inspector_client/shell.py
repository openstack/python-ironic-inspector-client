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

"""OpenStackClient plugin for Ironic Inspector."""

from __future__ import print_function

import json
import sys

from osc_lib.command import command
from osc_lib import utils

import ironic_inspector_client
from ironic_inspector_client import resource as res

API_NAME = 'baremetal_introspection'
API_VERSION_OPTION = 'inspector_api_version'
DEFAULT_API_VERSION = '1'
API_VERSIONS = {
    "1": "ironic_inspector.shell",
}

for mversion in range(ironic_inspector_client.MAX_API_VERSION[1] + 1):
    API_VERSIONS["1.%d" % mversion] = API_VERSIONS["1"]


def make_client(instance):
    return ironic_inspector_client.ClientV1(
        inspector_url=instance.get_configuration().get('inspector_url'),
        session=instance.session,
        api_version=instance._api_version[API_NAME],
        interface=instance._interface,
        region_name=instance._region_name)


def build_option_parser(parser):
    parser.add_argument('--inspector-api-version',
                        default=utils.env('INSPECTOR_VERSION',
                                          default=DEFAULT_API_VERSION),
                        help='inspector API version, only 1 is supported now '
                        '(env: INSPECTOR_VERSION).')
    parser.add_argument('--inspector-url',
                        default=utils.env('INSPECTOR_URL', default=None),
                        help='inspector URL, defaults to localhost '
                        '(env: INSPECTOR_URL).')
    return parser


class StartCommand(command.Lister):
    """Start the introspection."""

    COLUMNS = ('UUID', 'Error')

    def get_parser(self, prog_name):
        parser = super(StartCommand, self).get_parser(prog_name)
        parser.add_argument('node', help='baremetal node UUID(s) or name(s)',
                            nargs='+')
        parser.add_argument('--new-ipmi-username',
                            default=None,
                            help='if set, *Ironic Inspector* will update IPMI '
                            'user name to this value')
        parser.add_argument('--new-ipmi-password',
                            default=None,
                            help='if set, *Ironic Inspector* will update IPMI '
                            'password to this value')
        parser.add_argument('--wait',
                            action='store_true',
                            help='wait for introspection to finish; the result'
                            ' will be displayed in the end')
        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.baremetal_introspection
        for uuid in parsed_args.node:
            client.introspect(uuid,
                              new_ipmi_username=parsed_args.new_ipmi_username,
                              new_ipmi_password=parsed_args.new_ipmi_password)
        if parsed_args.new_ipmi_password:
            print('Setting IPMI credentials requested, please power on '
                  'the machine manually', file=sys.stderr)

        if parsed_args.wait:
            print('Waiting for introspection to finish...', file=sys.stderr)
            result = client.wait_for_finish(parsed_args.node)
            result = [(uuid, s.get('error'))
                      for uuid, s in result.items()]
        else:
            result = []

        return self.COLUMNS, result


class ReprocessCommand(command.Command):
    """Reprocess stored introspection data"""

    def get_parser(self, prog_name):
        parser = super(ReprocessCommand, self).get_parser(prog_name)
        parser.add_argument('node', help='baremetal node UUID or name')
        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.baremetal_introspection
        client.reprocess(parsed_args.node)


class StatusCommand(command.ShowOne):
    """Get introspection status."""
    hidden_status_items = {'links'}

    @classmethod
    def status_attributes(cls, client_item):
        """Get status attributes from an API client dict.

        Filters the status fields according to the cls.hidden_status_items
        :param client_item: an item returned from either the get_status or the
                            list_statuses client method
        :return: introspection status as a list of name, value pairs
        """
        return [item for item in client_item.items()
                if item[0] not in cls.hidden_status_items]

    def get_parser(self, prog_name):
        parser = super(StatusCommand, self).get_parser(prog_name)
        parser.add_argument('node', help='baremetal node UUID or name')
        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.baremetal_introspection
        status = client.get_status(parsed_args.node)
        return zip(*sorted(self.status_attributes(status)))


class StatusListCommand(command.Lister):
    """List introspection statuses"""

    COLUMNS = ('UUID', 'Started at', 'Finished at', 'Error')

    @classmethod
    def status_row(cls, client_item):
        """Get a row from a client_item.

        The row columns are filtered&sorted according to cls.COLUMNS.

        :param client_item: an item returned from either the get_status or the
                            list_statuses client method.
        :return: a list of client_item attributes as the row
        """
        status = dict(StatusCommand.status_attributes(client_item))
        return utils.get_dict_properties(status, cls.COLUMNS)

    def get_parser(self, prog_name):
        parser = super(StatusListCommand, self).get_parser(prog_name)
        parser.add_argument('--marker', help='UUID of the last item on the '
                                             'previous page', default=None)
        parser.add_argument('--limit', help='the amount of items to return',
                            type=int, default=None)
        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.baremetal_introspection
        statuses = client.list_statuses(marker=parsed_args.marker,
                                        limit=parsed_args.limit)
        rows = [self.status_row(status) for status in statuses]
        return self.COLUMNS, rows


class AbortCommand(command.Command):
    """Abort running introspection for node."""

    def get_parser(self, prog_name):
        parser = super(AbortCommand, self).get_parser(prog_name)
        parser.add_argument('node', help='baremetal node UUID or name')
        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.baremetal_introspection
        client.abort(parsed_args.node)


class RuleImportCommand(command.Lister):
    """Import one or several introspection rules from a json file."""

    COLUMNS = ("UUID", "Description")

    def get_parser(self, prog_name):
        parser = super(RuleImportCommand, self).get_parser(prog_name)
        parser.add_argument('file', help='JSON file to import, may contain '
                            'one or several rules')
        return parser

    def take_action(self, parsed_args):
        with open(parsed_args.file, 'r') as fp:
            rules = json.load(fp)
            if not isinstance(rules, list):
                rules = [rules]
        client = self.app.client_manager.baremetal_introspection
        result = []
        for rule in rules:
            result.append(client.rules.from_json(rule))
        result = [tuple(rule.get(col.lower()) for col in self.COLUMNS)
                  for rule in result]
        return self.COLUMNS, result


class RuleListCommand(command.Lister):
    """List all introspection rules."""

    COLUMNS = ("UUID", "Description")

    def take_action(self, parsed_args):
        client = self.app.client_manager.baremetal_introspection
        rules = client.rules.get_all()
        rules = [tuple(rule.get(col.lower()) for col in self.COLUMNS)
                 for rule in rules]
        return self.COLUMNS, rules


class RuleShowCommand(command.ShowOne):
    """Show an introspection rule."""

    def get_parser(self, prog_name):
        parser = super(RuleShowCommand, self).get_parser(prog_name)
        parser.add_argument('uuid', help='rule UUID')
        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.baremetal_introspection
        rule = client.rules.get(parsed_args.uuid)
        del rule['links']
        return self.dict2columns(rule)


class RuleDeleteCommand(command.Command):
    """Delete an introspection rule."""

    def get_parser(self, prog_name):
        parser = super(RuleDeleteCommand, self).get_parser(prog_name)
        parser.add_argument('uuid', help='rule UUID')
        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.baremetal_introspection
        client.rules.delete(parsed_args.uuid)


class RulePurgeCommand(command.Command):
    """Drop all introspection rules."""

    def take_action(self, parsed_args):
        client = self.app.client_manager.baremetal_introspection
        client.rules.delete_all()


class DataSaveCommand(command.Command):
    """Save or display raw introspection data."""

    def get_parser(self, prog_name):
        parser = super(DataSaveCommand, self).get_parser(prog_name)
        parser.add_argument("--file", metavar="<filename>",
                            help="downloaded introspection data filename "
                            "(default: stdout)")
        parser.add_argument('node', help='baremetal node UUID or name')
        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.baremetal_introspection
        data = client.get_data(parsed_args.node,
                               raw=bool(parsed_args.file))
        if parsed_args.file:
            with open(parsed_args.file, 'wb') as fp:
                fp.write(data)
        else:
            json.dump(data, sys.stdout)


class InterfaceListCommand(command.Lister):
    """List interface data including attached switch port information."""

    def get_parser(self, prog_name):
        parser = super(InterfaceListCommand, self).get_parser(prog_name)
        parser.add_argument('node_ident', help='baremetal node UUID or name')
        parser.add_argument("--vlan",
                            action='append',
                            default=[], type=int,
                            help="List only interfaces configured "
                            "for this vlan id, can be repeated")
        display_group = parser.add_mutually_exclusive_group()
        display_group.add_argument(
            '--long', dest='detail',
            action='store_true', default=False,
            help="Show detailed information about interfaces.")
        display_group.add_argument(
            '--fields', nargs='+', dest='fields',
            metavar='<field>',
            choices=sorted(res.InterfaceResource(detailed=True).fields),
            help="Display one or more fields.  "
            "Can not be used when '--long' is specified")

        return parser

    def take_action(self, parsed_args):

        client = self.app.client_manager.baremetal_introspection

        # If --long defined, use all fields
        interface_res = res.InterfaceResource(parsed_args.fields,
                                              parsed_args.detail)

        rows = client.get_all_interface_data(parsed_args.node_ident,
                                             interface_res.fields,
                                             vlan=parsed_args.vlan)

        return interface_res.labels, rows


class InterfaceShowCommand(command.ShowOne):
    """Show interface data including attached switch port information."""

    COLUMNS = ("Field", "Value")

    def get_parser(self, prog_name):
        parser = super(InterfaceShowCommand, self).get_parser(prog_name)
        parser.add_argument('node_ident', help='baremetal node UUID or name')
        parser.add_argument('interface', help='interface name')
        parser.add_argument(
            '--fields', nargs='+', dest='fields',
            metavar='<field>',
            choices=sorted(res.InterfaceResource(detailed=True).fields),
            help="Display one or more fields.")

        return parser

    def take_action(self, parsed_args):

        client = self.app.client_manager.baremetal_introspection

        if parsed_args.fields:
            interface_res = res.InterfaceResource(parsed_args.fields)
        else:
            # Show all fields in detailed resource
            interface_res = res.InterfaceResource(detailed=True)

        iface_dict = client.get_interface_data(parsed_args.node_ident,
                                               parsed_args.interface,
                                               interface_res.fields)

        return tuple(zip(*(iface_dict.items())))
