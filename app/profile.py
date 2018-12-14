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

import time

profiles = {}


def start():
    return time.time()


def current(key, value):
    profiles[key] = value


def highest(key, value):
    if value > profiles.get(key):
        profiles[key] = value


def lowest(key, value):
    if value < profiles.get(key, value):
        profiles[key] = value


def highestDelta(key, startTime):
    delta = time.time() - startTime
    if delta > profiles.get(key):
        profiles[key] = delta


def runningDelta(key, startTime):
    delta = time.time() - startTime
    bleed = 0.501
    profiles[key] = delta * bleed + profiles.get(key, delta) * (1 - bleed)


def results():
    return "one\ntwo\nthree"


#----------------------------
# TODO(dschuyler): consider moving this python profile code out of this file.
import app.log
import cProfile
import pstats
import io


def beginPythonProfile():
    profile = cProfile.Profile()
    profile.enable()
    return profile


def endPythonProfile(profile):
    profile.disable()
    output = io.StringIO.StringIO()
    stats = pstats.Stats(profile, stream=output).sort_stats('cumulative')
    stats.print_stats()
    app.log.info(output.getvalue())
