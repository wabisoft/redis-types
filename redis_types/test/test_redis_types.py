import unittest
import json

from redis import StrictRedis

from .. import initialize, set_encoding, ping
from .. import ZSet, Hash

redis = StrictRedis(host="localhost", decode_responses=True)


class TestZSet(unittest.TestCase):
    def setUpClass():
        initialize(redis)
        set_encoding()

    def setUp(self):
        try:
            self.zset = ZSet("test_zset")
        except Exception as err:
            raise unittest.SkipTest(err.args)

    def test_init(self):
        ping()

    def test_methods(self):
        values = {"1": 1, "2": 2, "3": 3}
        self.zset.add(values)
        self.assertTrue("1" in self.zset)
        self.assertEqual(len(values), len(self.zset))
        self.assertEqual(["1", "2", "3"], self.zset[::])
        self.assertEqual(["1", "2", "3"][::-1], self.zset[::-1])
        self.zset.withscores = True
        self.assertEqual([("1", 1), ("2", 2), ("3", 3)], self.zset[::])
        self.zset.withscores = False
        self.assertEqual(0, self.zset.rank("1"))
        self.assertEqual(1, self.zset.score("1"))
        self.assertEqual("1", self.zset.front())
        self.assertEqual("3", self.zset.back())
        self.assertEqual([("1", 1)], self.zset.unshift())
        self.assertEqual([("3", 3)], self.zset.pop())
        self.assertEqual(1, len(self.zset))


class TestJSONZSet(TestZSet):
    def setUpClass():
        initialize(redis)
        set_encoding(encoder=json.JSONEncoder, decoder=json.JSONDecoder)

    def setUp(self):
        try:
            self.zset = ZSet("test_zset_json")
        except Exception as err:
            raise unittest.SkipTest(err.args)



class TestHash(unittest.TestCase):
    def setUpClass():
        initialize(redis)
        set_encoding()

    def setUp(self):
        try:
            redis.delete("test_hash")
            self.hash = Hash("test_hash")
        except Exception as err:
            raise unittest.SkipTest(str(err))

    def test_methods(self):
        self.hash["1"] = "one"
        self.hash["2"] = "two"
        self.hash["3"] = "three"
        self.assertEqual(3, len(self.hash))
        self.assertTrue("1" in self.hash)
        self.assertEqual({"1", "2", "3"}, self.hash.keys())
        self.assertEqual({"one", "two", "three"}, self.hash.values())
        self.assertEqual({("1", "one"), ("2", "two"), ("3", "three")}, set(self.hash.items()))
        del self.hash["1"]
        self.assertTrue("1" not in self.hash)
        self.hash.update({"4": "four", "5": "five"})
        self.assertEqual({"2", "3", "4", "5"}, self.hash.keys())
