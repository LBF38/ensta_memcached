import unittest
import sys

sys.path.append("src")
from utils import LRU


class TestLRU(unittest.TestCase):
    def test_lru(self):
        lru = LRU(3)
        self.assertEqual(lru.read("K"), None)
        lru.create("K", 1)
        self.assertEqual(lru.read("K"), 1)

        lru.create("A", 2)
        self.assertEqual(lru.read("A"), 2)

        lru.create("B", 3)
        self.assertEqual(lru.read("B"), 3)

        lru.create("C", 4)
        self.assertEqual(lru.read("C"), 4)
        self.assertEqual(lru.read("K"), None)
        self.assertEqual(lru.read("A"), 2)
        lru.create("K", 5)
        self.assertEqual(lru.read("A"), 2)
        self.assertEqual(lru.read("K"), 5)
        self.assertEqual(lru.read("B"), None)

        lru.delete("A")
        self.assertEqual(lru.read("A"), None)


if __name__ == "__main__":
    unittest.main()