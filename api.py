from flask import Blueprint, request, g

from util import *
from database import *
from datetime import datetime
import json

# Versioning
API_LATEST_VERSION = 1
API_SUPPORTED_VERSIONS = [API_LATEST_VERSION]
API_DEPRECATED_VERSIONS = []

api = Blueprint("api", __name__)

@api.before_request
def api_pre():
    g.deprecated = False

    # Check the version of the request
    if "hora-version" in request.headers:
        version = request.headers["hora-version"]
        if not version.isdigit():
            return APIError("API Version must be integer")
        version = int(version)

        if not version in API_SUPPORTED_VERSIONS:
            return APIError("Invalid API Version `%s`, must be one of %s" %
                (version, API_SUPPORTED_VERSIONS))
        if version in API_DEPRECATED_VERSIONS:
            g.deprecated = True
        g.version = version
    else:
        return APIError("You must specify an API version in the header `hora-version`!")

    # Check the key and secret
    if "hora-key" in request.headers and "hora-secret" in request.headers:
        key, secret = request.headers["hora-key"], request.headers["hora-secret"]

        # Confirm the key and secret in conjunction to avoid brute-force
        #  attacks or guess attacks.
        try:
            auth = APIAuth.get((APIAuth.key == key) & (APIAuth.secret == secret))
        except APIAuth.DoesNotExist:
            return APIError("Invalid API Credentials!")

        g.realm = auth.realm
        g.auth = auth
    else:
        return APIError("You must be authenticated to make Hora API requests!")

@api.after_request
def api_post(resp):
    if g.deprecated:
        resp.headers["hora-warning"] = "API Version Deprecated!"

    return resp

@api.route("", methods=["HEAD", "GET"])
def api_base():
    return JsonResponse({
        "version": API_LATEST_VERSION,
        "status": {
            "id": 0,
            "msg": "ALL OK"
        }
    })

REGISTER_ERROR_INVALID = (1, "Invalid User Information!")
REGISTER_ERROR_EXISTS = (2, "User already exists!")

@api.route("/register/simple", methods=['POST'])
@params(username=str, password=str, data=json.loads)
def register_simple_route(username, password, data):
    if g.version in (1, ):
        # Validate username and password
        # TODO: validate chars
        if not username or not password:
            return error_from(REGISTER_ERROR_INVALID)

        try:
            User.get(User.username == username)
            return error_from(REGISTER_ERROR_EXISTS)
        except User.DoesNotExist: pass

        auth = SimpleAuth()
        auth.set_password(password)

        user = User(realm=g.realm, username=username, auth={
            "active": [auth.dump()]}, data=data)
        user.save()

        return JsonResponse({
            "userid": user.id
        })

LOGIN_ERROR_INVALID = (3, "Invalid Login Information")
LOGIN_INVALID_USERNAME = (4, "Invalid Login Information")
LOGIN_INVALID_PASSWORD = (5, "Invalid Login Information")
LOGIN_TOO_MANY_SESSIONS = (6, "User has too many active sessions")

@api.route("/login/simple", methods=['POST'])
@params(username=str, password=str, data=json.loads, tiny=int)
def login_simple_route(username, password, data, tiny):
    if g.version in (1, ):
        # TODO: validate chars
        if not username or not password:
            return error_from(LOGIN_ERROR_INVALID)

        try:
            u = User.get(
                (User.username == username) &
                (User.realm == g.realm.id))
        except User.DoesNotExist:
            return error_from(LOGIN_INVALID_USERNAME)

        # Check auth password
        if not auth_check_any(u.get_auth(), SimpleAuth, password=password):
            return error_from(LOGIN_INVALID_PASSWORD)

        # Check number of sessions
        num_sess = u.get_sessions().where(Session.expires > datetime.utcnow()).count()
        if num_sess >= g.realm.config['sessions']['max-count']:
            return error_from(LOGIN_TOO_MANY_SESSIONS)

        # Create new session
        sess = u.new_session(data)

        # Construct response payload
        payload = {
            "user": u.id,
            "session": sess.id,
            "data": {}
        }

        if not tiny:
            payload["data"] = u.data

        return JsonResponse(payload)


USER_DELETE_ERROR_INVALID = (7, "User does not exist in the system")

@api.route("/user/delete", methods=['POST', 'DELETE'])
@params(id=int)
def user_delete_route(id):
    if g.version in (1, ):
        try:
            u = User.get((User.id == id) & (User.realm == g.realm))
            u.delete()
            return JsonResponse({
                "deleted": True
            })
        except User.DoesNotExist:
            return error_from(USER_DELETE_ERROR_INVALID)


@api.route("/session/delete", methods=['POST', 'DELETE'])
@params(session_id=int)
def user_logout_route(session_id):
    """
    Deletes (invalidates) an active session
    """
    if g.version in (1, ):
        deleted = Session.remove(session_id, g.realm)
        return JsonResponse({
            "deleted": deleted
        })

@api.route("/session/valid", methods=['GET'])
@params(id=int)
def session_valid_route(id):
    if g.version in (1, ):
        return JsonResponse({"v": int(Session.check(id))}, True)
