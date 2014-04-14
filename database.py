from peewee import *
from playhouse.postgres_ext import *

from datetime import datetime, timedelta

# from twisted.internet import reactor, protocol
# from txredis.client import RedisClient
import redis
from auth import *

import random, string

def get_random_chars(i):
    full = ""
    for _ in range(i):
        full += random.choice(string.ascii_letters + string.punctuation)
    return full

REDIS = redis.Redis()

def get_redis():
    return REDIS

db = PostgresqlExtDatabase('hora', user="b1n", password="b1n", threadlocals=True)

class BaseModel(Model):
    class Meta:
        database = db

class Auth(BaseModel): pass

class Realm(BaseModel):
    name = CharField()
    config = JSONField()

class APIAuth(BaseModel):
    class Meta:
        indexes = ((('key', 'secret'), True),)

    realm = ForeignKeyField(Realm)

    key = CharField()
    secret = CharField()
    hash = CharField()

    @classmethod
    def create(cls, realm):
        self = cls()
        self.realm = realm
        self.key = "1"  # get_random_chars(24)
        self.secret = "1"  # get_random_chars(64)
        self.hash = get_random_chars(128)
        self.save()
        return self

class User(BaseModel):
    realm = ForeignKeyField(Realm)

    username = CharField()

    auth = JSONField()
    data = JSONField()

    created = DateTimeField(default=datetime.utcnow)

    def get_sessions(self):
        return Session.select().where((Session.user == self))

    def new_session(self, data={}):
        return Session.create(self, data)

    def get_auth(self):
        return map(get_auth, self.auth['active'])

class Session(BaseModel):
    user = ForeignKeyField(User)
    data = JSONField()
    created = DateTimeField(default=datetime.utcnow)
    expires = DateTimeField()

    @classmethod
    def create(cls, user, data):
        self = cls()
        self.user = user
        self.data = data
        duration = self.user.realm.config['sessions']['duration']
        self.expires = (datetime.utcnow() + timedelta(**duration))
        self.save()
        self.cache()
        return self

    def cache(self):
        redis = get_redis()
        redis.setex('session-%s' % self.id, 1, int(self.expires.strftime("%s")))

    @staticmethod
    def check(sid):
        redis = get_redis()
        value = redis.get("session-%s" % sid)
        if value:
            return True
        return False

    @staticmethod
    def remove(sid, realm):
        redis = get_redis()
        redis.delete("session-%s" % sid)
        try:
            s = Session.select().join(User).where(
                (Session.id == sid) & (User.realm == realm)).get()
            s.delete_instance()
            return True
        except Session.DoesNotExist:
            return False


tables = [Realm, APIAuth, User, Session]

if __name__ == "__main__":
    for table in tables:
        print "Recreating `%s`" % table.__name__
        table.drop_table(True, cascade=True)
        table.create_table(True)

    base = Realm(name="test", config={
        "sessions": {
            "duration": {
                "weeks": 4
            },
            "max-count": 24
        }
    })
    base.save()

    lunch = Realm(name="lunch", config={
        "sessions": {
            "duration": {
                "weeks": 4
            },
            "max-count": 24
        }
    })
    lunch.save()

    lauth = APIAuth.create(lunch)
    print "Lunch Key: `%s`, secret: `%s`" % (lauth.key, lauth.secret)

    auth = APIAuth.create(base)
    print "Key: `%s`, Secret: `%s`" % (auth.key, auth.secret)
