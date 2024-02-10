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
        self.__storage(cost).create(key, data)
        self.log.debug("create - done")

    def read(self, filename: str, cost: int) -> bytes:
        return self.__storage(cost).read(filename)

    def delete(self, key: str, cost: int) -> None:
        self.log.debug("delete - key: %s", key)
        try:
            self.__storage(cost).delete(key)
        except Exception as e:
            self.log.error(e)
        self.log.debug("delete - done")

    def __storage(self, cost: int) -> Storage:
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


# Node = namedtuple("Node", ["value", "prev", "next"])
class Node:
    def __init__(
        self, value: bytes, prev: Optional["Node"] = None, next: Optional["Node"] = None
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

    def create(self, key: str, value: bytes):
        # does it exist ?
        node = self.__lookup.get(key)
        if node is None:
            node = self.__createNode(value)
            self.__length += 1
            self.__prepend(node)
            self.__trimCache()

            self.__lookup[key] = node
            self.__reverseLookup[node] = key
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

    def __trimCache(self):
        if self.__length <= self.__capacity:
            return
        tail = self.__tail
        self.__detach(tail)
        del self.__lookup[self.__reverseLookup[tail]]
        del self.__reverseLookup[tail]
        self.__length -= 1

    def __createNode(self, value: bytes):
        return Node(value, None, None)


class Mem_LRU(Storage):
    def __init__(self, client: Client, capacity: int = 10) -> None:
        self.client = client
        self.lru = LRU(capacity)
        self.log = logging.getLogger("Mem LRU")
        self.log.debug("init - client %s", client.__class__)

    def create(self, key: str, value: bytes):
        self.log.debug("create - key: %s", key)
        # self.client.set(key, value)
        self.lru.create(key, value)

    def read(self, key: str) -> bytes | None:
        self.log.debug("read - key: %s", key)
        value = self.lru.read(key)
        # value = self.client.get(key)
        if value is None:
            self.log.warn("read - key not found")
            # raise ValueError(f"Key {key} not found")
            return None
        self.log.debug("read - value: %s", value[:10])
        return value

    def delete(self, key: str):
        self.log.debug("delete - key: %s", key)
        # self.client.delete(key)
        self.lru.delete(key)
        self.log.debug("delete - done")


def cache_2level():
    """2 level caching
    This type of storage uses an LRU cache for managing the keys of the files in each storage.
    Therefore, a first LRU cache is used in the Memcached storage, and a second LRU cache is used in the filesystem. These LRU caches are used to store the keys of the files that are stored in the Memcached storage and the filesystem, respectively.
    They enable us to manage the keys based on the frequency of access to the files.
    """
    pass


class Auto_tiering(Tiering):
    def __init__(self, filesystem: FileSystem, aws: AWSS3, memcached: Mem) -> None:
        super().__init__(filesystem, aws, memcached)
        self.log = logging.getLogger("Auto-tiering")
        self.__frequency: Dict[str, int] = {}

    def create(self, filename: str, data: bytes) -> None:
        self.log.debug("create - filename: %s", filename)
        self.__frequency[filename] = 0
        super().create(
            filename,
            data,
            self.__frequency[filename],
        )

    def read(self, filename: str) -> bytes:
        self.log.debug("read - filename: %s", filename)
        self.__frequency[filename] += 1
        self.log.debug("read - frequency: %s", self.__frequency[filename])
        return super().read(filename, self.__frequency[filename])

    def delete(self, filename: str) -> None:
        self.log.debug("delete - filename: %s", filename)
        self.log.debug("delete - frequency: %s", self.__frequency[filename])
        super().delete(filename, self.__frequency[filename])
        del self.__frequency[filename]
