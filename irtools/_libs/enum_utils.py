#! /usr/bin/env python

# irtools Imports
from irtools import *


# logging
log = logging.getLogger('irtools.utils.enum')


def dget_tkey(dictionary, tuple_key, default=None, ignore_case=True, raise_if_missing=False):
    """
    Dictionary helper function to retrieve values from dictionaries with tuple keys.
    Yields the first value found corresponding to a tuple_key found within that key.
    :param dictionary:
    :param tuple_key:
    :param default:
    :param ignore_case:
    :param raise_if_missing:
    :return:
    """
    if ignore_case:
        if isinstance(tuple_key, str):
            tuple_key = tuple_key.lower()
        else:
            ignore_case = False
    for keys, value in dictionary.iteritems():
        for key in keys:
            if ignore_case and isinstance(key, str):
                key = key.lower()
            if tuple_key != key:
                continue
            return value
    if raise_if_missing:
        raise KeyError(tuple_key)
    return default


def complex_enum_gen(**kwargs):
    """
    Create an EnumObj with kwargs as NAME=(VALUE[, list(KEYS)])
    obj.get(KEY) will return VALUE for NAME if KEY in KEYS
    obj.NAME will return VALUE also
    :param kwargs: key word arguments with tuple values NAME=(VALUE[, list(KEYS)])
    :return: enum object
    """
    fkwargs = {n: t if isinstance(t, (list, tuple)) and len(t) == 2 and isinstance(t[1], (list, tuple)) else (t, [])
               for n, t in kwargs.items()}
    enum_cls_obj = type('EnumObj', (), {})
    enum_cls_obj.__kwargs = kwargs
    enum_cls_obj.__fkwargs = fkwargs
    enum_cls_obj.members = {tuple(set([n, n.upper(), n.lower(), v, str(v)] + k)): v for n, (v, k) in fkwargs.items()}
    enum_cls_obj.reverse_map = {v: n for n, (v, k) in fkwargs.items()}
    enum_cls_obj.name_map = {n: v for n, (v, k) in fkwargs.items()}
    enum_cls_obj.all_values = enum_cls_obj.members.values()
    enum_cls_obj.all_names = enum_cls_obj.reverse_map.values()
    enum_cls_obj.get_keys = lambda x, _key: [k for n, (v, k) in x.__fkwargs.items() if _key == v][0]
    enum_cls_obj.all_keys = [key for n, (v, k) in fkwargs.items() for key in k]
    enum_cls_obj.get = lambda x, k, d=None, ic=True, rim=True: dget_tkey(x.members, k, d, ic, rim)
    enum_cls_obj.rget = lambda x, k, d=None: x.reverse_map.get(k, d)
    enum_cls_obj.to_str = lambda x, v, d=None: str(x.reverse_map.get(v, d))
    enum_cls_obj.display = lambda x, v: \
        'Item(name={} value={})'.format(x.to_str(v), v) if v in x else raise_(KeyError(v))
    enum_cls_obj.__str__ = lambda x: 'EnumObj({})'.format(' '.join(['{}+{}={}'.format(n, len(k), v)
                                                                    for n, (v, k) in x.__fkwargs.items()]))
    enum_cls_obj.__getattr__ = lambda x, y: x.get(y)
    enum_cls_obj.__iter__ = lambda x: iter(x.all_values)
    enum_cls_obj.__call__ = lambda x, y: y if y in x else raise_(KeyError(y))
    enum_cls_obj.__dir__ = lambda x: dir(x.__class__) + x.all_names
    return enum_cls_obj()


def enum(*sequential, **named):
    """
    Create an Enumerator
    :param sequential: Sequential items will get values based on their index
    :param named: Key-value pairs as enums
    :return: returns an enumerator class.
    """
    enums = dict(zip(sequential, range(len(sequential))), **named)
    reverse = dict((value, key) for key, value in enums.iteritems())
    enums['reverse_mapping'] = reverse
    enum_cls_obj = type('Enum', (), enums)
    enum_cls_obj.to_str = lambda x, v, d=None: str(x.reverse_mapping.get(v, d))
    enum_cls_obj.__iter__ = lambda x: iter(x.reverse_mapping)
    enum_cls_obj.__call__ = lambda x, y: y if y in x else raise_(KeyError(y))
    return enum_cls_obj()


def raise_(ex=None):
    """
    Raises an exception, to be used inside lambdas, or raise exceptions as function calls
    :param ex: which exception to raise
    :return: raises an exception
    """
    ex = ex or Exception()
    raise ex


__all__ = ['complex_enum_gen', 'enum']
