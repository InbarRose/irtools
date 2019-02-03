#! /usr/bin/env python

# Standard Imports
import unittest

# irtools Imports
from irtools import *
from irtools._libs import exec_utils

# Logging
log = logging.getLogger('irtools.lib_tests.exec_utils')
utils.logging_setup(level=0, log_file=ir_log_dir + '/test_lib_exec_utils.log')


class Testiexec(unittest.TestCase):

    def test_dump_kwargs_true(self):
        # prepare dump output file
        tmp_file = os.path.join(utils.get_tmp_dir(), 'test_dump_kwargs_true.dump.txt')
        utils.check_makedir(tmp_file)  # make sure path is clear for writing
        utils.clean_paths(tmp_file)
        # prepare command
        cmd = 'hostname'  # works on all machine types?
        # prepare kwargs
        subprocess_kwargs = {'cwd': os.getcwd()}  # add cwd explicitly to the subprocess kwargs
        command_kwargs = {
            'to_console': False,  # we don't want to spam the console with output
            'show_log': False,  # we don't need to log the process
        }
        dump_kwargs = {
            'dump_file': tmp_file,
            'dump_kwargs': True,
        }
        kwargs = {}
        kwargs.update(subprocess_kwargs)
        kwargs.update(command_kwargs)
        kwargs.update(dump_kwargs)
        # run command
        ret = exec_utils.iexec(cmd, **kwargs)
        # verify subprocess kwargs in ret.
        self.assertEquals(subprocess_kwargs, ret.subprocess_kwargs)
        # verify ret creates subprocess kwargs format correctly
        expected_kwargs_dump = '<subprocess kwargs>\n{}'.format(
                '\n'.join(['{}: {}'.format(k, v) for k, v in sorted(subprocess_kwargs.items())]))
        ret_kwargs_dump = ret.get_subprocess_kwargs_dump()
        self.assertEqual(expected_kwargs_dump, ret_kwargs_dump)
        # verify subprocess kwargs in dump file
        dump_file_contents = utils.read_file(tmp_file, as_str=True)
        self.assertIn(expected_kwargs_dump, dump_file_contents)

    def test_dump_kwargs_false(self):
        # prepare dump output file
        tmp_file = os.path.join(utils.get_tmp_dir(), 'test_dump_kwargs_false.dump.txt')
        utils.check_makedir(tmp_file)  # make sure path is clear for writing
        utils.clean_paths(tmp_file)
        # prepare command
        cmd = 'hostname'  # works on all machine types?
        # prepare kwargs
        subprocess_kwargs = {'cwd': os.getcwd()}  # add cwd explicitly to the subprocess kwargs
        command_kwargs = {
            'to_console': False,  # we don't want to spam the console with output
            'show_log': False,  # we don't need to log the process
        }
        dump_kwargs = {
            'dump_file': tmp_file,
            'dump_kwargs': False,
        }
        kwargs = {}
        kwargs.update(subprocess_kwargs)
        kwargs.update(command_kwargs)
        kwargs.update(dump_kwargs)
        # run command
        ret = exec_utils.iexec(cmd, **kwargs)
        # verify subprocess kwargs in ret.
        self.assertEquals(subprocess_kwargs, ret.subprocess_kwargs)
        # verify ret creates subprocess kwargs format correctly
        expected_kwargs_dump = '<subprocess kwargs>\n{}'.format(
            '\n'.join(['{}: {}'.format(k, v) for k, v in sorted(subprocess_kwargs.items())]))
        ret_kwargs_dump = ret.get_subprocess_kwargs_dump()
        self.assertEqual(expected_kwargs_dump, ret_kwargs_dump)
        # verify subprocess kwargs not in dump data
        ret_dump_data = ret.get_dump_data(dump_kwargs=False, as_str=False)
        self.assertNotIn('kwargs', ret_dump_data)
        # verify subprocess kwargs NOT in dump file
        dump_file_contents = utils.read_file(tmp_file, as_str=True)
        self.assertNotIn(expected_kwargs_dump, dump_file_contents)
