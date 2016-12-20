"""
Convert subunit stream to PyUnit-ish output

Usage:
    $ bin/test --subunit | subunit2pyunit.py
"""
import sys
import optparse
import unittest

from subunit import ProtocolTestCase

parser = optparse.OptionParser('bin/test --subunit | %prog')
parser.add_option('-v', '--verbose',
                  action='count', dest='verbosity', default=0,
                  help='increment verbosity level')


def main():
    opts, args = parser.parse_args()
    if args:
        parser.error('no arguments expected')

    runner = unittest.TextTestRunner(verbosity=opts.verbosity)
    test = ProtocolTestCase(sys.stdin)
    result = runner.run(test)

    if not result.wasSuccessful():
        sys.exit(1)

if __name__ == '__main__':
    main()
