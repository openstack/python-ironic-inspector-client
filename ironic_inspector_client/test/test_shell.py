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

import mock
from openstackclient.tests import utils
import tempfile

from ironic_inspector_client import shell
from ironic_inspector_client import v1


class BaseTest(utils.TestCommand):
    def setUp(self):
        super(BaseTest, self).setUp()
        self.client = mock.Mock(spec=['rules'],
                                rules=mock.Mock(spec=v1._RulesAPI))
        self.api = self.client.rules
        self.app.client_manager.baremetal_introspection = self.client


class TestRules(BaseTest):
    def test_import_single(self):
        f = tempfile.NamedTemporaryFile()
        self.addCleanup(f.close)
        f.write(b'{"foo": "bar"}')
        f.flush()

        arglist = [f.name]
        verifylist = [('file', f.name)]

        cmd = shell.RuleImportCommand(self.app, None)
        parsed_args = self.check_parser(cmd, arglist, verifylist)
        cmd.take_action(parsed_args)

        self.api.from_json.assert_called_once_with({'foo': 'bar'})

    def test_import_multiple(self):
        f = tempfile.NamedTemporaryFile()
        self.addCleanup(f.close)
        f.write(b'[{"foo": "bar"}, {"answer": 42}]')
        f.flush()

        arglist = [f.name]
        verifylist = [('file', f.name)]

        cmd = shell.RuleImportCommand(self.app, None)
        parsed_args = self.check_parser(cmd, arglist, verifylist)
        cmd.take_action(parsed_args)

        self.api.from_json.assert_any_call({'foo': 'bar'})
        self.api.from_json.assert_any_call({'answer': 42})

    def test_list(self):
        self.api.get_all.return_value = [
            {'uuid': '1', 'description': 'd1', 'links': []},
            {'uuid': '2', 'description': 'd2', 'links': []}
        ]

        cmd = shell.RuleListCommand(self.app, None)
        parsed_args = self.check_parser(cmd, [], [])
        cols, values = cmd.take_action(parsed_args)

        self.assertEqual(('UUID', 'Description'), cols)
        self.assertEqual([('1', 'd1'), ('2', 'd2')], values)
        self.api.get_all.assert_called_once_with()

    def test_show(self):
        self.api.get.return_value = {
            'uuid': 'uuid1',
            'links': [],
            'description': 'd',
            'conditions': [{}],
            'actions': [{}]
        }
        arglist = ['uuid1']
        verifylist = [('uuid', 'uuid1')]

        cmd = shell.RuleShowCommand(self.app, None)
        parsed_args = self.check_parser(cmd, arglist, verifylist)
        cols, values = cmd.take_action(parsed_args)

        self.assertEqual(('actions', 'conditions', 'description', 'uuid'),
                         cols)
        self.assertEqual(([{}], [{}], 'd', 'uuid1'), values)
        self.api.get.assert_called_once_with('uuid1')

    def test_delete(self):
        arglist = ['uuid1']
        verifylist = [('uuid', 'uuid1')]

        cmd = shell.RuleDeleteCommand(self.app, None)
        parsed_args = self.check_parser(cmd, arglist, verifylist)
        cmd.take_action(parsed_args)

        self.api.delete.assert_called_once_with('uuid1')

    def test_purge(self):
        cmd = shell.RulePurgeCommand(self.app, None)
        parsed_args = self.check_parser(cmd, [], [])
        cmd.take_action(parsed_args)

        self.api.delete_all.assert_called_once_with()
