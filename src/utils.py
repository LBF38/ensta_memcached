import io
import logging
import os
from abc import abstractmethod
from typing import Dict, Optional

import boto3
from dotenv import load_dotenv
from memcache import Client
from PIL import Image

load_dotenv()
# logging.basicConfig(level=logging.DEBUG)
if not (os.getenv("ak") and os.getenv("sk")):
    print("Please set up your AWS credentials in .env file")
    exit(1)


def show_image(data: bytes):
    image = Image.open(io.BytesIO(data))
    image.show()


class Storage:
    @abstractmethod
    def create(self, key: str, data: bytes) -> None:
        pass

    @abstractmethod
    def read(self, filename: str) -> bytes:
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        pass


class FileSystem(Storage):
    def __init__(self) -> None:
        self.log = logging.getLogger("FileSystem")

    def list(self, directory: str):
        self.log.debug("list - directory: %s", directory)
        return os.listdir(directory)

    def create(self, filename: str, data: bytes):
        self.log.debug("create - filename: %s", filename)
        with open(filename, "wb") as file:
            file.write(data)

    def delete(self, filename: str):
        self.log.debug("delete - filename: %s", filename)
        os.remove(filename)

    def read(self, filename: str):
        self.log.debug("read - filename: %s", filename)
        with open(filename, "rb") as file:
            return file.read()


class Mem(Storage):
    def __init__(self, client: Client) -> None:
        self.client = client
        self.log = logging.getLogger("Mem")
        self.log.debug("init - client %s", client.__class__)

    def create(self, key: str, value: bytes):
        self.log.debug("create - key: %s", key)
        self.client.set(key, value)
        print("create - done val:", type(value))
        print(value[:10])
        print("key: ", key)
        # self.log.debug("create - done val:" + type(val))

    def read(self, key: str) -> bytes | None:
        self.log.debug("read - key: %s", key)
        value = self.client.get(key)
        if value is None:
            self.log.warn("read - key not found")
            # raise ValueError(f"Key {key} not found")
            return None
        self.log.debug("read - value: %s", value[:10])
        return value

    def delete(self, key: str):
        self.log.debug("delete - key: %s", key)
        self.client.delete(key)
        self.log.debug("delete - done")


class AWSS3(Storage):
    def __init__(self) -> None:
        self.ak = os.getenv("ak")
        self.sk = os.getenv("sk")
        self.session = boto3.Session(
            aws_access_key_id=self.ak,
            aws_secret_access_key=self.sk,
        )
        self.s3 = self.session.resource("s3")
        self.bucket = self.s3.Bucket("ensta")
        self.log = logging.getLogger("AWSS3")

    def list(self):
        self.log.debug("list - start listing")
        objects = self.bucket.objects.all()
        return [obj.key for obj in objects]

    def create(self, filename: str, data: bytes):
        self.log.debug("create - filename: %s", filename)
        self.bucket.put_object(Key=filename, Body=data)

    def read(self, filename: str) -> bytes:
        self.log.debug("read - filename: %s", filename)
        obj = self.bucket.Object(filename)
        resource = obj.get()["Body"].read()
        self.log.debug("read - resource: %s", resource[:10])
        return resource
        # return self.s3.Object("ensta", filename).get()["Body"].read().decode("UTF-8")

    def delete(self, filename: str):
        self.log.debug("delete - filename: %s", filename)
        self.bucket.Object(filename).delete()
        self.log.debug("delete - done")


class Replica(Storage):
    def __init__(self, filesystem: FileSystem, aws: AWSS3) -> None:
        self.fs = filesystem
        self.aws = aws
        self.log = logging.getLogger("Replica")

    def create(self, key: str, data: bytes):
        self.log.debug("create - key: %s", key)
        self.fs.create(key, data)
        self.log.debug("file created in filesystem at key: %s", key)
        self.aws.create(key, data)
        self.log.debug("file created in aws at key: %s", key)

    def read(self, filename: str):
        self.log.debug("read - filename: %s", filename)
        try:
            self.log.debug("trying filesystem")
            return self.fs.read(filename)
        except FileNotFoundError:
            self.log.debug("file not found in filesystem, trying aws")
            content = self.aws.read(filename)
            self.log.debug("file found in aws, creating in filesystem")
            self.fs.create(filename, content)
            self.log.debug("file created in filesystem")
            return content

    def delete(self, key: str):
        try:
            self.fs.delete(key)
            self.aws.delete(key)
        except Exception as e:
            self.log.error(e)


class Tiering(Storage):
    def __init__(self, filesystem: FileSystem, aws: AWSS3, memcached: Mem) -> None:
        self.fs = filesystem
        self.aws = aws
        self.mem = memcached
        self.log = logging.getLogger("Tiering")

    def create(self, key: str, data: bytes, cost: int):
        self.log.debug("create - key: %s", key)
        self._storage(cost).create(key, data)
        self.log.debug("create - done")

    def read(self, filename: str, cost: int) -> bytes:
        return self._storage(cost).read(filename)

    def delete(self, key: str, cost: int) -> None:
        self.log.debug("delete - key: %s", key)
        try:
            self._storage(cost).delete(key)
        except Exception as e:
            self.log.error(e)
        self.log.debug("delete - done")

    def _storage(self, cost: int) -> Storage:
        self.log.debug("storage - cost: %s", cost)
        if cost < 100:
            self.log.debug("cost < 100: aws storage")
            return self.aws
        elif cost < 1000:
            self.log.debug("cost < 1000: filesystem storage")
            return self.fs
        else:
            self.log.debug("cost >= 1000: memcached storage")
            return self.mem


class Node:
    def __init__(
        self, value: str, prev: Optional["Node"] = None, next: Optional["Node"] = None
    ) -> None:
        self.value = value
        self.prev = prev
        self.next = next


class LRU:
    def __init__(self, capacity: int = 10) -> None:
        self.__head: Node | None = None
        self.__tail: Node | None = None
        self.__capacity = capacity
        self.__length = 0
        self.__lookup: Dict[str, Node] = {}
        self.__reverseLookup: Dict[Node, str] = {}

    def create(self, key: str, value: str) -> str | None:
        # does it exist ?
        node = self.__lookup.get(key)
        if node is None:
            node = self.__createNode(value)
            self.__length += 1
            self.__prepend(node)
            del_value = self.__trimCache()

            self.__lookup[key] = node
            self.__reverseLookup[node] = key
            return del_value
        else:
            self.__detach(node)
            self.__prepend(node)
            node.value = value

    def read(self, key: str):
        node = self.__lookup.get(key)
        if node is None:
            return

        self.__detach(node)
        self.__prepend(node)

        return node.value

    def delete(self, key: str):
        node = self.__lookup.get(key)
        if node is None:
            return

        self.__detach(node)
        self.__length -= 1
        del self.__lookup[key]
        del self.__reverseLookup[node]

    def __detach(self, node: Node):
        if node.prev:
            node.prev.next = node.next
        if node.next:
            node.next.prev = node.prev

        if self.__head == node:
            self.__head = self.__head.next
        if self.__tail == node:
            self.__tail = self.__tail.prev

        node.next = None
        node.prev = None

    def __prepend(self, node: Node):
        if not self.__head:
            self.__head = self.__tail = node
            return
        node.next = self.__head
        self.__head.prev = node
        self.__head = node

    def __trimCache(self) -> str | None:
        if self.__length <= self.__capacity:
            return
        tail = self.__tail
        self.__detach(tail)
        del self.__lookup[self.__reverseLookup[tail]]
        del self.__reverseLookup[tail]
        self.__length -= 1
        return tail.value

    def __createNode(self, value: bytes):
        return Node(value, None, None)


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


class TwoLevelCaching(Storage):
    """2 level caching

    This type of storage uses an LRU cache for managing the keys of the files in each storage.

    Therefore, a first LRU cache is used in the Memcached storage, and a second LRU cache is used in the filesystem.

    These LRU caches are used to store the keys of the files that are stored in the Memcached storage and the filesystem, respectively.

    They enable us to manage the keys based on the frequency of access to the files.
    """

    def __init__(
        self, mem_client: Client, fs_lru_capacity: int = 20, mem_lru_capacity: int = 15
    ) -> None:
        assert (
            fs_lru_capacity > mem_lru_capacity > 0
        ), "fs_lru_capacity must be greater than mem_lru_capacity and both should be greater than 0"
        self.log = logging.getLogger("Cache_2level")
        self.aws = AWSS3()
        self.fs_lru = FileSystem_LRU(fs_lru_capacity)
        self.mem_lru = Mem_LRU(mem_client, mem_lru_capacity)

    def create(self, key: str, value: bytes):
        self.log.debug("create - key: %s", key)
        self.aws.create(key, value)
        self.fs_lru.create(key, value)
        self.mem_lru.create(key, value)
        self.log.debug("create - done")

    def read(self, key: str) -> bytes | None:
        self.log.debug("read - key: %s", key)
        mem_value = self.mem_lru.read(key)
        if mem_value is None:
            fs_value = self.fs_lru.read(key)
            if fs_value is None:
                self.log.warn("read - key not found in LRU caches")
                aws_value = self.aws.read(key)
                self.log.debug("read from aws - value: %s", mem_value[:10])
                self.fs_lru.create(key, aws_value)
                self.mem_lru.create(key, aws_value)
                return aws_value
            self.log.debug("read from fs - value: %s", mem_value[:10])
            self.mem_lru.create(key, fs_value)
            return fs_value
        self.log.debug("read from mem - value: %s", mem_value[:10])
        self.log.debug("read - done")
        return mem_value

    def delete(self, key: str):
        self.log.debug("delete - key: %s", key)
        self.mem_lru.delete(key)
        self.fs_lru.delete(key)
        self.aws.delete(key)
        self.log.debug("delete - done")


class Auto_tiering(Tiering):
    def __init__(self, filesystem: FileSystem, aws: AWSS3, memcached: Mem) -> None:
        super().__init__(filesystem, aws, memcached)
        self.log = logging.getLogger("Auto-tiering")
        self.__frequency: Dict[str, int] = {}
        self.__current_storage: Storage

    def create(self, filename: str, data: bytes) -> None:
        self.log.debug("create - filename: %s", filename)
        self.__frequency[filename] = 0
        self.__current_storage = super()._storage(self.__frequency[filename])
        super().create(
            filename,
            data,
            self.__frequency[filename],
        )

    def read(self, filename: str) -> bytes:
        self.log.debug("read - filename: %s", filename)
        self.__frequency[filename] += 1
        # ^ This can be updated to a more complex algorithm for calculating the frequency of access based on the time of access.
        self.log.debug("read - frequency: %s", self.__frequency[filename])
        self.__auto_check(filename)
        return super().read(filename, self.__frequency[filename])

    def delete(self, filename: str) -> None:
        self.log.debug("delete - filename: %s", filename)
        self.log.debug("delete - frequency: %s", self.__frequency[filename])
        super().delete(filename, self.__frequency[filename])
        del self.__frequency[filename]

    def __auto_check(self, filename: str) -> None:
        self.log.debug("auto_check - filename: %s", filename)
        if self.__current_storage != super()._storage(self.__frequency[filename]):
            self.__move(filename)
        self.log.debug("auto_check - done")

    def __move(self, filename: str) -> None:
        self.log.debug("move - filename: %s", filename)
        content = self.__current_storage.read(filename)
        self.log.debug("move - content: %s", content[:10])
        super().create(filename, content, self.__frequency[filename])
        self.__current_storage.delete(filename)
        self.log.debug(
            "move - update current storage to %s",
            super()._storage(self.__frequency[filename]).__class__.__name__,
        )
        self.__current_storage = super()._storage(self.__frequency[filename])
        self.log.debug("move - done")
