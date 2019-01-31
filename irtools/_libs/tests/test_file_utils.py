#! /usr/bin/env python

# Standard Imports
import unittest
import time
import datetime

# irtools Imports
from irtools import *
from irtools._libs import file_utils

# Logging
log = logging.getLogger('irtools.lib_tests.file_utils')
utils.logging_setup(level=0, log_file=ir_log_dir + '/test_lib_file_utils.log')


class TestFileSmartCopy(unittest.TestCase):

    def test_file_to_file_dst_dir_exists(self):
        src_path = utils.write_to_tmp_file('test_file_to_file_dst_dir_exists')
        dst_dir = utils.check_makedir(utils.get_tmp_dir())
        dst_path = os.path.join(dst_dir, 'test_file_to_file_dst_dir_exists.dst')

        file_utils.smart_copy(src_path, dst_path)
        self.assertTrue(os.path.exists(dst_path))
        self.assertEqual('test_file_to_file_dst_dir_exists', utils.read_file(dst_path, as_str=True))

    def test_file_to_file_dst_dir_missing(self):
        src_path = utils.write_to_tmp_file('test_file_to_file_dst_dir_missing')
        dst_dir = os.path.join(utils.get_tmp_dir(), 'missing_dir')
        utils.clean_paths(dst_dir)
        dst_path = os.path.join(dst_dir, 'test_file_to_file_dst_dir_missing.dst')

        file_utils.smart_copy(src_path, dst_path)
        self.assertTrue(os.path.exists(dst_path))
        self.assertEqual('test_file_to_file_dst_dir_missing', utils.read_file(dst_path, as_str=True))
