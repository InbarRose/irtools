#! /usr/bin/env python

# Standard Imports
import json
import functools

# Lib Imports
from file_utils import write_file, check_makedir

# irtools Imports
from irtools import *

# logging
log = logging.getLogger('irtools.utils.report')


def json_serializer(obj, debug=False):
    """serializer for json for many of the objects in the library"""
    # todo: move to serializing lib
    try:
        return obj.to_dict()
    except AttributeError:
        try:
            return vars(obj)
        except (ValueError, TypeError) as exc:
            if debug:
                log.error('json serialize object failed: exc={} obj={} type={} repr={} dir={}'.format(
                    exc, obj, type(obj), repr(obj), dir(obj)), exc_info=True)
            return str(obj)


def create_json_report(data, file_name, debug=False):
    """
    Create a JSON file with the report content
    :param data: extra dictionary information to serialize
    :param file_name: path to create report
    :param debug: json debug
    :return: filename that was written
    """
    if debug:
        func = functools.partial(json_serializer, debug=True)
    else:
        func = json_serializer
    try:
        json_str = json.dumps(data, sort_keys=True, indent=4, default=func)
    except (TypeError, ValueError) as exc:
        log.error('Exception serializing json: exc={}'.format(exc))
        if debug:
            log.error('json serialize dumps failed: exc={} obj={} type={} repr={} dir={}'.format(
                exc, data, type(data), repr(data), dir(data)), exc_info=True)
    else:
        return write_file(file_name, json_str)


def junit_stdout_safe_format(stdout, **kwargs):
    """
    tries to safely escape any stdout passed to junit, to use this function simply pass the following:
    stdout_format=utils.junit_stdout_safe_format
    when calling utils.create_junit_results
    :param stdout:
    :return:
    """
    error_message = kwargs.pop('error_message', 'STDOUT contained bad characters')
    suite_name = kwargs.pop('suite_name', None)
    test_name = kwargs.pop('test_name', None)
    try:
        try:
            unicode(stdout)
        except UnicodeError:
            return junit_stdout_safe_format(stdout.decode(errors='replace'))
        else:
            return stdout
    except Exception as exc:
        log.error('Exception formatting stdout for junit: suite={} test={} exc={}'.format(suite_name, test_name, exc))
        return error_message


def create_junit_results(data, output=None, **kwargs):
    """
    Creates a Junit result, can write to a file if desired, or return xml string. (used by Jenkins)
    input either dict(dict(dict())) or dict(list(dict()))
    dict = {suite: {test: {stderr,stdout,time,class,err,fail,skip}}}
    list = {suite: [(test, {stderr,stdout,time,class,err,fail,skip})]}
    :param data: A dictionary with dict or list hierarchy
    :param output: A filename to write results to  /path/to/file/*.junit.xml
    :return: Returns an XML string if no output, else nothing.
    """
    log.debug('creating junit results: output={}'.format(output))
    stdout_format = kwargs.pop('stdout_format', None)
    test_class = kwargs.pop('test_class', None)
    package = kwargs.pop('package', None)
    from junit_xml import TestSuite, TestCase
    test_suites = []
    for suite, tests in data.items():
        test_cases = []
        for test, result in (tests if isinstance(tests, list) else tests.items()):
            tc = TestCase(test)
            stdout = result.get('stdout')
            if stdout_format is not None and callable(stdout_format):
                if hasattr(stdout_format, 'func_code') and 'kwargs' in stdout_format.func_code.co_varnames:
                    stdout = stdout_format(stdout, suite_name=suite, test_name=test, **kwargs)
                else:
                    stdout = stdout_format(stdout)
            tc.stdout = stdout
            tc.stderr = result.get('stderr')
            tc.elapsed_sec = result.get('time')
            tc.classname = result.get('class', test_class)
            err = result.get('err')
            if err:
                tc.add_error_info(*err if isinstance(err, (list, tuple)) else [err])
            fail = result.get('fail')
            if fail:
                tc.add_failure_info(*fail if isinstance(fail, (list, tuple)) else [fail])
            skip = result.get('skip')
            if skip:
                tc.add_skipped_info(*skip if isinstance(skip, (list, tuple)) else [skip])
            test_cases.append(tc)
        ts = TestSuite(suite, test_cases, package=package)
        test_suites.append(ts)

    if output:
        check_makedir(os.path.dirname(output))
        with open(output, 'w') as out:
            TestSuite.to_file(out, test_suites)
        return output
    else:
        return TestSuite.to_xml_string(test_suites)


__all__ = [
    # for test reporting
    'create_junit_results', 'junit_stdout_safe_format',
    # for object reporting (and others?)
    'create_json_report', 'json_serializer',

]
