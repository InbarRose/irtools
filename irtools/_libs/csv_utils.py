#! /usr/bin/env python

# Standard Imports
import csv
import numbers
from itertools import izip

# irtools Imports
from irtools import *

# logging
log = logging.getLogger('irtools.utils.csv')

if not running_on_windows:
    csv.field_size_limit(sys.maxsize)  # to read large queries


def _stringify(s, encoding, errors):
    # https://github.com/jdunck/python-unicodecsv
    if s is None:
        return ''
    if isinstance(s, unicode):
        return s.encode(encoding, errors)
    elif isinstance(s, numbers.Number):
        pass  # let csv.QUOTE_NONNUMERIC do its thing.
    elif not isinstance(s, str):
        s = str(s)
    return s


def _stringify_list(l, encoding, errors='strict'):
    # https://github.com/jdunck/python-unicodecsv
    try:
        return [_stringify(s, encoding, errors) for s in iter(l)]
    except TypeError as e:
        raise csv.Error(str(e))


def _unicodify(s, encoding):
    # https://github.com/jdunck/python-unicodecsv
    if s is None:
        return None
    if isinstance(s, (unicode, int, float)):
        return s
    elif isinstance(s, str):
        return s.decode(encoding)
    return s


class UnicodeWriter(object):
    # https://github.com/jdunck/python-unicodecsv
    def __init__(self, f, dialect=csv.excel, encoding='utf-8', errors='strict',
                 *args, **kwds):
        self.encoding = encoding
        self.writer = csv.writer(f, dialect, *args, **kwds)
        self.encoding_errors = errors

    def writerow(self, row):
        return self.writer.writerow(
                _stringify_list(row, self.encoding, self.encoding_errors))

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)

    @property
    def dialect(self):
        return self.writer.dialect


class UnicodeReader(object):
    # https://github.com/jdunck/python-unicodecsv
    def __init__(self, f, dialect=None, encoding='utf-8', errors='strict',
                 *args, **kwds):

        format_params = ['delimiter', 'doublequote', 'escapechar',
                         'lineterminator', 'quotechar', 'quoting',
                         'skipinitialspace']

        if dialect is None:
            if not any([kwd_name in format_params
                        for kwd_name in kwds.keys()]):
                dialect = csv.excel
        self.reader = csv.reader(f, dialect, **kwds)
        self.encoding = encoding
        self.encoding_errors = errors
        self._parse_numerics = bool(
            self.dialect.quoting & csv.QUOTE_NONNUMERIC)

    def next(self):
        row = self.reader.next()
        encoding = self.encoding
        encoding_errors = self.encoding_errors
        unicode_ = unicode
        if self._parse_numerics:
            float_ = float
            return [(value if isinstance(value, float_) else
                    unicode_(value, encoding, encoding_errors))
                    for value in row]
        else:
            return [unicode_(value, encoding, encoding_errors)
                    for value in row]

    def __iter__(self):
        return self

    @property
    def dialect(self):
        return self.reader.dialect

    @property
    def line_num(self):
        return self.reader.line_num


class DictWriter(csv.DictWriter):
    # https://github.com/jdunck/python-unicodecsv
    def __init__(self, csvfile, fieldnames, restval='',
                 extrasaction='raise', dialect=csv.excel, encoding='utf-8',
                 errors='strict', *args, **kwds):
        self.encoding = encoding
        csv.DictWriter.__init__(self, csvfile, fieldnames, restval,
                                extrasaction, dialect, *args, **kwds)
        self.writer = UnicodeWriter(csvfile, dialect, encoding=encoding,
                                    errors=errors, *args, **kwds)
        self.encoding_errors = errors

    def writeheader(self):
        header = dict(zip(self.fieldnames, self.fieldnames))
        self.writerow(header)


class DictReader(csv.DictReader):
    # https://github.com/jdunck/python-unicodecsv
    def __init__(self, csvfile, fieldnames=None, restkey=None, restval=None,
                 dialect='excel', encoding='utf-8', errors='strict', *args,
                 **kwds):
        if fieldnames is not None:
            fieldnames = _stringify_list(fieldnames, encoding)
        csv.DictReader.__init__(self, csvfile, fieldnames, restkey, restval,
                                dialect, *args, **kwds)
        self.reader = UnicodeReader(csvfile, dialect, encoding=encoding,
                                    errors=errors, *args, **kwds)
        if fieldnames is None and not hasattr(csv.DictReader, 'fieldnames'):
            # Python 2.5 fieldnames workaround.
            # See http://bugs.python.org/issue3436
            reader = UnicodeReader(csvfile, dialect, encoding=encoding,
                                   *args, **kwds)
            self.fieldnames = _stringify_list(reader.next(), reader.encoding)

        if self.fieldnames is not None:
            self.unicode_fieldnames = [_unicodify(f, encoding) for f in
                                       self.fieldnames]
        else:
            self.unicode_fieldnames = []

        self.unicode_restkey = _unicodify(restkey, encoding)

    def next(self):
        row = csv.DictReader.next(self)
        result = dict((uni_key, row[str_key]) for (str_key, uni_key) in
                      izip(self.fieldnames, self.unicode_fieldnames))
        rest = row.get(self.restkey)
        if rest:
            result[self.unicode_restkey] = rest
        return result


def read_csv_from_string(text, return_headers=False):
    """
    reads a csv (comma separated values) string using DictReader and returns a rowdicts list
    :param text: string to parse CSV from
    :param return_headers: return value becomes (rows, headers)
    :return: rows read from csv
    """
    log.trace('reading csv string: content[:20]={} len={}'.format(repr(text[:20]), len(text)))
    reader = DictReader(text.splitlines())
    rows = [row for row in reader]
    if return_headers:
        return rows, reader.fieldnames
    return rows


def read_tsv_from_string(text, return_headers=False):
    """
    reads a tsv (tab separated values) string using DictReader and returns a rowdicts list
    :param text: string to parse TSV from
    :param return_headers: return value becomes (rows, headers)
    :return: rows read from csv
    """
    log.trace('reading tsv string: content[:20]={} len={}'.format(repr(text[:20]), len(text)))
    reader = DictReader(text.splitlines(), dialect='excel-tab')
    rows = [row for row in reader]
    if return_headers:
        return rows, reader.fieldnames
    return rows


class excel_space(csv.excel):
    """Describe the usual properties of Excel-generated SPACE-delimited files."""
    delimiter = ' '


csv.register_dialect("excel-space", excel_space)


def read_ssv_from_string(text, return_headers=False):
    """
    reads a ssv (space separated values) string using DictReader and returns a rowdicts list
    :param text: string to parse SSV from
    :param return_headers: return value becomes (rows, headers)
    :return: rows read from csv
    """
    log.trace('reading ssv string: content[:20]={} len={}'.format(repr(text[:20]), len(text)))
    reader = DictReader(text.splitlines(), dialect='excel-space')
    rows = [row for row in reader]
    if return_headers:
        return rows, reader.fieldnames
    return rows


__all__ = ['DictReader', 'DictWriter', 'read_csv_from_string', 'read_tsv_from_string', 'read_ssv_from_string']
