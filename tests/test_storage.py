import logging
import sys
import unittest

import pytest

sys.path.append("src")
from memcache import Client
from utils import (
    AWSS3,
    Auto_tiering,
    FileSystem,
    Mem,
    Replica,
    Tiering,
    TwoLevelCaching,
)

logging.basicConfig(level=logging.DEBUG)

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
        self.__assertStorage(replica_filename, content, aws=False, fs=False)
        replica.create(replica_filename, content)
        self.__assertStorage(replica_filename, content, aws=True, fs=True)

        log.info("reading file from replica")
        content_replica = replica.read(replica_filename)
        assert content == content_replica

        log.info("deleting file from replica")
        replica.delete(replica_filename)
        self.__assertStorage(replica_filename, content, aws=False, fs=False)

    def test_tiering(self):
        # Arrange
        tiering = Tiering(FS, AWS, MEM)
        content = FS.read("assets/image_small.jpg")
        tiering_filename = "image_small_tiering.jpg"
        cost = 1

        # Act & Assert
        log.info("##### test for cost < 100 #####")
        log.info("creating file in tiering")
        self.__assertStorage(tiering_filename, content, aws=False, fs=False, mem=False)
        tiering.create(tiering_filename, content, cost)
        self.__assertStorage(tiering_filename, content, aws=True, fs=False, mem=False)

        log.info("reading file from tiering")
        content_tiering = tiering.read(tiering_filename, cost)
        assert content == content_tiering

        log.info("deleting file from tiering")
        tiering.delete(tiering_filename, cost)
        self.__assertStorage(tiering_filename, content, aws=False, fs=False, mem=False)

        log.info("##### test for cost > 100 #####")
        cost = 101
        log.info("creating file in tiering")
        self.__assertStorage(tiering_filename, content, aws=False, fs=False, mem=False)
        tiering.create(tiering_filename, content, cost)
        self.__assertStorage(tiering_filename, content, aws=False, fs=True, mem=False)

        log.info("reading file from tiering")
        content_tiering = tiering.read(tiering_filename, cost)
        assert content == content_tiering

        log.info("deleting file from tiering")
        tiering.delete(tiering_filename, cost)
        self.__assertStorage(tiering_filename, content, aws=False, fs=False, mem=False)

        log.info("##### test for cost > 1000 #####")
        cost = 1001
        log.info("creating file in tiering")
        self.__assertStorage(tiering_filename, content, aws=False, fs=False, mem=False)
        tiering.create(tiering_filename, content, cost)
        self.__assertStorage(tiering_filename, content, aws=False, fs=False, mem=True)

        log.info("reading file from tiering")
        content_tiering = tiering.read(tiering_filename, cost)
        assert content == content_tiering

        log.info("deleting file from tiering")
        tiering.delete(tiering_filename, cost)
        self.__assertStorage(tiering_filename, content, aws=False, fs=False, mem=False)

    def test_two_level_caching(self):
        # Arrange
        with pytest.raises(AssertionError):
            two_level_caching = TwoLevelCaching(MEM.client, 10, 100)
        two_level_caching = TwoLevelCaching(MEM.client, 10, 5)
        content = FS.read("assets/image_small.jpg")
        two_level_caching_filename = "image_small_two_level_caching.jpg"

        # Act & Assert
        log.info("creating file in two_level_caching")
        self.__assertStorage(
            two_level_caching_filename, content, aws=False, fs=False, mem=False
        )
        two_level_caching.create(two_level_caching_filename, content)
        self.__assertStorage(
            two_level_caching_filename, content, aws=True, fs=True, mem=True
        )

        log.info("reading file from two_level_caching")
        content_two_level_caching = two_level_caching.read(two_level_caching_filename)
        assert content == content_two_level_caching

        log.info("deleting file from two_level_caching")
        two_level_caching.delete(two_level_caching_filename)
        self.__assertStorage(
            two_level_caching_filename, content, aws=False, fs=False, mem=False
        )

    def test_auto_tiering(self):
        # Arrange
        auto_tiering = Auto_tiering(FS, AWS, MEM)
        content = FS.read("assets/image_small.jpg")
        auto_tiering_filename = "image_small_auto_tiering.jpg"

        # Act & Assert
        log.info("creating file in auto_tiering")
        self.__assertStorage(
            auto_tiering_filename, content, aws=False, fs=False, mem=False
        )
        auto_tiering.create(auto_tiering_filename, content)
        self.__assertStorage(
            auto_tiering_filename, content, aws=True, fs=False, mem=False
        )

        log.info("reading file from auto_tiering")
        log.info("testing the auto tiering w/ lots of reads - 100 < cost < 1000")
        for i in range(200):
            content_auto_tiering = auto_tiering.read(auto_tiering_filename)
            assert content == content_auto_tiering
        self.__assertStorage(
            auto_tiering_filename, content, aws=False, fs=True, mem=False
        )

        log.info("testing the auto tiering w/ lots of reads - cost >= 1000")
        for i in range(2000):
            content_auto_tiering = auto_tiering.read(auto_tiering_filename)
            assert content == content_auto_tiering
        self.__assertStorage(
            auto_tiering_filename, content, aws=False, fs=False, mem=True
        )

        log.info("deleting file from auto_tiering")
        auto_tiering.delete(auto_tiering_filename)
        self.__assertStorage(
            auto_tiering_filename, content, aws=False, fs=False, mem=False
        )

    def __assertStorage(
        self,
        filename: str,
        content: bytes,
        aws: bool | None = None,
        fs: bool | None = None,
        mem: bool | None = None,
    ):
        if aws is True:
            assert filename in AWS.list()
        elif aws is False:
            assert filename not in AWS.list()
        if fs is True:
            assert filename in FS.list(".")
        elif fs is False:
            assert filename not in FS.list(".")
        if mem is True:
            assert MEM.read(filename) == content
        elif mem is False:
            assert MEM.read(filename) is None
