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

class Bookmark:
  """
  This bookmark object is used as a marker for different places in a
  text document. Note that because text buffer lines index at 0, all
  references to rows also assume that 0 is the first line.
  """
  def __init__(self, beginRow, endRow, data={}):
    """
    Args:
      beginRow (int): The line that the bookmark starts on (inclusive).
      endRow (int): The line that the bookmark ends on (inclusive).
      data (other): This is used to store any information that you would like to
                    to associate with this bookmark. It can be accessed by calling
                    bookmark.getData()
    """
    self.range = (beginRow, endRow)
    self.data = data

  @property
  def begin(self):
    return self.range[0]

  @property
  def end(self):
    return self.range[1]

  def overlap(self, bookmark):
    """
    Takes in another bookmark object and returns True if this bookmark
    shares any rows with the passed in bookmark.
    """
    begin1, end1 = self.range
    begin2, end2 = bookmark.range
    return begin1 <= end2 and end1 >= begin2

  def __contains__(self, row):
    """
    Args:
      row (int): the row that you want to check.

    Returns:
      True if the passed in row is inside the bookmark's range.
    """
    assert type(row) == int
    begin, end = self.range
    return begin <= row <= end

  def __lt__(self, other):
    return self.range < other.range

  def __gt__(self, other):
    return self.range > other.range

  def __eq__(self, other):
    return self.range == other.range

  def __ne__(self, other):
    return self.range != other.range

  def __le__(self, other):
    return self.range <= other.range

  def __ge__(self, other):
    return self.range >= other.range

  def __hash__(self):
    return hash(self.range)

  def __repr__(self):
    return repr(self.range)
