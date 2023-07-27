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
from unittest import mock

from shoobx.mocks3 import config

TEST_CONFIG = """
[shoobx:mocks3]
log-level = INFO
directory = %s
hostname = localhost
"""


class MockS3ConfigTests(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self._dir)
        config._CONFIG = None
        config.CONFIG_FILE = None

    def test_configure(self):
        config_path = os.path.join(self._dir, "config.ini")
        with open(config_path, "w") as file:
            file.write(TEST_CONFIG % self._dir)
        app = config.configure(config_path)
        self.assertEqual("s3-sbx", app.service)

    @mock.patch.object(os, "environ", {"name": "Jane", "NAME": "Joe"})
    def test_configure_dupe_env_key(self):
        config_path = os.path.join(self._dir, "config.ini")
        with open(config_path, "w") as file:
            file.write(TEST_CONFIG % self._dir)
        # Ensure loading does not fail.
        config.configure(config_path)
