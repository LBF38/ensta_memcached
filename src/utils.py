from abc import abstractmethod
import logging
import os
from memcache import Client
from PIL import Image
import io
from dotenv import load_dotenv
import boto3

load_dotenv()
# logging.basicConfig(level=logging.DEBUG)
ak = "ak"
sk = "sk"
if not (os.getenv(ak) and os.getenv(sk)):
    print("Please set up your AWS credentials in .env file")
    exit(1)


def show_image(data: bytes):
    image = Image.open(io.BytesIO(data))
    image.show()


class Storage:
    @abstractmethod
    def create(self, key: str, data: bytes) -> bytes:
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

    def read(self, key: str) -> bytes:
        self.log.debug("read - key: %s", key)
        value = self.client.get(key)
        if value is None:
            self.log.warn("read - key not found")
            raise ValueError(f"Key {key} not found")
        self.log.debug("read - value: %s", value[:10])
        return value

    def delete(self, key: str):
        self.log.debug("delete - key: %s", key)
        self.client.delete(key)
        self.log.debug("delete - done")


class AWSS3(Storage):
    def __init__(self) -> None:
        self.ak = os.getenv(ak)
        self.sk = os.getenv(sk)
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
            self.fs.read(filename)
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
        self.__storage(cost).read(filename)

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


class LRU:
    def __init__(self, capacity: int = 10) -> None:
        self.__head = self.__tail = None
        self.__capacity = capacity
        self.__length = 0
        self.__lookup: dict = {}
        self.__reverseLookup: dict = {}

    def create(self, key, value):
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

    def read(self, key):
        node = self.__lookup.get(key)
        if node is None:
            return

        self.__detach(node)
        self.__prepend(node)

        return node.value

    def delete(self, key):
        node = self.__lookup.get(key)
        if node is None:
            return

        self.__detach(node)
        self.__length -= 1
        del self.__lookup[key]
        del self.__reverseLookup[node]

    def __detach(self, node):
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

    def __prepend(self, node):
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

    def __createNode(self, value):
        return {value}


def cache_2level():
    pass


class Auto_tiering:
    pass
