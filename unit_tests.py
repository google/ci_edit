#!/usr/bin/python
import tests.selectable_tests
import tests.text_buffer_tests
import unittest

if __name__ == '__main__':
  print "starting unit tests"

  suite = unittest.TestLoader().loadTestsFromTestCase(tests.selectable_tests.SelectableTestCases)
  unittest.TextTestRunner(verbosity=2).run(suite)

  suite = unittest.TestLoader().loadTestsFromTestCase(tests.text_buffer_tests.TextBufferTestCases)
  unittest.TextTestRunner(verbosity=2).run(suite)
