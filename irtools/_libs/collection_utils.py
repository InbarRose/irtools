#! /usr/bin/env python

# Standard Imports
from collections import Counter

# irtools Imports
from irtools import *

# logging
log = logging.getLogger('irtools.utils.collection')


def swap_key_and_value(k, v):
    return v, k


def swap_dictionary_keys_and_values(input_dict, raise_on_duplicate_values=False, swap_function=swap_key_and_value):
    if raise_on_duplicate_values:
        value_counts = Counter(input_dict.values())
        duplicates = {k: v for k, v in value_counts.items() if v > 1}
        if duplicates:
            log.error('duplicate values found in dictionary: duplicates={}'.format(duplicates))
            raise ValueError('duplicate values found in dictionary', duplicates)

    return dict(swap_function(k, v) for k, v in input_dict.iteritems())


class ReverseLookupDict(dict):
    """dictionary extension which supports reverse-lookup by value to get all matching keys"""

    def get_keys_by_value(self, value):
        """
        returns all keys matching value
        :param value: value to search for
        :return: a list of keys
        """
        return [k for k, v in self.iteritems() if v == value]

    def rget(self, value, default=None, raise_on_multiple=False, raise_on_missing=False):
        """
        returns the first key (arbitrary sort order) found matching value
        :param value: value to search for
        :param default: what default value to return if no keys found
        :param raise_on_multiple: should raise exception on multiple keys found for value
        :param raise_on_missing: should raise exception if no found for value
        :return: the key or default unless raises an exception
        """
        keys = self.get_keys_by_value(value)
        if not keys:
            if raise_on_missing:
                raise KeyError(value)  # no keys found
            return default
        if raise_on_multiple and len(keys) > 1:
            raise KeyError(value)  # multiple keys found
        return keys[0]  # return first key (arbitrary sort order)


__all__ = ['swap_dictionary_keys_and_values', 'ReverseLookupDict']
