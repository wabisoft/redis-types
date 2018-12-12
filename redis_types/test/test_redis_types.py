import unittest
import json

from redis import StrictRedis

from .. import ZSet, initialize

redis = StrictRedis(host="localhost", decode_responses=True)


class TestZSet(unittest.TestCase):
    def setUpClass():
        initialize(redis)

    def setUp(self):
        try:
            self.zset = ZSet("test_zset")
        except Exception as err:
            raise unittest.SkipTest(err.args)

    def test_init(self):
        self.zset.__client__.ping()

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
        self.assertEqual(["1"], self.zset.front())
        self.assertEqual(["3"], self.zset.back())
        self.assertEqual([("1", 1)], self.zset.unshift())
        self.assertEqual([("3", 3)], self.zset.pop())
        self.assertEqual(1, len(self.zset))


class TestJSONZSet(TestZSet):
    def setUp(self):
        try:
            self.zset = ZSet("test_zset_json")
        except Exception as err:
            raise unittest.SkipTest(err.args)

        self.zset.__encoder__ = json.JSONEncoder()
        self.zset.__decoder__ = json.JSONDecoder()
