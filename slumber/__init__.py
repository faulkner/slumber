__version__ = "dev"

__author__ = "Donald Stufft"
__email__ = "donald.stufft@gmail.com"

__description__ = "A library that makes consuming a ReST API easier and more convenient"
__url__ = "https://github.com/dstufft/slumber/"

__all__ = ["Resource", "API"]

import httplib2
import json # @@@ Should we look for one with speedups?
import urlparse

from slumber.http import HttpClient

class Resource(object):

    def __init__(self, domain, list_endpoint=None, schema=None):
        self.domain = domain
        self.endpoints = {}
        self.schema = None

        if list_endpoint is not None:
            self.endpoints["list"] = list_endpoint
        if schema is not None:
            self.endpoints["schema"] = schema

        self.discover_schema()

    def discover_schema(self):
        if self.endpoints.has_key("schema"):
            h = httplib2.Http()
            resp, content = h.request(self.domain + self.endpoints["schema"])
            self.schema = json.loads(content)


class APIMeta(object):

    resources = {}
    http = {
        "schema": "http",
        "hostname": None,
        "port": "80",
        "path": "/",

        "params": "",
        "query": "",
        "fragment": "",
    }

    def __init__(self, **kwargs):
        for key, value in kwargs.iteritems():
            default_value = getattr(self, key)
            
            if isinstance(default_value, dict) and isinstance(value, dict):
                setattr(self, key, default_value.update(value))
            else:
                setattr(self, key, value)

    @property
    def base_url(self):
        ORDERING = ["schema", "hostname", "port", "path", "params", "query", "fragment"]
        urlparts = []
        for key in ORDERING:
            if key in ["path"]:
                urlparts.append("")
            else:
                urlparts.append(self.http[key])
        return urlparse.urlunparse(urlparts[:1] + [":".join([str(x) for x in urlparts[1:3]])] + urlparts[3:])

    @property
    def api_url(self):
        ORDERING = ["schema", "hostname", "port", "path", "params", "query", "fragment"]
        urlparts = []
        for key in ORDERING:
            urlparts.append(self.http[key])
        return urlparse.urlunparse(urlparts[:1] + [":".join([str(x) for x in urlparts[1:3]])] + urlparts[3:])


class API(object):

    def __init__(self, api_url=None):
        class_meta = getattr(self, "Meta", None)
        if class_meta is not None:
            keys = [x for x in dir(class_meta) if not x.startswith("_")]
            meta_dict = dict([(x, getattr(class_meta, x)) for x in keys])
        else:
            meta_dict = {}

        self._meta = APIMeta(**meta_dict)

        if api_url is not None:
            # Attempt to parse the url into it's parts
            parsed = urlparse.urlparse(api_url)
            for key in self._meta.http.keys():
                val = getattr(parsed, key, None)
                if val:
                    self._meta.http[key] = val

        self.http_client = HttpClient()

        self.discover_resources()

    def discover_resources(self):
        resp, content = self.http_client.get(self._meta.api_url)

        resources = json.loads(content)
        for name, resource in resources.iteritems():
            kwargs = dict(
                [x for x in resource.items() if x[0] in ["list_endpoint", "schema"]]
            )
            kwargs.update({
                "domain": self._meta.base_url,
            })
            self._meta.resources[name] = Resource(**kwargs) 