###############################################################################
#
# Copyright 2018 by Shoobx, Inc.
#
###############################################################################
"""Shoobx S3 Config Test
"""

import os
import shutil
import tempfile
import unittest

from shoobx.mocks3 import config

TEST_CONFIG = '''
[shoobx:mocks3]
log-level = INFO
directory = %s
hostname = localhost
'''


class MockS3ConfigTests(unittest.TestCase):

    def setUp(self):
        self._dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self._dir)

    def test_configure(self):
        config_path = os.path.join(self._dir, 'config.ini')
        with open(config_path, 'w') as file:
            file.write(TEST_CONFIG % self._dir)
        app = config.configure(config_path)
        self.assertEqual('s3-sbx', app.service)
