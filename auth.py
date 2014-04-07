import bcrypt

class Auth(object):
    def __init__(self, obj={}):
        for field in self.FIELDS:
            setattr(self, field, "")

        self.__dict__.update(obj)

    def dump(self):
        base = {k: v for k, v in self.__dict__.items() if k in self.FIELDS}
        base['id'] = self.ID
        return base

    def is_valid(self, **kwargs): return False

class SimpleAuth(Auth):
    ID = 1
    FIELDS = ["password"]

    def set_password(self, pw):
        self.password = str(bcrypt.hashpw(pw, bcrypt.gensalt()))
        return True

    def is_valid(self, password):
        return bcrypt.hashpw(str(password), str(self.password)) == str(self.password)

AUTH = {
    SimpleAuth.ID: SimpleAuth
}

def get_auth(data):
    return AUTH.get(data.get("id"))(data)

def auth_check_any(li, acls, **kwargs):
    for auth in li:
        if isinstance(auth, acls):
            if auth.is_valid(**kwargs):
                break
    else:
        return False
    return True
