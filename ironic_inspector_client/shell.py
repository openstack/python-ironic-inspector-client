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
import logging
import sys

from cliff import command
from cliff import lister
from cliff import show
from openstackclient.common import utils

import ironic_inspector_client


LOG = logging.getLogger('ironic_inspector.shell')
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


class StartCommand(lister.Lister):
    """Start the introspection."""

    COLUMNS = ('UUID', 'Error')

    def get_parser(self, prog_name):
        parser = super(StartCommand, self).get_parser(prog_name)
        parser.add_argument('uuid', help='baremetal node UUID(s)', nargs='+')
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
        for uuid in parsed_args.uuid:
            client.introspect(uuid,
                              new_ipmi_username=parsed_args.new_ipmi_username,
                              new_ipmi_password=parsed_args.new_ipmi_password)
        if parsed_args.new_ipmi_password:
            print('Setting IPMI credentials requested, please power on '
                  'the machine manually', file=sys.stderr)

        if parsed_args.wait:
            print('Waiting for introspection to finish...', file=sys.stderr)
            result = client.wait_for_finish(parsed_args.uuid)
            result = [(uuid, s.get('error'))
                      for uuid, s in result.items()]
        else:
            result = []

        return self.COLUMNS, result


class ReprocessCommand(command.Command):
    """Reprocess stored introspection data"""

    def get_parser(self, prog_name):
        parser = super(ReprocessCommand, self).get_parser(prog_name)
        parser.add_argument('uuid', help='baremetal node UUID')
        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.baremetal_introspection
        client.reprocess(parsed_args.uuid)


class StatusCommand(show.ShowOne):
    """Get introspection status."""

    def get_parser(self, prog_name):
        parser = super(StatusCommand, self).get_parser(prog_name)
        parser.add_argument('uuid', help='baremetal node UUID')
        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.baremetal_introspection
        status = client.get_status(parsed_args.uuid)
        return zip(*sorted(status.items()))


class AbortCommand(command.Command):
    """Abort running introspection for node."""

    def get_parser(self, prog_name):
        parser = super(AbortCommand, self).get_parser(prog_name)
        parser.add_argument('uuid', help='baremetal node UUID')
        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.baremetal_introspection
        client.abort(parsed_args.uuid)


class RuleImportCommand(command.Command):
    """Import one or several introspection rules from a json file."""

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
        for rule in rules:
            client.rules.from_json(rule)


class RuleListCommand(lister.Lister):
    """List all introspection rules."""

    COLUMNS = ("UUID", "Description")

    def take_action(self, parsed_args):
        client = self.app.client_manager.baremetal_introspection
        rules = client.rules.get_all()
        rules = [tuple(rule.get(col.lower()) for col in self.COLUMNS)
                 for rule in rules]
        return self.COLUMNS, rules


class RuleShowCommand(show.ShowOne):
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
        parser.add_argument('uuid', help='baremetal node UUID')
        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.baremetal_introspection
        data = client.get_data(parsed_args.uuid,
                               raw=bool(parsed_args.file))
        if parsed_args.file:
            with open(parsed_args.file, 'wb') as fp:
                fp.write(data)
        else:
            json.dump(data, sys.stdout)
