#! /usr/bin/env python

# Standard Imports
import re

# irtools Imports
from irtools import *

# logging
log = logging.getLogger('irtools.utils.sort')

float_pattern = r'([+-]?(?:[0-9]+(?:[.][0-9]*)?|[.][0-9]+))'
float_regex = re.compile(float_pattern)


def atoi(text):
    """
    helper for natural_keys
    attempt to convert text to int, or return text
    :param text: arbitrary text
    :return: int if succeeded to convert, the input text as is otherwise
    """
    return int(text) if text.isdigit() else text


def atof(text):
    """
    helper for natural_keys
    attempt to convert text to float, or return text
    :param text: arbitrary text
    :return: float if succeeded to convert, the input text as is otherwise
    """
    try:
        retval = float(text)
    except ValueError:
        retval = text
    return retval


def is_non_empty_string(str_):
    """checks if a string is not an empty string, True if not empty"""
    return bool(str_ != '')


def natural_keys_floats(text):
    """
    https://stackoverflow.com/a/5967539/1561176
    alist.sort(key=natural_keys_floats) sorts in human order
    http://nedbatchelder.com/blog/200712/human_sorting.html
    float regex comes from https://stackoverflow.com/a/12643073/190597
    :param text: arbitrary text to use as a sort key
    """
    return filter(is_non_empty_string, [atof(c) for c in float_regex.split(text)])


def natural_keys(text):
    """
    http://stackoverflow.com/a/5967539/1561176
    alist.sort(key=natural_keys) sorts in human order
    http://nedbatchelder.com/blog/200712/human_sorting.html
    :param text: arbitrary text to use as a sort key
    """
    return [atoi(c) for c in re.split('(\d+)', text)]


__all__ = ['atoi', 'atof', 'natural_keys', 'natural_keys_floats']
