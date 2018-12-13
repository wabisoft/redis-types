import os
import sys
import logging
from distutils.version import StrictVersion
from collections import namedtuple
from typing import List as ListType
from typing import Any, Iterator


logger = logging.getLogger(__name__)

redis_client = None


def initialize(client_instance):
    global redis_client
    redis_client = client_instance

def set_encoding(encoder=None, decoder=None):
    RedisType.__encoder__ = encoder or _NoOpEncoder
    RedisType.__decoder__ = decoder or _NoOpDecoder


def redis_version(redis_client):
    return StrictVersion(redis_client.execute_command("INFO")["redis_version"])

def ping():
    return redis_client.ping()

class ConfiurationError(Exception):
    def __init__(self, msg):
        self.msg = msg
        self.redis_client = redis_client


class _NoOpEncoder:
    def encode(self, value):
        return value


class _NoOpDecoder:
    def decode(self, value):
        return value


class RedisType(object):
    __encoder__ = _NoOpEncoder
    __decoder__ = _NoOpDecoder

    def __init__(self, key: str, use_client=None, encoder_class=None, decoder_class=None) -> None:
        self._key = key
        self._client = use_client or redis_client
        self._encoder = encoder_class() if encoder_class else self.__encoder__()
        self._decoder = decoder_class() if decoder_class else self.__decoder__()
        if not self._client:
            raise ConfiurationError("Redis Client is not configured, please call redis_types.initialize before using")

    def key(self) -> str:
        return self._key

    def __str__(self) -> str:
        return self.key()

    def __repr__(self) -> str:
        return str(self)


class ZSet(RedisType):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.withscores = False

    def __contains__(self, item: Any) -> bool:
        return (
            self._client.zscore(self._key, self._encoder.encode(item)) is not None
        )

    def __len__(self):
        return self._client.zcard(self._key)

    def __getitem__(self, indices: slice) -> ListType[Any]:
        """Sugar on range and revrange"""
        if not isinstance(indices, slice):
            raise IndexError(
                "ZSet does not support direct indexing, use a slice instead"
            )
        if indices.step == -1:
            return self.revrange(
                indices.start or 0, indices.stop if indices.stop is not None else -1
            )
        return self.range(
            indices.start or 0, indices.stop if indices.stop is not None else -1
        )[:: indices.step]

    def rank(self, member: Any) -> int:
        """Get index of member"""
        return self._client.zrank(self._key, self._encoder.encode(member))

    def score(self, member: Any) -> float:
        """Get score of member"""
        return self._client.zscore(self._key, self._encoder.encode(member))

    def range(self, start: int, stop: int, withscores: bool = False) -> ListType[Any]:
        withscores = withscores or self.withscores
        return [
            (self._decoder.decode(i[0]), i[1])
            if withscores
            else self._decoder.decode(i)
            for i in self._client.zrange(
                self._key, start, stop, withscores=withscores
            )
        ]

    def revrange(self, start: int, stop: int, withscores: bool = False) -> ListType[Any]:
        withscores = withscores or self.withscores
        return [
            (self._decoder.decode(i[0]), i[1])
            if withscores
            else self._decoder.decode(i)
            for i in self._client.zrevrange(
                self._key, start, stop, withscores=withscores
            )
        ]

    def front(self, withscore=False):
        """returns the first member in a redis sorted set without popping"""
        ret = self.range(0, 0, withscores=withscore) # weird in python but legal in redis
        return ret[0] if ret else None 

    def back(self, withscore=False):
        """returns the last member in a redis sorted set without popping"""
        ret = self.range(-1, -1, withscores=withscore) # weird in python but legal in redis
        return ret[0] if ret else None 

    def unshift(self, count: int = 1) -> Any:
        """Pops the first `count` members from the from of set in a redis sorted set"""
        if redis_version(self._client) < StrictVersion("5.0.0"):
            front = self.range(0, count-1, withscores = True)
            for i in front:
                self.remove(i[0])
            return front
        return [(self._decoder.decode(i[0]), i[1]) for i in self._client.zpopmin(self._key, count=count)]

    def pop(self, count: int = 1) -> Any:
        if redis_version(self._client) < StrictVersion("5.0.0"):
            back = self.revrange(0, count-1, withscores = True)
            for i in back:
                self.remove(i[0])
            return back
        return [(self._decoder.decode(i[0]), i[1]) for i in self._client.zpopmax(self._key, count=count)]

    def add(self, mapping):
        """Adds a value to the sorted set at the score given"""
        mapping = {
            self._encoder.encode(key): value for key, value in mapping.items()
        }
        return self._client.zadd(self._key, mapping)

    def remove(self, member):
        """Removes the specified member from the sorted set"""
        return self._client.zrem(self._key, self._encoder.encode(member))

    def card(self) -> int:
        """Returns the cardinality (number of elements) of the sorted set"""
        return len(self)


class Set(RedisType):
    def __contains__(self, item):
        return self._client.sismember(self._decoder.decode(item))

    def __len__(self):
        return self._client.scard(self._key)

    def members(self):
        """Return all the members of the set"""
        return {self._decoder.decode(i) for i in self._client.smembers(self._key)}

    def randmember(self):
        """Returns a random member of the set"""
        return self._decoder.decode(self._client.srandmember(self._key))

    def add(self, member):
        """Adds a member to the set"""
        return self._client.sadd(self._key, self._encoder.encode(member))

    def remove(self, member):
        """Removes a member from the set"""
        return self._client.srem(self._key, self._encoder.encode(member))

    def cardinality(self):
        """Returns the cardinality (number of elements) of the set"""
        return len(self)


class Hash(RedisType):
    def __len__(self) -> int:
        return self._client.hlen(self._key)

    def __getitem__(self, key)-> Any:
        return self.get(key)

    def __setitem__(self, key, value) -> None:
        return self.set(key, value)
    
    def __delitem__(self, key) -> None:
        return self.delete(key)

    def __iter__(self) -> Iterator:
        return iter(self.items())

    def __contains__(self, key):
        return self._client.hexists(self._key, key)

    def get(self, field):
        """Gets a value at the given key referenced by the given field"""
        return self._client.hget(self._key, field)

    def set(self, field, value):
        """Sets the specified field to the given value at the given key"""
        return self._client.hset(self._key, field, self._encoder.encode(value))

    def getall(self):
        """Returns all field/value pairs in the Hash"""
        return {
            key: self._decoder.decode(value)
            for key, value in self._client.hgetall(self._key).items()
        }

    def keys(self):
        return set(self._client.hkeys(self._key))

    def values(self):
        return {self._decoder.decode(i) for i in self._client.hvals(self._key)}

    def items(self):
        return self.getall().items()

    def delete(self, field):
        """Deletes a field from the hash"""
        return self._client.hdel(self._key, self._encoder.encode(field))

    def update(self, mapping):
        """Updates the hash map with mapping"""
        return self._client.hmset(self._key, {key: self._encoder.encode(value) for key, value in mapping.items()})


class List(RedisType):
    def __len__(self):
        return self._client.llen(self._key)

    def __bool__(self):
        return len(self) > 0

    def __getitem__(self, index):
        if isinstance(index, slice):
            return self.lrange(index.start, index.stop)[:: index.step]
        return self.lindex(index)

    def lindex(self, index):
        return self._decoder.decode(self._client.lindex(index))

    def lrange(self, start, stop):
        return [
            self._decoder.decode(i)
            for i in self._client.lrange(self._key, start, stop)
        ]

    def shift(self, item):
        self._client.lpush(self._key, self._encoder.encode(item))

    def unshift(self):
        return self._decoder.decode(self._client.lpop(self._key))

    def push(self, item):
        self._client.rpush(self._key, self._encoder.encode(item))

    def pop(self):
        return self._decoder.decode(self._client.rpop(self._key))
