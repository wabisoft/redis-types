import os
import logging
from collections import namedtuple

from redis import StrictRedis


logger = logging.getLogger(__name__)

REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = os.getenv('REDIS_PORT', 6379)
REDIS = StrictRedis(host=REDIS_HOST, port=REDIS_PORT)

SortedItem = namedtuple('SortedItem', ['score', 'member'])


class RedisType(object):
    def __init__(self, key):
        self._key = key

    def key(self):
        return self._key

    def __str__(self):
        return self.key()

    def __repr__(self):
        return str(self)


class SortedSet(RedisType):
    def __init__(self, key):
        RedisType.__init__(self, key)

    def exists(self, member):  # type: (self, string) -> bool
        '''Tries to find a members rank to determine if the member exists in the set
           and returns True if it finds it or False if it does not'''
        rank = self.rank(member)
        return True if rank is not None else False

    def rank(self, member):  # type: (self, string) -> int
        '''Looks for a member in a sorted set at key
           and returns it's rank (0 based) if it exists or
           None if it does not'''
        return REDIS.zrank(self._key, member)

    def score(self, member):  # type: (self, string) -> float
        '''Same as rank but returns members actual score [-inf, +inf]'''
        return REDIS.zscore(self._key, member)

    def range(self, start, stop):  # type(self, string, string) -> [SortedItem(string, string)]
        '''gets a range from start to stop of the sorted set'''
        items = REDIS.zrange(self._key, start, stop, withscores=True)
        items = [SortedItem(score, member) for member, score in items]
        return items

    def revrange(self, start, stop):
        '''gets range from start to stop sorted in reverse order, revers of range'''
        items = REDIS.zrevrange(self._key, start, stop, withscores=True)
        items = [SortedItem(score, member) for member, score in items]
        return items

    def front(self):
        '''returns the first member in a redis sorted set without popping'''
        first = self.range(0, 0)  # returns a list of the zeroth tuple in the zset [(member, score)]
        if first:
            return first[0]
        else:
            return None

    def back(self):
        '''returns the last member in a redis sorted set without popping'''
        last = self.revrange(0, 0)
        if last:
            return last[0]
        else:
            return None

    def pop_front(self):
        '''Pops the first member in a redis sorted set'''
        first = self.front()
        if first:
            self.remove(first.member)
        return first

    def deshift(self):
        '''Pops (deshifts) first member in the sorted set'''
        first = self.front()
        if first:
            self.remove(first.member)
        return first

    def pop_back(self):
        '''Pops the last member in a redis sorted set'''
        last = self.last()
        if last:
            self.remove(last.member)
        return last

    def pop(self):
        '''Pops the last member in the sorted set'''
        last = self.last()
        if last:
            self.remove(last.member)
        return last

    def add(self, score, member):
        '''Adds a value to the sorted set at the score given'''
        return REDIS.zadd(self._key, score, member)

    def remove(self, member):
        '''Removes the specified member from the sorted set'''
        return REDIS.zrem(self._key, member)

    def cardinality(self):  # type: (self) -> int
        '''Returns the cardinality (number of elements) of the sorted set'''
        return REDIS.zcard(self._key)

    def __len__(self):
        return self.cardinality()


class Set(RedisType):
    def __init__(self, key):
        RedisType.__init__(self, key)

    def members(self):
        '''Return all the members of the set'''
        return REDIS.smembers(self._key)

    def randmember(self):
        '''Returns a random member of the set'''
        return REDIS.srandmember(self._key)

    def add(self, member):
        '''Adds a member to the set'''
        return REDIS.sadd(self._key, member)

    def remove(self, member):
        '''Removes a member from the set'''
        return REDIS.srem(self._key, member)

    def cardinality(self):
        '''Returns the cardinality (number of elements) of the set'''
        return REDIS.scard(self._key)

    def __len__(self):
        return self.cardinality()


class Hash(RedisType):
    def __init__(self, key):
        RedisType.__init__(self, key)

    @property
    def length(self):
        return REDIS.hlen(self._key)

    def get(self, field):
        '''Gets a value at the given key referenced by the given field'''
        return REDIS.hget(self._key, field)

    def set(self, field, value):
        '''Sets the specified field to the given value at the given key'''
        return REDIS.hset(self._key, field, value)

    def get_all(self):
        '''Returns all field/value pairs in the Hash'''
        return REDIS.hgetall(self._key)

    def delete(self, field):
        '''Deletes a field from the hash'''
        return REDIS.hdel(self._key, field)

    def __len__(self):
        return self.length


class List(RedisType):
    def __init__(self, key):
        RedisType.__init__(self, key)

    @property
    def length(self):
        return REDIS.llen(self._key)

    def push(self, value):
        return REDIS.rpush(self._key, value)

    def pop(self):
        return REDIS.rpop(self._key)

    def shift(self, value):
        return REDIS.lpush(self._key, value)

    def deshift(self):
        return REDIS.lpop(self._key)

    def __len__(self):
        return self.length
