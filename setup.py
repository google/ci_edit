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
    author='Google Inc.',
    author_email='opensource@google.com',
    url='https://github.com/google/ci_edit',
    packages=find_packages(),
    scripts=['ci.py'],
    license='Apache 2.0',
)
