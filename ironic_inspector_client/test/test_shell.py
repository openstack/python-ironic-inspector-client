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

import sys

import mock
from openstackclient.tests import utils
import six
import tempfile

from ironic_inspector_client import shell
from ironic_inspector_client import v1


class BaseTest(utils.TestCommand):
    def setUp(self):
        super(BaseTest, self).setUp()
        self.client = mock.Mock(spec=v1.ClientV1)
        self.rules_api = mock.Mock(spec=v1._RulesAPI)
        self.client.rules = self.rules_api
        self.app.client_manager.baremetal_introspection = self.client


class TestIntrospect(BaseTest):
    def test_introspect_one(self):
        arglist = ['uuid1']
        verifylist = [('uuid', arglist)]

        cmd = shell.StartCommand(self.app, None)
        parsed_args = self.check_parser(cmd, arglist, verifylist)
        result = cmd.take_action(parsed_args)

        self.assertEqual((shell.StartCommand.COLUMNS, []), result)
        self.client.introspect.assert_called_once_with('uuid1',
                                                       new_ipmi_password=None,
                                                       new_ipmi_username=None)

    def test_introspect_many(self):
        arglist = ['uuid1', 'uuid2', 'uuid3']
        verifylist = [('uuid', arglist)]

        cmd = shell.StartCommand(self.app, None)
        parsed_args = self.check_parser(cmd, arglist, verifylist)
        cmd.take_action(parsed_args)

        calls = [mock.call(uuid, new_ipmi_password=None,
                           new_ipmi_username=None)
                 for uuid in arglist]
        self.assertEqual(calls, self.client.introspect.call_args_list)

    def test_introspect_many_fails(self):
        arglist = ['uuid1', 'uuid2', 'uuid3']
        verifylist = [('uuid', arglist)]
        self.client.introspect.side_effect = (None, RuntimeError())

        cmd = shell.StartCommand(self.app, None)
        parsed_args = self.check_parser(cmd, arglist, verifylist)
        self.assertRaises(RuntimeError, cmd.take_action, parsed_args)

        calls = [mock.call(uuid, new_ipmi_password=None,
                           new_ipmi_username=None)
                 for uuid in arglist[:2]]
        self.assertEqual(calls, self.client.introspect.call_args_list)

    def test_introspect_set_credentials(self):
        uuids = ['uuid1', 'uuid2', 'uuid3']
        arglist = ['--new-ipmi-password', '1234'] + uuids
        verifylist = [('uuid', uuids), ('new_ipmi_password', '1234')]

        cmd = shell.StartCommand(self.app, None)
        parsed_args = self.check_parser(cmd, arglist, verifylist)
        with mock.patch('sys.stdout', write=lambda s: None):
            cmd.take_action(parsed_args)

        calls = [mock.call(uuid, new_ipmi_password='1234',
                           new_ipmi_username=None)
                 for uuid in uuids]
        self.assertEqual(calls, self.client.introspect.call_args_list)

    def test_introspect_set_credentials_with_username(self):
        uuids = ['uuid1', 'uuid2', 'uuid3']
        arglist = ['--new-ipmi-password', '1234',
                   '--new-ipmi-username', 'root'] + uuids
        verifylist = [('uuid', uuids), ('new_ipmi_password', '1234'),
                      ('new_ipmi_username', 'root')]

        cmd = shell.StartCommand(self.app, None)
        parsed_args = self.check_parser(cmd, arglist, verifylist)
        with mock.patch('sys.stdout', write=lambda s: None):
            cmd.take_action(parsed_args)

        calls = [mock.call(uuid, new_ipmi_password='1234',
                           new_ipmi_username='root')
                 for uuid in uuids]
        self.assertEqual(calls, self.client.introspect.call_args_list)

    def test_reprocess(self):
        node = 'uuid1'
        arglist = [node]
        verifylist = [('uuid', node)]
        response_mock = mock.Mock(status_code=202, content=b'')
        self.client.reprocess.return_value = response_mock

        cmd = shell.ReprocessCommand(self.app, None)

        parsed_args = self.check_parser(cmd, arglist, verifylist)
        result = cmd.take_action(parsed_args)

        self.client.reprocess.assert_called_once_with(node)
        self.assertIs(None, result)

    def test_wait(self):
        nodes = ['uuid1', 'uuid2', 'uuid3']
        arglist = ['--wait'] + nodes
        verifylist = [('uuid', nodes), ('wait', True)]
        self.client.wait_for_finish.return_value = {
            'uuid1': {'finished': True, 'error': None},
            'uuid2': {'finished': True, 'error': 'boom'},
            'uuid3': {'finished': True, 'error': None},
        }

        cmd = shell.StartCommand(self.app, None)
        parsed_args = self.check_parser(cmd, arglist, verifylist)
        _c, values = cmd.take_action(parsed_args)

        calls = [mock.call(uuid, new_ipmi_password=None,
                           new_ipmi_username=None)
                 for uuid in nodes]
        self.assertEqual(calls, self.client.introspect.call_args_list)
        self.assertEqual([('uuid1', None), ('uuid2', 'boom'), ('uuid3', None)],
                         sorted(values))

    def test_abort(self):
        node = 'uuid1'
        arglist = [node]
        verifylist = [('uuid', node)]
        response_mock = mock.Mock(status_code=202, content=b'')
        self.client.abort.return_value = response_mock

        cmd = shell.AbortCommand(self.app, None)

        parsed_args = self.check_parser(cmd, arglist, verifylist)
        result = cmd.take_action(parsed_args)

        self.client.abort.assert_called_once_with(node)
        self.assertIs(None, result)


class TestGetStatus(BaseTest):
    def test_get_status(self):
        arglist = ['uuid1']
        verifylist = [('uuid', 'uuid1')]
        self.client.get_status.return_value = {'finished': True,
                                               'error': 'boom'}

        cmd = shell.StatusCommand(self.app, None)
        parsed_args = self.check_parser(cmd, arglist, verifylist)
        result = cmd.take_action(parsed_args)

        self.assertEqual([('error', 'finished'), ('boom', True)], list(result))
        self.client.get_status.assert_called_once_with('uuid1')


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

        self.rules_api.from_json.assert_called_once_with({'foo': 'bar'})

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

        self.rules_api.from_json.assert_any_call({'foo': 'bar'})
        self.rules_api.from_json.assert_any_call({'answer': 42})

    def test_list(self):
        self.rules_api.get_all.return_value = [
            {'uuid': '1', 'description': 'd1', 'links': []},
            {'uuid': '2', 'description': 'd2', 'links': []}
        ]

        cmd = shell.RuleListCommand(self.app, None)
        parsed_args = self.check_parser(cmd, [], [])
        cols, values = cmd.take_action(parsed_args)

        self.assertEqual(('UUID', 'Description'), cols)
        self.assertEqual([('1', 'd1'), ('2', 'd2')], values)
        self.rules_api.get_all.assert_called_once_with()

    def test_show(self):
        self.rules_api.get.return_value = {
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
        self.rules_api.get.assert_called_once_with('uuid1')

    def test_delete(self):
        arglist = ['uuid1']
        verifylist = [('uuid', 'uuid1')]

        cmd = shell.RuleDeleteCommand(self.app, None)
        parsed_args = self.check_parser(cmd, arglist, verifylist)
        cmd.take_action(parsed_args)

        self.rules_api.delete.assert_called_once_with('uuid1')

    def test_purge(self):
        cmd = shell.RulePurgeCommand(self.app, None)
        parsed_args = self.check_parser(cmd, [], [])
        cmd.take_action(parsed_args)

        self.rules_api.delete_all.assert_called_once_with()


class TestDataSave(BaseTest):
    def test_stdout(self):
        self.client.get_data.return_value = {'answer': 42}
        buf = six.StringIO()

        arglist = ['uuid1']
        verifylist = [('uuid', 'uuid1')]

        cmd = shell.DataSaveCommand(self.app, None)
        parsed_args = self.check_parser(cmd, arglist, verifylist)
        with mock.patch.object(sys, 'stdout', buf):
            cmd.take_action(parsed_args)
        self.assertEqual('{"answer": 42}', buf.getvalue())
        self.client.get_data.assert_called_once_with('uuid1', raw=False)

    def test_file(self):
        self.client.get_data.return_value = b'{"answer": 42}'

        with tempfile.NamedTemporaryFile() as fp:
            arglist = ['--file', fp.name, 'uuid1']
            verifylist = [('uuid', 'uuid1'), ('file', fp.name)]

            cmd = shell.DataSaveCommand(self.app, None)
            parsed_args = self.check_parser(cmd, arglist, verifylist)
            cmd.take_action(parsed_args)

            content = fp.read()

        self.assertEqual(b'{"answer": 42}', content)
        self.client.get_data.assert_called_once_with('uuid1', raw=True)
