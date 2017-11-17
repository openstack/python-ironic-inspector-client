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

import types
import unittest

import ironic_inspector_client


class TestExposedAPI(unittest.TestCase):
    def test_only_client_all_exposed(self):
        exposed = {x for x in dir(ironic_inspector_client)
                   if not x.startswith('__') and
                   not isinstance(getattr(ironic_inspector_client, x),
                                  types.ModuleType)}
        self.assertEqual({'ClientV1', 'ClientError', 'EndpointNotFound',
                          'VersionNotSupported',
                          'MAX_API_VERSION', 'DEFAULT_API_VERSION'},
                         exposed)
