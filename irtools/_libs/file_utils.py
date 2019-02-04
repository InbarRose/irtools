#! /usr/bin/env python

# Standard Imports
import re
import shutil
import glob
import difflib
import fnmatch
import tempfile
import zipfile
import json

# Lib Imports
from byte_utils import check_file_size
from csv_utils import DictReader, DictWriter

# irtools Imports
from irtools import *

# logging
log = logging.getLogger('irtools.utils.file')

# check_makedir ignore
MKDIR_IGNORE = ['file already exists', 'File exists', 'No such file or directory']


def zip_dir(path_to_dir, zip_file, exclude_dirs=None, raise_on_error=True, validate=True):
    """
    make zip file with relative paths
    :param path_to_dir: the path to directory
    :param zip_file: name of zip file to create
    :param exclude_dirs: dir paths to ignore (exclude)
    :param raise_on_error: Raise an exception if error
    :param validate: Validate the zip file
    :return: boolean of success
    """
    log.debug('zip_dir: path={} zip={}'.format(path_to_dir, zip_file))
    check_makedir(os.path.dirname(zip_file))
    zip_ref = zipfile.ZipFile(zip_file, "w", zipfile.ZIP_DEFLATED)
    try:
        for dirname, subdirs, files in os.walk(path_to_dir):
            for subdir in [os.path.join(dirname, sdir) for sdir in subdirs]:
                if exclude_dirs:
                    for exdir in [xd for xd in exclude_dirs if os.path.abspath(xd) == os.path.abspath(subdir)]:
                        subdirs.remove(os.path.split(exdir)[-1])
            if not files:
                continue
            relative_dir_name = os.path.relpath(dirname, path_to_dir)
            zip_ref.write(dirname, relative_dir_name)
            for filename in files:
                full_path_to_file = os.path.join(dirname, filename)
                relative_path_to_file = os.path.relpath(full_path_to_file, path_to_dir)
                zip_ref.write(full_path_to_file, relative_path_to_file)
        zip_ref.close()
    except IOError as exc:
        log.error('Exception while zipping directory: zip_file={} directory={} exc={}'.format(
            zip_file, path_to_dir, exc))
        if raise_on_error:
            raise
        return False
    else:
        if validate:
            if not validate_zip(zip_file, raise_on_fail=raise_on_error):
                log.error('invalid zipfile: zip={}'.format(zip_file))
                return False
        return True


def zip_files(files, zip_file, raise_on_error=True, validate=True):
    """
    make a zip file from a list of files
    :param files: list of files to put into zip
    :param zip_file: the zip file to make
    :param raise_on_error: Raise an exception if error
    :param validate: Validate the zip file
    :return: boolean of success
    """
    log.debug('zip_files: files={} zip={}'.format(files, zip_file))
    check_makedir(os.path.dirname(zip_file))
    zip_ref = zipfile.ZipFile(zip_file, "w", zipfile.ZIP_DEFLATED)
    try:
        for filepath in files:
            zip_ref.write(filepath, os.path.basename(filepath))
        zip_ref.close()
    except IOError as exc:
        log.error('Exception while zipping files: zip_file={} files={} exc={}'.format(
            zip_file, files, exc))
        if raise_on_error:
            raise
        return False
    else:
        if validate:
            if not validate_zip(zip_file, raise_on_fail=raise_on_error):
                log.error('invalid zipfile: zip={}'.format(zip_file))
                return False
        return True


def unzip_dir(path_to_zip_file, directory_to_unzip_file, raise_on_error=True, validate=True):
    """
    unzip file to directory
    :param raise_on_error:
    :param path_to_zip_file: name to existing zip file
    :param directory_to_unzip_file: directory to unzip into (and create)
    :param validate: Validate the zip file
    :return: boolean of success
    """
    log.debug('unzip_dir: zip={} path={}'.format(path_to_zip_file, directory_to_unzip_file))
    if validate:
        if not validate_zip(path_to_zip_file, raise_on_fail=raise_on_error):
            log.error('invalid zipfile, skipping unzip: zip={}'.format(path_to_zip_file))
            return False
    check_makedir(os.path.dirname(directory_to_unzip_file))
    zip_ref = zipfile.ZipFile(path_to_zip_file, 'r')
    try:
        zip_ref.extractall(directory_to_unzip_file)
    except IOError as exc:
        log.error('Exception while unzipping into directory: zip_file={} directory={} exc={}'.format(
            path_to_zip_file, directory_to_unzip_file, exc))
        if raise_on_error:
            raise
        return False
    else:
        zip_ref.close()
        log.info('Successfully unzipped into directory: zip_file={} directory={}'.format(
            path_to_zip_file, directory_to_unzip_file))
        return True


def validate_zip(path_to_zip, raise_on_fail=True):
    """
    validates a zip file
    :param path_to_zip:
    :param raise_on_fail:
    :return:
    """
    log.debug('validate_zip: zip={}'.format(path_to_zip))
    zip_ref = zipfile.ZipFile(path_to_zip, "r", zipfile.ZIP_DEFLATED)
    try:
        ret = zip_ref.testzip()
    except Exception as exc:
        log.error('Exception validating zip file: zip_file={} exc={}'.format(path_to_zip, exc))
        if raise_on_fail:
            raise
        return False
    else:
        if ret is not None:
            log.error('zip_file validation failed: zip_file={} ret={}'.format(path_to_zip, ret))
            if raise_on_fail:
                raise zipfile.BadZipfile('zip validation failed for zip file {} on {}'.format(path_to_zip, ret))
            return False
    finally:
        zip_ref.close()
    return True


def smart_copy(src, dst, ignore_patterns=(), ignore_dst_dir_exists=True, build_dst_dirs=True, raise_on_fail=True):
    """
    Copies a path `src` to `dst` including dirs and files.
    if src is file, will build dirtree at destination
    :param src: file or dir tree
    :param dst: destination dir
    :param ignore_patterns: sequence of glob-style patterns to ignore
    :param ignore_dst_dir_exists: if dst dir exists, copy each file into it
    :param build_dst_dirs: build dirtree at dst (check_makedir on [dst dirname for files else dst])
    :param raise_on_fail: raise exception on failure
    :return: success or failure boolean
    """
    try:
        if os.path.isfile(src):
            # source is a file
            if any(p.strip('*') in src for p in ignore_patterns):
                # source file is in ignored list, we should do nothing
                return False
            if build_dst_dirs and not os.path.exists(dst):
                # if we should build dst dirs and the dst does not exist, we first assume dst is a file and make its dir
                check_makedir(os.path.dirname(dst))
            try:
                shutil.copy(src, dst)  # copy src into dst location, assuming dst was a filepath and dirs exist
            except IOError as exc:
                if exc.errno == 2:
                    # "No such file or directory" can be ignored, otherwise raise
                    # likely we are here because dst was a dir not a file and it didn't exist
                    check_makedir(dst)  # so lets make dst dir
                    shutil.copy(src, dst)  # try again with no catching
                else:
                    raise
        elif os.path.exists(dst) and os.path.isdir(dst):
            if not ignore_dst_dir_exists:
                log.error('smart_copy failed, cannot copy a directory into an existing directory')
                return False
            for fname in os.listdir(src):
                fpath = os.path.join(src, fname)
                smart_copy(fpath, dst, ignore_patterns, ignore_dst_dir_exists)
        else:
            # copytree, dst should not exist
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns(*ignore_patterns))
    except OSError as exc:
        log.error('smart_copy failed: exc={}'.format(exc))
        if raise_on_fail:
            raise
        return False
    else:
        return True


def clean_paths(*paths, **kwargs):
    """Clean the paths by deleting them, can handle files or directories"""
    log_as_trace = kwargs.pop('log_as_trace', False)
    msg = 'Cleaning paths: count={} paths={}'.format(len(paths), list(paths))
    if log_as_trace:
        log.trace(msg)
    else:
        log.info(msg)
    rc = 0
    for path in paths:
        if not path or not os.path.exists(path):
            log.trace('Skip cleaning path: path={}'.format(path))
            continue
        try:
            if os.path.isfile(path):
                os.unlink(path)
            else:
                shutil.rmtree(path)
        except Exception as exc:
            log.error('Exception in cleanup: path={} exc={}'.format(path, exc))
            rc = 1
    msg = 'finished cleaning paths: rc={}'.format(rc)
    if log_as_trace:
        log.trace(msg)
    else:
        log.info(msg)
    return rc


def check_makedir(path, mode=0777):
    """Makes a directory. Must be given a path to a directory, not a file."""
    if not os.path.exists(path):
        try:
            os.makedirs(path, mode)
        except Exception as exc:
            if any(mkdir_ignore in str(exc) for mkdir_ignore in MKDIR_IGNORE):
                log.debug('makedir exception, (ignored): path={} exc=(msg={} args={} class={})'.format(
                    path, exc.message, exc.args, exc.__class__))
            else:
                log.warn('makedir exception, (ignored): path={} exc=(msg={} args={} class={})'.format(
                    path, exc.message, exc.args, exc.__class__), exc_info=True)
    return path


def get_tmp_dir(use_logging=True):
    """gets the temp dir on local machine"""
    tmp_dir = tempfile.gettempdir()
    if use_logging:
        log.info('Temporary Directory Found: tempdir=({})'.format(tmp_dir))
    return tmp_dir


def write_to_tmp_file(content):
    """
    writes the content to a temporary file
    :param content: the content to write (string)
    :return: returns the file_path
    """
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(content)
    return f.name


def find_single_path(glob_pattern, raise_on_fail=True):
    """
    Find a filename/path with the given glob pattern and returns the filename/path matching it
    :param glob_pattern: /path/to/file/with/aster*x
    :param raise_on_fail: raise exception if no match or multiple matches found
    :return: return the filename/path or Raise or None
    """
    log.trace('find single path: glob={}'.format(glob_pattern))
    matching_files = glob.glob(glob_pattern)

    if len(matching_files) > 1:
        if raise_on_fail:
            raise Exception('Too many matches: files={}'.format(matching_files))
    elif not matching_files:
        if raise_on_fail:
            raise Exception('No matching file found')
    else:
        return matching_files[0]
    return None


def find_files_recursively(directory, pattern):
    """
    finds all files in a directory recursively based on the file filter.
    pattern is a Unix shell style:

    *       matches everything
    ?       matches any single character
    [seq]   matches any character in seq
    [!seq]  matches any char not in seq

    :param directory: directory to search
    :param pattern: filename pattern
    :return: a list of matched files
    """
    matches = []
    for root, dirnames, filenames in os.walk(directory):
        for filename in fnmatch.filter(filenames, pattern):
            matches.append(os.path.join(root, filename))
    return matches


def file_rotation(file_name, rotate_rx='_rx_'):
    """
    Find next available file name using rotation, does not actually move files.
    just finds next available name using delimiter

    example writing to "/tmp/file_name.txt" multiple times using "_rx_" as rotation delimiter:
    # first time
    >> utils.file_rotation('/tmp/file_name.txt')
    '/tmp/file_name.txt'  # we write to the desired path
    # second time
    >> utils.file_rotation('/tmp/file_name.txt')
    '/tmp/file_name_rx_1.txt'  # we write to the next available rotation
    # third time
    >> utils.file_rotation('/tmp/file_name.txt')
    '/tmp/file_name_rx_2.txt'  # we write to the next available rotation

    :param file_name:
    :param rotate_rx: rotation delimiter
    :return:
    """
    # todo: abstract rotation pattern, ie; allow filename.txt.1 .. filename.txt.n (simply adding a .number to the end)
    rotation_pattern = r'(.*?)({})(\d+)(.*)'.format(rotate_rx)
    rotation_re = re.compile(rotation_pattern)
    while os.path.exists(file_name):
        dirname, basename = os.path.split(file_name)
        mo = rotation_re.match(basename)
        if not mo:
            rotation = 1
            file_base, file_ext = os.path.splitext(basename)
        else:
            file_base, _, rotation, file_ext = mo.groups()
            rotation = int(rotation) + 1
        file_name = os.path.join(dirname, '{}{}{}{}'.format(file_base, rotate_rx, rotation, file_ext))
    return file_name


def write_file(file_name, contents=None, mode='w', rotate=False, **kwargs):
    """
    create, or append to a file, optionally with content, return file_name
    :param file_name:
    :param contents:
    :param mode:
    :param rotate:
    :return: the filename that was written
    """
    check_makedir(os.path.dirname(file_name))
    if rotate:
        file_name = file_rotation(file_name, rotate_rx=kwargs.get('rotate_rx', '_rx_'))
    with open(file_name, mode) as f:
        if contents:
            if isinstance(contents, list) and isinstance(contents[0], str):
                f.writelines(contents)
            else:
                if not isinstance(contents, str):
                    contents = str(contents)
                f.write(contents)
    return file_name


def read_file(file_name, mode='r', raise_on_error=True, as_str=False, strip_newlines=False):
    """
    Read a file: by default read the lines f.readlines() or f.read() if as_str=True
    :param file_name: path of the file
    :param mode: mode to read the file (r)
    :param raise_on_error: raise exception on read error
    :param as_str: return the contents as a string
    :param strip_newlines: return the contents as a list with no newlines: [l.strip('\n') for l in lines]
    :return: a list of lines or string
    """
    try:
        with open(file_name, mode=mode) as f:
            if as_str:
                content = f.read()
            else:
                content = f.readlines()
    except Exception as exc:
        if raise_on_error:
            raise
        log.warn('Exception reading file, ignoring, and return empty: exc={}'.format(exc))
        if as_str:
            return ''
        else:
            return []
    else:
        if as_str:
            return content
        else:
            if strip_newlines:
                content = [l.strip('\n') for l in content]
            return content


def write_csv(file_name, contents, headers=None, **kwargs):
    """
    writes a csv file using DictWriter and returns the filename
    if contents is a rowdicts uses the keys of the first dict in contents as the headers
    if contents is a dictionary, you must supply the headers, for 2 columns [key, value]
    :param file_name: path of the file
    :param contents: rowdicts list (or simple dict/map with all strings, for 2 columns [key, value]
    :param headers: specify headers, or take from contents
    :return: the filename that was written
    """
    if isinstance(contents, dict):
        assert headers and len(headers) == 2
        contents = [{headers[0]: key, headers[1]: value} for key, value in contents.items()]
    headers = headers or contents[0].keys()
    log.trace('writing csv file: path={} headers={} rows={}'.format(file_name, headers, len(contents)))
    check_makedir(os.path.dirname(file_name))
    with open(file_name, 'wb') as f:
        writer = DictWriter(f, headers, **kwargs)
        writer.writeheader()
        writer.writerows(contents)
    return file_name


def read_csv(file_name, return_headers=False):
    """
    reads a csv file using DictReader and returns a rowdicts list
    :param file_name: path of the file
    :param return_headers: return value becomes (rows, headers)
    :return: rows read from csv
    """
    log.trace('reading csv file: path={}'.format(file_name))
    with open(file_name, 'rb') as f:
        # verify file is not empty
        if not check_file_size(file_name):
            log.warn('csv file size is 0 bytes: csv={}'.format(file_name))
            if return_headers:
                return [], []
            return []

        reader = DictReader(f)
        rows = [row for row in reader]
    if return_headers:
        return rows, reader.fieldnames
    return rows


def iread_csv(file_name, return_headers=False):
    """
    iter-reads a csv file using DictReader and returns a rowdicts generator
    :param file_name: path of the file
    :param return_headers: first yield is the headers
    :return: rows read from csv as generator
    """
    log.trace('reading csv file: path={}'.format(file_name))
    if not check_file_size(file_name):
        # verify file is not empty
        log.warn('csv file size is 0 bytes: csv={}'.format(file_name))
        raise StopIteration()
    f = open(file_name, 'rb')
    reader = DictReader(f)
    try:
        if return_headers:
            yield reader.fieldnames
        for row in reader:
            yield row
    except StopIteration:
        f.close()
    finally:
        f.close()


def read_json(file_name, json_kwargs=None, **kwargs):
    """
    reads a json file using read_file and creates a python object using json module
    :param file_name: path of the file
    :param json_kwargs:
    :param kwargs:
    :return: python object (dict)
    """
    log.trace('reading json file: path={}'.format(file_name))
    raise_on_json_error = kwargs.pop('raise_on_json_error', True)
    json_kwargs = json_kwargs or {}
    kwargs['as_str'] = True
    contents = read_file(file_name, **kwargs)
    try:
        python_object = json.loads(contents, **json_kwargs)
    except Exception as exc:
        if raise_on_json_error:
            raise
        log.error('exception loading json from file: exc={}'.format(exc))
    else:
        return python_object


def write_json(file_name, python_object, json_kwargs=None, **kwargs):
    """
    writes a python object as json into a json file using json module and write_file method
    :param file_name: path of the file
    :param python_object: python object (dict)
    :param json_kwargs:
    :param kwargs:
    :return: path to file
    """
    log.trace('writing json file: path={}'.format(file_name))
    raise_on_json_error = kwargs.pop('raise_on_json_error', True)
    json_kwargs = json_kwargs or {}
    try:
        contents = json.dumps(python_object, **json_kwargs)
    except Exception as exc:
        if raise_on_json_error:
            raise
        log.error('exception dumping json to file: exc={}'.format(exc))
    else:
        return write_file(file_name, contents, **kwargs)


def file_diff(file_a, file_b, output=None, **kwargs):
    """
    performance a diff between two files
    :param file_a: first file
    :param file_b: second file
    :param output: output file for diff
    :param kwargs: any kwargs
    :return:
    """
    file_mode = kwargs.pop('file_mode', 'Urb')
    if kwargs.pop('show_log', True):
        log.trace('performing file diff between two files: a={} b={}'.format(file_a, file_b))
    with open(file_a, mode=file_mode) as af, open(file_b, mode=file_mode) as bf:
        al = af.readlines()
        if kwargs.pop('ignore_utf_bom', True) and al:
            al[0] = al[0].decode('utf-8-sig')  # ignore utf BOM ('\xef\xbb\xbf')

        diff = list(difflib.unified_diff(
            al,
            bf.readlines(),
            fromfile=file_a,
            tofile=file_b,
            n=0
        ))

    if diff:
        if output:
            with open(output, 'w') as f:
                f.writelines(diff)
        if kwargs.pop('as_bool', True):
            return True
        return diff

    return False


def bulk_rename(src_dir, before, after, dst_dir=None, raise_on_error=True):
    """
    Perform bulk-rename operation on files in a directory. optionally move them to another directory.
    :param src_dir:
    :param before:
    :param after:
    :param dst_dir:
    :param raise_on_error:
    :return:
    """
    assert before != after
    dst_dir = dst_dir or src_dir
    log.debug('bulk-renaming: src={} dst={} before={} after={}'.format(src_dir, dst_dir, before, after))
    fns = [fn for fn in os.listdir(src_dir) if os.path.isfile(fn) and before in fn]
    if not fns:
        log.warn('bulk-rename found no files to work with')
        return False
    success = 0
    for fn in fns:
        fp = os.path.join(src_dir, fn)
        nfp = os.path.join(dst_dir, fn.replace(before, after))
        log.trace('bulk-renaming: src={} dst={}'.format(fp, nfp))
        try:
            shutil.move(fp, nfp)
        except Exception as exc:
            if not raise_on_error:
                log.warn('Exception bulk-renaming files, ignoring: exc={}'.format(exc))
            raise
        else:
            success += 1
    if success == len(fns):
        return True
    log.warn('bulk-rename had failures: fails={}'.format(len(fns) - success))
    return False


def format_file(filepath, raise_on_fail=True, **kwargs):
    """
    format a files contents with given kwargs using pythons string.format()
    :param filepath: filepath to format
    :param raise_on_fail: raise exceptions
    :param kwargs:
    :return: returns True if success else False
    """
    try:
        with open(filepath, 'rb') as fr:
            content_before = fr.readlines()
    except Exception as exc:
        log.error('Exception reading file before format: filepath={} exc={}'.format(filepath, exc))
        if raise_on_fail:
            raise
        return False
    else:
        content_after = []
        for idx, line in enumerate(content_before):
            # todo: harden {} rules
            if not any(k in line for k in kwargs.keys()):
                new_line = line
            else:
                try:
                    new_line = line.format(**kwargs)
                except Exception as exc:
                    log.error('Exception formatting file line: filepath={} idx={} exc={}'.format(filepath, idx, exc))
                    if raise_on_fail:
                        raise
                    return False
            content_after.append(new_line)
        try:
            with open(filepath, 'wb') as fw:
                fw.writelines(content_after)
        except Exception as exc:
            log.error('Exception writing file after format: filepath={} exc={}'.format(filepath, exc))
            if raise_on_fail:
                raise
            return False
        else:
            return True


def replace_content_in_file(filepath, replacements, raise_on_fail=True, **kwargs):
    """
    replaces content in a file,
    :param filepath: the path to the file for replacements
    :param replacements: replacements should be a dictionary of {target: replacement}
    :param raise_on_fail:
    :param kwargs:
    :return:
    """
    log.debug('Modifying file in-place: filepath={}'.format(filepath))
    backup_file = kwargs.pop('backup_file', None)
    return_success = kwargs.pop('return_success', True)
    new_content = []  # will contain the final content of the conf file
    successful_replacements = []

    # make a backup
    if backup_file:
        smart_copy(filepath, backup_file)

    # read conf
    contents = read_file(filepath)

    for idx, line in enumerate(contents[:]):
        # make new line so we can modify it
        new_line = line
        # normal line (configuration / not section)
        for key in replacements.keys():
            if key not in new_line:
                continue  # line is not relevant
            log.trace('replace content in file: filepath={} index={} key={} value={}'.format(
                filepath, idx, key, replacements[key]))
            # replace and save (supports multiple per line)
            new_line = new_line.replace(key, replacements[key])
            successful_replacements.append(key)
        # add the new_line to the new_content (it may be unchanged)
        new_content.append(new_line)

    # write conf
    write_file(filepath, new_content)

    # return success
    if return_success:
        return bool(all([k in successful_replacements for k in replacements.keys()]))
    # todo: raise on fail ?
    # return the replacements that were done
    return successful_replacements


__all__ = [
    'check_makedir', 'find_single_path', 'find_files_recursively',
    'read_file', 'write_file', 'read_csv', 'write_csv', 'read_json', 'write_json', 'iread_csv',
    'bulk_rename', 'file_diff', 'file_rotation', 'format_file', 'replace_content_in_file',
    'get_tmp_dir', 'write_to_tmp_file',
    # simple wrappers of copy/delete
    'smart_copy', 'clean_paths',
    # zip functions
    'zip_dir', 'unzip_dir', 'zip_files',
]
