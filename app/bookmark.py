class Bookmark:
  """
  This bookmark object is used as a marker for different places in a
  text document. Note that because text buffer lines index at 0, all
  references to rows also assume that 0 is the first line.
  """
  def __init__(self, beginRow, endRow, data=None):
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

  def __le__(self, other):
    return self.range <= other.range

  def __ge__(self, other):
    return self.range >= other.range
