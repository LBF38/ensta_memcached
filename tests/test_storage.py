import logging
import sys
import unittest

sys.path.append("src")
from memcache import Client
from utils import AWSS3, FileSystem, Mem, Replica, Tiering

logging.basicConfig(level=logging.INFO)

FS = FileSystem()
client = Client(["localhost"], debug=0)
MEM = Mem(client)
AWS = AWSS3()
log = logging.getLogger("test_storage")


class TestStorage(unittest.TestCase):
    def test_replica(self):
        # Arrange
        replica = Replica(FS, AWS)
        content = FS.read("assets/image_small.jpg")
        replica_filename = "image_small_replica.jpg"

        # Act & Assert
        log.info("creating file in replica")
        assert replica_filename not in AWS.list()
        assert replica_filename not in FS.list(".")
        replica.create(replica_filename, content)
        assert replica_filename in AWS.list()
        assert replica_filename in FS.list(".")

        log.info("reading file from replica")
        content_replica = replica.read(replica_filename)
        assert content == content_replica

        log.info("deleting file from replica")
        replica.delete(replica_filename)
        assert replica_filename not in AWS.list()
        assert replica_filename not in FS.list(".")
