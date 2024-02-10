import logging
import os
from utils.LRU import LRU
from utils.base_storage import Storage
from memcache import Client


class Mem_LRU(Storage):
    def __init__(self, client: Client, capacity: int = 10) -> None:
        self.client = client
        self.lru = LRU(capacity)
        self.log = logging.getLogger("Mem LRU")
        self.log.debug("init - client %s", client.__class__.__name__)

    def create(self, key: str, value: bytes):
        self.log.debug("create - key: %s", key)
        del_key = self.lru.create(key, key)
        self.client.set(key, value)
        if del_key:
            self.client.delete(del_key)

    def read(self, key: str) -> bytes | None:
        self.log.debug("read - key: %s", key)
        key = self.lru.read(key)
        if key is None:
            self.log.warn("read - key not found")
            # raise ValueError(f"Key {key} not found")
            return None
        value = self.client.get(key)
        self.log.debug("read - value: %s", key[:10])
        return value

    def delete(self, key: str):
        self.log.debug("delete - key: %s", key)
        self.lru.delete(key)
        self.client.delete(key)
        self.log.debug("delete - done")


class FileSystem_LRU(Storage):
    def __init__(self, capacity: int = 10) -> None:
        self.log = logging.getLogger("FileSystem LRU")
        self.lru = LRU(capacity)

    def list(self, directory: str):
        self.log.debug("list - directory: %s", directory)
        return os.listdir(directory)

    def create(self, filename: str, data: bytes):
        self.log.debug("create - filename: %s", filename)
        del_filename = self.lru.create(filename, filename)
        with open(filename, "wb") as file:
            file.write(data)
        if del_filename:
            self.delete(del_filename)

    def delete(self, filename: str):
        self.log.debug("delete - filename: %s", filename)
        self.lru.delete(filename)
        os.remove(filename)

    def read(self, filename: str):
        self.log.debug("read - filename: %s", filename)
        lru_filename = self.lru.read(filename)
        if lru_filename is None:
            self.log.warn("read - filename not found")
            # raise ValueError(f"Filename {filename} not found")
            return None
        with open(lru_filename, "rb") as file:
            return file.read()
