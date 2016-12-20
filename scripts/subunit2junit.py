"""
Convert subunit stream to JUnix XML

Usage:
    $ bin/test --subunit | subunit2junit.py testresult.xml
"""
import sys
import optparse

from subunit import ProtocolTestCase
from junitxml import JUnitXmlResult

parser = optparse.OptionParser('bin/test --subunit | %prog testresult.xml')


def main():
    opts, args = parser.parse_args()
    if len(args) != 1:
        parser.error('expected one output file name')

    if sys.stdout.isatty():
        forward = None
    else:
        forward = sys.stdout

    with open(args[0], 'wb') as outfile:
        result = JUnitXmlResult(outfile)
        test = ProtocolTestCase(sys.stdin, forward=forward)
        result.startTestRun()
        test.run(result)
        result.stopTestRun()

    if not result.wasSuccessful():
        sys.exit(1)

if __name__ == '__main__':
    main()
