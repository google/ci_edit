#!/usr/bin/python
import app.unit_test_parser
import app.unit_test_selectable
import app.unit_test_text_buffer
import unittest


# Add new test cases here.
tests = [
  app.unit_test_selectable.SelectableTestCases,
  app.unit_test_parser.ParserTestCases,
  app.unit_test_text_buffer.MouseTestCases,
]

def runTests(stopOnFailure=False):
  """Run through the list of tests."""
  for test in tests:
    suite = unittest.TestLoader().loadTestsFromTestCase(test)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if stopOnFailure and result.failures:
      break;

if __name__ == '__main__':
  app.log.info("starting unit tests")
  app.log.wrapper(runTests)
