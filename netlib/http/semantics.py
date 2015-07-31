from __future__ import (absolute_import, print_function, division)
import binascii
import collections
import string
import sys
import urlparse

from .. import utils, odict

CONTENT_MISSING = 0


class ProtocolMixin(object):

    def read_request(self):
        raise NotImplemented

    def read_response(self):
        raise NotImplemented

    def assemble(self, message):
        if isinstance(message, Request):
            return self.assemble_request(message)
        elif isinstance(message, Response):
            return self.assemble_response(message)
        else:
            raise ValueError("HTTP message not supported.")

    def assemble_request(self, request):
        raise NotImplemented

    def assemble_response(self, response):
        raise NotImplemented


class Request(object):

    def __init__(
        self,
        form_in,
        method,
        scheme,
        host,
        port,
        path,
        httpversion,
        headers=None,
        body=None,
        timestamp_start=None,
        timestamp_end=None,
    ):
        if not headers:
            headers = odict.ODictCaseless()
        assert isinstance(headers, odict.ODictCaseless)

        self.form_in = form_in
        self.method = method
        self.scheme = scheme
        self.host = host
        self.port = port
        self.path = path
        self.httpversion = httpversion
        self.headers = headers
        self.body = body
        self.timestamp_start = timestamp_start
        self.timestamp_end = timestamp_end


    def __eq__(self, other):
        try:
            self_d = [self.__dict__[k] for k in self.__dict__ if k not in ('timestamp_start', 'timestamp_end')]
            other_d = [other.__dict__[k] for k in other.__dict__ if k not in ('timestamp_start', 'timestamp_end')]
            return self_d == other_d
        except:
            return False

    def __repr__(self):
        return "Request(%s - %s, %s)" % (self.method, self.host, self.path)

    @property
    def content(self):
        # TODO: remove deprecated getter
        return self.body

    @content.setter
    def content(self, content):
        # TODO: remove deprecated setter
        self.body = content


class EmptyRequest(Request):
    def __init__(self):
        super(EmptyRequest, self).__init__(
            form_in="",
            method="",
            scheme="",
            host="",
            port="",
            path="",
            httpversion=(0, 0),
            headers=odict.ODictCaseless(),
            body="",
            )


class Response(object):

    def __init__(
        self,
        httpversion,
        status_code,
        msg=None,
        headers=None,
        body=None,
        sslinfo=None,
        timestamp_start=None,
        timestamp_end=None,
    ):
        if not headers:
            headers = odict.ODictCaseless()
        assert isinstance(headers, odict.ODictCaseless)

        self.httpversion = httpversion
        self.status_code = status_code
        self.msg = msg
        self.headers = headers
        self.body = body
        self.sslinfo = sslinfo
        self.timestamp_start = timestamp_start
        self.timestamp_end = timestamp_end


    def __eq__(self, other):
        try:
            self_d = [self.__dict__[k] for k in self.__dict__ if k not in ('timestamp_start', 'timestamp_end')]
            other_d = [other.__dict__[k] for k in other.__dict__ if k not in ('timestamp_start', 'timestamp_end')]
            return self_d == other_d
        except:
            return False

    def __repr__(self):
        return "Response(%s - %s)" % (self.status_code, self.msg)

    @property
    def content(self):
        # TODO: remove deprecated getter
        return self.body

    @content.setter
    def content(self, content):
        # TODO: remove deprecated setter
        self.body = content

    @property
    def code(self):
        # TODO: remove deprecated getter
        return self.status_code

    @code.setter
    def code(self, code):
        # TODO: remove deprecated setter
        self.status_code = code



def is_valid_port(port):
    if not 0 <= port <= 65535:
        return False
    return True


def is_valid_host(host):
    try:
        host.decode("idna")
    except ValueError:
        return False
    if "\0" in host:
        return None
    return True


def parse_url(url):
    """
        Returns a (scheme, host, port, path) tuple, or None on error.

        Checks that:
            port is an integer 0-65535
            host is a valid IDNA-encoded hostname with no null-bytes
            path is valid ASCII
    """
    try:
        scheme, netloc, path, params, query, fragment = urlparse.urlparse(url)
    except ValueError:
        return None
    if not scheme:
        return None
    if '@' in netloc:
        # FIXME: Consider what to do with the discarded credentials here Most
        # probably we should extend the signature to return these as a separate
        # value.
        _, netloc = string.rsplit(netloc, '@', maxsplit=1)
    if ':' in netloc:
        host, port = string.rsplit(netloc, ':', maxsplit=1)
        try:
            port = int(port)
        except ValueError:
            return None
    else:
        host = netloc
        if scheme == "https":
            port = 443
        else:
            port = 80
    path = urlparse.urlunparse(('', '', path, params, query, fragment))
    if not path.startswith("/"):
        path = "/" + path
    if not is_valid_host(host):
        return None
    if not utils.isascii(path):
        return None
    if not is_valid_port(port):
        return None
    return scheme, host, port, path


def get_header_tokens(headers, key):
    """
        Retrieve all tokens for a header key. A number of different headers
        follow a pattern where each header line can containe comma-separated
        tokens, and headers can be set multiple times.
    """
    toks = []
    for i in headers[key]:
        for j in i.split(","):
            toks.append(j.strip())
    return toks