import os
import sys
import logging
from distutils.version import StrictVersion
from collections import namedtuple
from typing import List as ListType
from typing import Any

import redis

logger = logging.getLogger(__name__)

redis_client = None


def initialize(client_instance):
    global redis_client
    redis_client = client_instance


def redis_version(redis_client):
    return StrictVersion(redis_client.execute_command("INFO")["redis_version"])


class _NoOpEncoder:
    def encode(self, value):
        return value


class _NoOpDecoder:
    def decode(self, value):
        return value


class RedisType(object):
    __encoder__ = _NoOpEncoder()
    __decoder__ = _NoOpDecoder()
    __client__: redis.Redis = None

    def __init__(self, key: str, use_client=None) -> None:
        self._key = key
        self.__client__ = use_client or redis_client

    def key(self) -> str:
        return self._key

    def __str__(self) -> str:
        return self.key()

    def __repr__(self) -> str:
        return str(self)


class ZSet(RedisType):
    def __init__(self, key: str) -> None:
        RedisType.__init__(self, key)
        self.withscores = False

    def __contains__(self, item: Any) -> bool:
        return (
            self.__client__.zscore(self._key, self.__encoder__.encode(item)) is not None
        )

    def __len__(self):
        return self.__client__.zcard(self._key)

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
        return self.__client__.zrank(self._key, self.__encoder__.encode(member))

    def score(self, member: Any) -> float:
        """Get score of member"""
        return self.__client__.zscore(self._key, self.__encoder__.encode(member))

    def range(self, start: int, stop: int) -> ListType[Any]:
        return [
            (self.__decoder__.decode(i[0]), i[1])
            if self.withscores
            else self.__decoder__.decode(i)
            for i in self.__client__.zrange(
                self._key, start, stop, withscores=self.withscores
            )
        ]

    def revrange(self, start: int, stop: int) -> ListType[Any]:
        return [
            (self.__decoder__.decode(i[0]), i[1])
            if self.withscores
            else self.__decoder__.decode(i)
            for i in self.__client__.zrevrange(
                self._key, start, stop, withscores=self.withscores
            )
        ]

    def front(self):
        """returns the first member in a redis sorted set without popping"""
        return self[0:0]  # weird in python but legal in redis

    def back(self):
        """returns the last member in a redis sorted set without popping"""
        return self[-1:-1]  # weird in python but legal in redis

    def unshift(self, count: int = 1) -> Any:
        """Pops the first `count` members from the from of set in a redis sorted set"""
        if redis_version(self.__client__) < StrictVersion("5.0.0"):
            self.withscores = True
            ret = self.front()
            self.withscores = False
            self.remove(ret[0])
            return (self.__decoder__.decode(ret[0]), ret[1])
        return [
            (self.__decoder__.decode(i[0]), i[1])
            for i in self.__client__.zpopmin(self._key, count=count)
        ]

    def pop(self, count: int = 1) -> Any:
        if redis_version(self.__client__) < StrictVersion("5.0.0"):
            self.withscores = True
            ret = self.back()
            self.withscores = False
            self.remove(ret[0])
            return (self.__decoder__.decode(ret[0]), ret[1])
        return [
            (self.__decoder__.decode(i[0]), i[1])
            for i in self.__client__.zpopmax(self._key, count=count)
        ]

    def add(self, mapping):
        """Adds a value to the sorted set at the score given"""
        mapping = {
            self.__encoder__.encode(key): value for key, value in mapping.items()
        }
        return self.__client__.zadd(self._key, mapping)

    def remove(self, member):
        """Removes the specified member from the sorted set"""
        return self.__client__.zrem(self._key, self.__encoder__.encode(member))

    def card(self) -> int:
        """Returns the cardinality (number of elements) of the sorted set"""
        return len(self)


class Set(RedisType):
    def __init__(self, key):
        RedisType.__init__(self, key)

    def __contains__(self, item):
        return self.__client__.sismember(self.__decoder__.decode(item))

    def __len__(self):
        return self.__client__.scard(self._key)

    def members(self):
        """Return all the members of the set"""
        return {self.__decoder__.decode(i) for i in self.__client__.smembers(self._key)}

    def randmember(self):
        """Returns a random member of the set"""
        return self.__decoder__.decode(self.__client__.srandmember(self._key))

    def add(self, member):
        """Adds a member to the set"""
        return self.__client__.sadd(self._key, self.__encoder__.encode(member))

    def remove(self, member):
        """Removes a member from the set"""
        return self.__client__.srem(self._key, self.__encoder__.encode(member))

    def cardinality(self):
        """Returns the cardinality (number of elements) of the set"""
        return len(self)


class Hash(RedisType):
    def __init__(self, key):
        RedisType.__init__(self, key)

    def __len__(self):
        return self.__client__.hlen(self._key)

    def __getitem__(self, key):
        return self.get(key)

    def __setitem__(self, key, value):
        return self.set(key, value)

    def get(self, field):
        """Gets a value at the given key referenced by the given field"""
        return self.__client__.hget(self._key, field)

    def set(self, field, value):
        """Sets the specified field to the given value at the given key"""
        return self.__client__.hset(self._key, field, self.__encoder__.encode(value))

    def get_all(self):
        """Returns all field/value pairs in the Hash"""
        return {
            key: self.__decoder__.decode(value)
            for key, value in self.__client__.hgetall(self._key).items()
        }

    def delete(self, field):
        """Deletes a field from the hash"""
        return self.__client__.hdel(self._key, field)


class List(RedisType):
    def __init__(self, key):
        RedisType.__init__(self, key)

    def __len__(self):
        return self.__client__.llen(self._key)

    def __bool__(self):
        return len(self) > 0

    def __getitem__(self, index):
        if isinstance(index, slice):
            return self.lrange(index.start, index.stop)[:: index.step]
        return self.lindex(index)

    def lindex(self, index):
        return self.__decoder__.decode(self.__client__.lindex(index))

    def lrange(self, start, stop):
        return [
            self.__decoder__.decode(i)
            for i in self.__client__.lrange(self._key, start, stop)
        ]

    def shift(self, item):
        self.__client__.lpush(self._key, self.__encoder__.encode(item))

    def unshift(self):
        return self.__decoder__.decode(self.__client__.lpop(self._key))

    def push(self, item):
        self.__client__.rpush(self._key, self.__encoder__.encode(item))

    def pop(self):
        return self.__decoder__.decode(self.__client__.rpop(self._key))
