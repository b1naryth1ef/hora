from flask import Response, request
from functools import wraps
import ujson as json

error_from = lambda i: JsonResponse({"success": False, "error": {"code": i[0], "msg": i[1]}})

class JsonResponse(Response):
    def __init__(self, data, force=False):
        Response.__init__(self)
        if not force:
            data['success'] = data.get("success", True)
        self.data = json.dumps(data)
        self.headers['content-type'] = "application/json"

class APIException(Response):
    id = 0
    code = 500

    def __init__(self, msg, code=None):
        Response.__init__(self)
        self.headers['content-type'] = "application/json"
        self.status_code = code or self.code
        self.data = json.dumps({
            "success": False,
            "error": {
                "code": self.id,
                "msg": "%s: %s" % (self.__class__.__name__, msg)
            }
        })

class InvalidMethod(APIException):
    id = 1
    code = 405

class APIError(APIException):
    id = 2
    code = 400

def allow(*methods):
    def deco(a):
        def _f(*args, **kwargs):
            if request.method not in methods:
                return InvalidMethod("%s" % request.method)
            return a(*args, **kwargs)
        return _f
    return deco

def params(**required):
    def deco(b):
        @wraps(b)
        def _f(*args, **kwargs):
            gathered = {}
            for k, v in required.items():
                if k not in request.values:
                    return APIError("Requires paramater `%s`" % k)
                val = request.values[k]
                try:
                    val = v(val)
                except Exception as e:
                    return APIError("Paramater `%s` must be type `%s`" % (k, v))
                gathered[k] = val
            return b(**gathered)
        return _f
    return deco
