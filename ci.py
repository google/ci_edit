#!/usr/bin/env python3
# TODO(dschuyler): !/usr/bin/python -O

# Copyright 2016 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import sys

def version_check():
    if sys.version_info[0] <= 2:
        msg = """

Hi,

  Are you able to use Python 3? Please use ci_edit with Python 3. Doing so will
avoid this message.

In the future ci_edit will be dropping support for Python 2.

I/we are not able to 'see' how many users are currently using Python 2. This is
for your safety/privacy. The ci_edit program is not permitted to send
information about you back to us. So for us to know if you need Python 2 support
we need you to tell us. If you need Python 2 support please report (make a
comment) here: https://github.com/google/ci_edit/issues/205

In the near term, you can also avoid this message by passing --p2 on the command
line when running ci_edit.

"""
        print(msg)
        sys.exit(1)

if __name__ == '__main__':
    args = sys.argv
    if '--test' in args:
        import unit_tests
        args.remove('--test')
        sys.exit(unit_tests.parseArgList(args))
    if '--p2' not in args:
        version_check()
    else:
        args.remove('--p2')
    if '--strict' in args:
        import app.config
        args.remove('--strict')
        app.config.strict_debug = True
    import app.ci_program
    app.ci_program.run_ci()
