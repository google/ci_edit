# Copyright 2018 Google Inc.
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

import os

import app.config


def guess(cliFiles, openToLine):
    """Guess whether unrecognized file paths refer to another file.

    Passing non-None in openToLine disables guessing. Otherwise the code will
    try to convert an unrecognized path to an exiting file.
    E.g.
    In `git diff` an 'a/' or 'b/' may be prepended to the path. Or in a compiler
    error ':<line number>' may be appended. If the file doesn't exist as-is, try
    removing those decorations, and if that exists use that path instead.
    """
    if app.config.strict_debug:
        assert isinstance(cliFiles, list)
        assert openToLine is None or isinstance(openToLine, int)
    if openToLine is not None:
        return cliFiles, openToLine
    out = []
    for file in cliFiles:
        path = file['path']
        if os.path.isfile(path):
            out.append({'path': path})
            continue
        if len(path) > 2 and path[1] == '/':
            if os.path.isfile(path[2:]):
                out.append({'path': path[2:]})
                continue
        index = path.rfind(':')
        if index != -1 and os.path.isfile(path[:index]):
            out.append({'path': path[:index]})
            openToLine = int(path[index + 1:])
            continue
        out.append({'path': path})
    return out, openToLine

def expandFullPath(path):
    if path.startswith(u"//"):
        cwd = os.getcwd()
        # TODO(dschuyler): make this not a hack (make it configurable).
        index = cwd.find(u"/fuchsia")
        if index >= 0:
            path = cwd[:index + 8] + path[1:]
    return os.path.abspath(os.path.expanduser(os.path.expandvars(path)))
