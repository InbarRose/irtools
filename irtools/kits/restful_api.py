# Standard Imports
import itertools
import json

# irtools Imports
from irtools import *

# External Imports
import requests

log = logging.getLogger('irtools.kits.restful_api')
# disable annoying debug logs from urllib3.connectionpool
urllib_log = logging.getLogger('urllib3.connectionpool')
urllib_log.setLevel(logging.WARN)


class RestfulAPI(object):
    """
    A class which wraps the process of sending restful API requests using the requests package
    conveniently logs all transactions for debugging and provides extendability
    """
    # todo: support sessions
    # todo: add extendability and convenience

    # class constants
    # transaction counter as a class constant is useful to prevent clashes with the same id
    transaction_counter = itertools.count()
    # the request timeout helps prevent hanging
    request_timeout = 120
    # these strings/keys are used to help parse kwargs related to logging transactions out of regular kwargs
    _log_keys = ['_log_transact_id', '_log_transact_name', '_log_save_request', '_log_save_response']
    # errors that should be ignored when converting JSON data
    _ignored_json_convert_error_messages = [
        'Extra data',
        'No JSON object could be decoded',
    ]
    # this file format is here so it can be extended easily
    _format_log_file_path = '{directory}/{method}_{id}.txt'

    def __init__(self, base_url, **kwargs):
        self.base_url = base_url
        self.name = kwargs.pop('name', 'rest')
        self.log_rest_dir = kwargs.pop('log_rest_dir', os.path.join(log_dir, self.name))

    @property
    def request_data_dir(self):
        """directory to store request data and logs"""
        return self.log_rest_dir + '/request'

    @property
    def response_data_dir(self):
        """directory to store response data and logs"""
        return self.log_rest_dir + '/response'

    def _get_transaction_id_parts(self):
        """gets the parts to include in the transaction id (log file name)"""
        return [self.transaction_counter.next(), self.base_url]

    def make_transaction_id(self, *args):
        """construct the transaction id using the default parts and any args"""
        return '.'.join(map(str, filter(None, self._get_transaction_id_parts() + list(args))))

    def _extract_log_kwargs(self, **kwargs):
        """extracts the log kwargs from request kwargs for use in logging"""
        log_kwargs = {lk[5:]: kwargs.pop(lk) for lk in self._log_keys if lk in kwargs.keys()}
        return log_kwargs, kwargs

    def _log_transaction(self, response, **kwargs):
        """
        logs the request transaction, both request and response with optional kwargs
        :param response:
        :param kwargs:
        :return:
        """
        transact_name = kwargs.pop('transact_name', None)
        if transact_name:
            transact_id = '{}.{}'.format(self.transaction_counter.next(), transact_name)
        else:
            transact_id = kwargs.pop('transact_id', None) or self.transaction_counter.next()
        save_request = kwargs.pop('save_request', True)
        save_response = kwargs.pop('save_response', True)
        if save_request:
            try:
                self._log_request(response, transact_id)
            except Exception as exc:
                log.error('Exception logging rest transaction request: id={} exc={} trace...'.format(transact_id, exc),
                          exc_info=True)
        if save_response:
            try:
                self._log_response(response, transact_id)
            except Exception as exc:
                log.error('Exception logging rest transaction response: id={} exc={} trace...'.format(transact_id, exc),
                          exc_info=True)

    def _log_request(self, response, transact_id):
        """log the request side of a transaction"""
        request_file_path = self._get_log_request_file_path(response.request.method, transact_id)
        if response.request.body:
            content = response.request.body
        else:
            content = response.request.url
        data_file = utils.write_file(request_file_path, content)
        log.trace('log-request: method={} url={} path={} data={}'.format(
            response.request.method, response.request.url, data_file, bool(response.request.body)))

    def _log_response(self, response, transact_id):
        """log the response side of a transaction"""
        response_file_path = self._get_log_response_file_path(response.request.method, transact_id)
        content = self._get_content_from_json(response)
        if content is not None:
            data_file = utils.write_file(response_file_path, json.dumps(content, indent=4))
            log.trace('log-response: status={} data={}'.format(response.status_code, data_file))
        else:
            log.trace('log-response: status={} data=None'.format(response.status_code))

    def _get_log_request_file_path(self, method, transact_id):
        """creates the final file path for request logs"""
        request_file_path = self._format_log_file_path.format(
            directory=self.request_data_dir, method=method, id=transact_id)
        return request_file_path

    def _get_log_response_file_path(self, method, transact_id):
        """creates the final file path for response logs"""
        response_file_path = self._format_log_file_path.format(
            directory=self.response_data_dir, method=method, id=transact_id)
        return response_file_path

    def _get_content_from_json(self, response):
        """attempts to extract content from a json in the response from server"""
        try:
            content = response.json()
        except ValueError as vexc:
            if not any([ignored_msg in str(vexc) for ignored_msg in self._ignored_json_convert_error_messages]):
                raise
            elif response.content:
                content = response.content
            else:
                content = None
        return content

    def request_get(self, url, **kwargs):
        """sends a GET command using requests package"""
        ignore_request_timeout = kwargs.pop('ignore_request_timeout', False)
        ignore_connection_aborted = kwargs.pop('ignore_connection_aborted', False)
        log_action = kwargs.pop('log_action', True)
        kwargs.setdefault('timeout', self.request_timeout)
        log_kwargs, kwargs = self._extract_log_kwargs(**kwargs)
        if log_action:
            log.debug('request.get: url={}'.format(url))
        try:
            r = requests.get(url, **kwargs)
        except requests.ReadTimeout as exc:
            if ignore_request_timeout:
                log.debug('Requests Timeout, ignored: url={} exc={}'.format(url, exc))
            else:
                raise
        except requests.ConnectionError as exc:
            if ignore_connection_aborted and 'Connection aborted.' in str(exc):
                log.debug('Connection Aborted, ignored: url={} exc={}'.format(url, exc))
            else:
                raise
        except requests.RequestException as exc:
            log.error('requests get exception: exc={} url={}'.format(exc, url))
            raise
        else:
            self._log_transaction(r, **log_kwargs)
            return r

    def request_post(self, url, **kwargs):
        """sends a POST command using requests package"""
        log_action = kwargs.pop('log_action', True)
        kwargs.setdefault('timeout', self.request_timeout)
        log_kwargs, kwargs = self._extract_log_kwargs(**kwargs)
        if log_action:
            log.debug('request.post: url={}'.format(url))
        try:
            r = requests.post(url, **kwargs)
        except requests.RequestException as exc:
            log.error('requests post exception: exc={} url={}'.format(exc, url))
            raise
        else:
            self._log_transaction(r, **log_kwargs)
        return r

    def request_put(self, url, **kwargs):
        """sends a PUT command using requests package"""
        log_action = kwargs.pop('log_action', True)
        kwargs.setdefault('timeout', self.request_timeout)
        log_kwargs, kwargs = self._extract_log_kwargs(**kwargs)
        if log_action:
            log.debug('request.put: url={}'.format(url))
        try:
            r = requests.put(url, **kwargs)
        except requests.RequestException as exc:
            log.error('requests put exception: exc={} url={}'.format(exc, url))
            raise
        else:
            self._log_transaction(r, **log_kwargs)
        return r

    def request_delete(self, url, **kwargs):
        """sends a DELETE command using requests package"""
        log_action = kwargs.pop('log_action', True)
        kwargs.setdefault('timeout', self.request_timeout)
        log_kwargs, kwargs = self._extract_log_kwargs(**kwargs)
        if log_action:
            log.debug('request.delete: url={}'.format(url))
        try:
            r = requests.delete(url, **kwargs)
        except requests.RequestException as exc:
            log.error('requests delete exception: exc={} url={}'.format(exc, url))
            raise
        else:
            self._log_transaction(r, **log_kwargs)
        return r
