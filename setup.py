#!/usr/bin/env python3
# TODO(dschuyler): !/usr/bin/python -O

# Copyright 2019 Google Inc.
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

from setuptools import setup
from setuptools import find_packages
from datetime import datetime
import io
import os

here = os.path.abspath(os.path.dirname(__file__))

def get_long_description():
  # Read the long-description from a file.
  with io.open(os.path.join(here, 'readme.md'), encoding='utf-8') as f:
    return '\n' + f.read()

setup(
    name='ci_edit',
    version=datetime.strftime(datetime.today(), "%Y%m%d"),
    description='A terminal text editor with mouse support and ctrl+Q to quit.',
    long_description=get_long_description(),
    long_description_content_type='text/markdown',
    maintainer='Dave Schuyler',
    maintainer_email='dschuyler@chromium.org',
    url='https://github.com/google/ci_edit',
    classifiers=[
        "Programming Language :: Python :: 3",
        "Environment :: Console",
        "Environment :: Console :: Curses",
        "License :: OSI Approved :: Apache Software License",
        "Topic :: Text Editors",
    ],
    packages=find_packages(),
    scripts=['ci.py'],
    license='Apache 2.0',
)
