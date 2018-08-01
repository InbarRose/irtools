#! /usr/bin/env python

# Standard Imports
import re
from datetime import datetime

# Lib Imports
from sort_utils import natural_keys_floats

# irtools Imports
from irtools import *

# logging
log = logging.getLogger('irtools.utils.string')

# normalize regex
NORMALIZE_WHITESPACE_PATTERN = r'\s+'
NORMALIZE_WHITESPACE_RE = re.compile(NORMALIZE_WHITESPACE_PATTERN)
datestring_frmt = '%Y%m%d%H%M%S'
datestring_pretty_frmt = '%Y-%m-%d %H:%M:%S'


def normalize_whitespace(text):
    """Reduce all whitespace to one space"""
    return NORMALIZE_WHITESPACE_RE.sub(' ', text)


def sanitize(text):
    """Replaces whitespaces with underscores and removes any special characters (not \w) and converts to lowercase"""
    return re.sub(r'\W', '', re.sub(r'\s+', '_', text)).lower()


def convert_number_to_string(number):
    """
    converts numbers into string, doesn't matter what format the number is in. will make it a string.
    verifies that there is just ONE number in the value being converted.
    :param number: number to convert to string
    :return: returns a string that represents a number (float)
    """
    string_of_number = str(number)
    if string_is_float(string_of_number):
        return string_of_number
    lst = natural_keys_floats(string_of_number)
    if len(lst) == 1:
        return lst[0]  # the single number
    else:
        raise ValueError('found multiple numbers in conversion: number={} conversion={}'.format(number, lst), number)


def string_is_float(text):
    """checks if a string is a float"""
    try:
        float(text)
    except ValueError:
        return False
    return True


def get_datestring():
    """get a string that is the current datetime for use in logging or such (%Y%m%d%H%M%S)"""
    return datetime.now().strftime(datestring_frmt)


def get_datestring_pretty():
    """get a string that is the current datetime, in a pretty format ('%Y-%m-%d %H:%M:%S')"""
    return datetime.now().strftime(datestring_pretty_frmt)


def xor_text(text, xor_key, **kwargs):
    """
    # uses xor to encrypt/decrypt some text given a xor_key
    >>> text = "Hello, World!"
    >>> xor_key = "secret"
    >>> encrypted = xor_text(text, xor_key)
    >>> encrypted
    ';\x00\x0f\x1e\nXS2\x0c\x00\t\x10R'
    >>> decrypted = xor_text(encrypted, xor_key)
    >>> print decrypted
    Hello, World!
    # warning, this is simple to break:
    >>> codebreak = xor_text("      ", xor_key)
    >>> print codebreak
    SECRET
    # copied from https://stackoverflow.com/a/2612877/1561176
    :param text: the text to xor
    :param xor_key: the xor key to use
    :param kwargs:
    :return:
    """
    # we must multiply the key so that it will extend over the whole text
    xor_key_multiplier = int(len(text) / len(xor_key)) + 1
    return ''.join(chr(ord(s) ^ ord(c)) for s, c in zip(text, xor_key * xor_key_multiplier))


def frmt_dict(d, **kwargs):
    """does some custom formatting to display a dictionary as a string, should be deprecated in favor of JSON"""
    join_on = kwargs.get('join_on', '\n')
    frmt_str = kwargs.get('frmt_str', '{}: {}')
    indent = kwargs.pop('indent', 0)
    indent_up = kwargs.get('indent_up', 4)
    indent_char = kwargs.get('indent_char', ' ')
    cur_space = indent_char * indent
    frmt_str = '{}{}'.format(cur_space, frmt_str)
    embedded = kwargs.get('embedded', True)

    def _handle_v(v):
        new_dent = indent + indent_up
        if embedded and isinstance(v, dict) and v:
            return '\n{}'.format(frmt_dict(v, indent=new_dent, **kwargs))
        if isinstance(v, (list, set, tuple)) and v:
            list_join = '\n{}\n'.format(new_dent * indent_char)
            list_base = '[\n{{}}\n{}]'.format(indent_char * indent)
            return list_base.format(list_join.join([frmt_dict(i, indent=new_dent, **kwargs) if isinstance(i, dict) else
                                                   '{}{}'.format(new_dent * indent_char, i) for i in v]))
        if isinstance(v, (str, unicode)):
            return v.replace('\n', '\n{}'.format((1 + new_dent) * indent_char))
        return v

    return join_on.join(frmt_str.format(k, _handle_v(v)) for k, v in sorted(d.items()))


def get_common_string(list_of_strings, **kwargs):
    """get the longest common substring from a list of strings"""

    # http://stackoverflow.com/questions/2892931/longest-common-substring-from-more-than-two-strings-python
    def long_substr(data):
        substr = ''
        if len(data) > 1 and len(data[0]) > 0:
            for i in range(len(data[0])):
                for j in range(len(data[0]) - i + 1):
                    if j > len(substr) and is_substr(data[0][i:i + j], data):
                        substr = data[0][i:i + j]
        return substr

    def is_substr(find, data):
        if len(data) < 1 and len(find) < 1:
            return False
        for i in range(len(data)):
            if find not in data[i]:
                return False
        return True

    min_str_len = kwargs.pop('min_str_len', 2)
    min_res_len = kwargs.pop('min_res_len', 4)

    def get_repl(res, c):
        replacement = res.replace(c, '')
        if len(replacement) < min_res_len:
            return res
        return replacement

    if kwargs.pop('make_map', False):
        rev_map = {s: s for s in list_of_strings}
        strip_numbers = kwargs.pop('strip_numbers', False)
        passes = kwargs.pop('passes', 1)
        assert isinstance(passes, int)
        for _ in range(passes):
            chunk = long_substr(rev_map.values())
            if strip_numbers:
                chunk = chunk.strip('0123456789')
            if len(chunk) < min_str_len:
                continue
            rev_map = {k: get_repl(v, chunk) for k, v in rev_map.items()}
        return rev_map

    return long_substr(list_of_strings)


def bool_from_text(text, include_none=True, ignore_non_bool=True, raise_on_fail=True):
    """
    converts text into Bool (or None)
    :param text: the text to convert
    :param include_none: is None valid? (default True)
    :param ignore_non_bool: is a non Bool/None okay? (default True) if not, will raise... if we raise
    :param raise_on_fail: if we should raise an exception if we can't convert or we don't ignore non Bool/None
    :return: the Bool / None (or the text)
    """
    if text == 'True':
        return True
    elif text == 'False':
        return False
    elif include_none and text == 'None':
        return None
    elif ignore_non_bool:
        return text
    elif raise_on_fail:
        raise ValueError('text is not bool: text={}'.format(text))
    else:
        log.warn('text is not bool: text={}'.format(text))
        return text


def convert_list_of_string_params_to_dict(params, splitter='=', as_bools=False):
    """
    converts a list of string params (x=y) into a dictionary
    should be the opposite of `convert_dict_params_to_list_of_string` function

    # Can handle list of normal params
    >>> convert_list_of_string_params_to_dict(['x=y', 'abc=123'])
    {'x': 'y', 'abc': '123'}
    # Can handle params that are bool/None and text
    >>> convert_list_of_string_params_to_dict(['param1=True', 'param2=False', 'var=None', 'bad=false'], as_bools=True)
    {'var': None, 'bad': 'false', 'param2': False, 'param1': True}
    # Can handle "flags" with no value (makes them True)
    >>> convert_list_of_string_params_to_dict(['flag', 'param=value'], as_bools=True)
    {'flag': True, 'param': 'value'}
    # But only handles flags to True when you specify, otherwise they are params with no values
    >>> convert_list_of_string_params_to_dict(['flag', 'param=value'], as_bools=False)
    {'flag': '', 'param': 'value'}

    :param params:
    :param splitter:
    :param as_bools:
    :return:
    """
    parts = ((k.strip(), v.strip()) for k, _, v in (seg.partition(splitter) for seg in params))
    return {k: (bool_from_text(v or True) if as_bools else v) for k, v in parts if k}


def convert_dict_params_to_list_of_string(params, splitter='='):
    """
    converts a dictionary into a list of string params (x=y)
    should be the opposite of `convert_list_of_string_params_to_dict` function

    # easily handles strings
    >>> convert_dict_params_to_list_of_string({'x': 'y', 'abc': '123'})
    ['x=y', 'abc=123']
    # also handles bools / None
    >>> convert_dict_params_to_list_of_string({'var': None, 'bad': 'false', 'param': True, 'other_param': False})
    ['var=None', 'bad=false', 'param=True', 'other_param=False']
    # even when those were flags before (they are normal now)
    >>> convert_dict_params_to_list_of_string({'flag': True, 'param': 'value'})
    ['flag=True', 'param=value']
    # but - WARNING - has problem with "flags", best not to use empty values.
    >>> convert_dict_params_to_list_of_string({'flag': '', 'param': 'value'})
    ['flag=', 'param=value']

    :param params:
    :param splitter:
    :return:
    """
    return ['{k}{s}{v}'.format(k=k, s=splitter, v=v) for k, v in params.items()]


def utils_args_kwargs_str(*args, **kwargs):
    """conveniently apply conversion to args and kwargs into a combined string for use with utils.py"""
    return ' '.join([utils_args_str(*args), utils_kwargs_str(**kwargs)])


def utils_args_str(*args):
    """format a list of args for use with utils.py"""
    return ' '.join(['--arg={}'.format(arg) for arg in args])


def utils_kwargs_str(**kwargs):
    """format a list of kwargs for use with utils.py"""
    return ' '.join(['--kwarg={}={}'.format(k, v) for k, v in kwargs.items()])


__all__ = [
    # normalization
    'normalize_whitespace', 'sanitize',
    # string generating
    'get_datestring_pretty', 'get_datestring',
    # structured object formatting into string
    'frmt_dict',
    # string utilities
    'get_common_string', 'convert_number_to_string', 'string_is_float',
    # parameter formatting
    'convert_dict_params_to_list_of_string', 'convert_list_of_string_params_to_dict', 'bool_from_text',
    'utils_args_kwargs_str', 'utils_args_str', 'utils_kwargs_str',
]
