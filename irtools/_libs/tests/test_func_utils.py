#! /usr/bin/env python

# Standard Imports
import unittest

# irtools Imports
from irtools import *
from irtools._libs import func_utils

# Logging
log = logging.getLogger('irtools.lib_tests.func_utils')
utils.logging_setup(level=0, log_file=ir_log_dir + '/test_lib_func_utils.log')


# functions / lambdas for testing
def foo_global_func():
    return None


foo_lambda = lambda: None


class TestFunc(unittest.TestCase):

    # functions for testing
    def foo_instance_method(self):
        return None

    @classmethod
    def foo_class_method(cls):
        return None

    @staticmethod
    def foo_static_method():
        return None

    def test_inner_func(self):
        # setup
        def foo_func():
            return None
        expected_name = 'foo_func'
        # fetch results
        found_name = func_utils.get_func_name(foo_func)
        # check results
        self.assertEquals(found_name, expected_name)

    def test_global_func(self):
        # setup
        expected_name = 'foo_global_func'
        # fetch results
        found_name = func_utils.get_func_name(foo_global_func)
        # check results
        self.assertEquals(found_name, expected_name)

    def test_instance_method(self):
        # setup
        expected_name = 'foo_instance_method'
        # fetch results
        found_name = func_utils.get_func_name(self.foo_instance_method)
        # check results
        self.assertEquals(found_name, expected_name)

    def test_class_method(self):
        # setup
        expected_name = 'foo_class_method'
        # fetch results
        found_name = func_utils.get_func_name(self.foo_class_method)
        # check results
        self.assertEquals(found_name, expected_name)

    def test_static_method_self(self):
        # setup
        expected_name = 'foo_static_method'
        # fetch results
        found_name_self = func_utils.get_func_name(self.foo_static_method)
        # check results
        self.assertEquals(found_name_self, expected_name)

    def test_static_method_class(self):
        # setup
        expected_name = 'foo_static_method'
        # fetch results
        found_name_class = func_utils.get_func_name(TestFunc.foo_static_method)
        # check results
        self.assertEquals(found_name_class, expected_name)

    def test_lambda_no_name(self):
        # setup
        expected_name = '<lambda>'  # lambda's are anonymous and have no names defined in the context of python
        # fetch results
        found_name = func_utils.get_func_name(foo_lambda)
        # check results
        self.assertEquals(found_name, expected_name)

    def test_lambda_raises(self):
        # fetch/check results
        self.assertRaises(RuntimeError, func_utils.get_func_name, foo_lambda, raise_on_lambda=True)
