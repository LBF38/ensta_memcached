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

    def test_tiering(self):
        # Arrange
        tiering = Tiering(FS, AWS, MEM)
        content = FS.read("assets/image_small.jpg")
        tiering_filename = "image_small_tiering.jpg"
        cost = 1

        # Act & Assert
        log.info("##### test for cost < 100 #####")
        log.info("creating file in tiering")
        assert tiering_filename not in AWS.list()
        assert tiering_filename not in FS.list(".")
        assert MEM.read(tiering_filename) is None
        tiering.create(tiering_filename, content, cost)
        assert tiering_filename in AWS.list()
        assert tiering_filename not in FS.list(".")
        assert MEM.read(tiering_filename) is None

        log.info("reading file from tiering")
        content_tiering = tiering.read(tiering_filename, cost)
        assert content == content_tiering

        log.info("deleting file from tiering")
        tiering.delete(tiering_filename, cost)
        assert tiering_filename not in AWS.list()
        assert tiering_filename not in FS.list(".")
        assert MEM.read(tiering_filename) is None

        log.info("##### test for cost > 100 #####")
        cost = 101
        log.info("creating file in tiering")
        assert tiering_filename not in AWS.list()
        assert tiering_filename not in FS.list(".")
        assert MEM.read(tiering_filename) is None
        tiering.create(tiering_filename, content, cost)
        assert tiering_filename not in AWS.list()
        assert tiering_filename in FS.list(".")
        assert MEM.read(tiering_filename) is None

        log.info("reading file from tiering")
        content_tiering = tiering.read(tiering_filename, cost)
        assert content == content_tiering

        log.info("deleting file from tiering")
        tiering.delete(tiering_filename, cost)
        assert tiering_filename not in AWS.list()
        assert tiering_filename not in FS.list(".")
        assert MEM.read(tiering_filename) is None

        log.info("##### test for cost > 1000 #####")
        cost = 1001
        log.info("creating file in tiering")
        assert tiering_filename not in AWS.list()
        assert tiering_filename not in FS.list(".")
        assert MEM.read(tiering_filename) is None
        tiering.create(tiering_filename, content, cost)
        assert tiering_filename not in AWS.list()
        assert tiering_filename not in FS.list(".")
        assert MEM.read(tiering_filename) == content

        log.info("reading file from tiering")
        content_tiering = tiering.read(tiering_filename, cost)
        assert content == content_tiering

        log.info("deleting file from tiering")
        tiering.delete(tiering_filename, cost)
        assert tiering_filename not in AWS.list()
        assert tiering_filename not in FS.list(".")
        assert MEM.read(tiering_filename) is None

    def test_2level_cache(self):
        pass

    def test_auto_tiering(self):
        pass
