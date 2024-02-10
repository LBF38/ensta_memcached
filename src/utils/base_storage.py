import logging
import os
from abc import abstractmethod

import boto3
from dotenv import load_dotenv
from memcache import Client

load_dotenv()
# logging.basicConfig(level=logging.DEBUG)
if not (os.getenv("ak") and os.getenv("sk")):
    print("Please set up your AWS credentials in .env file")
    exit(1)


class Storage:
    """Storage interface for different storage types

    This class is an interface for different storage types like FileSystem, Mem, AWSS3.

    It has three methods:
    - create: to create a file in the storage
    - read: to read a file from the storage
    - delete: to delete a file from the storage

    """

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
    """FileSystem class for file operations"""

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
    """Mem class for memcached operations"""

    def __init__(self, client: Client) -> None:
        self.client = client
        self.log = logging.getLogger("Mem")
        self.log.debug("init - client %s", client.__class__)

    def create(self, key: str, value: bytes):
        self.log.debug("create - key: %s", key)
        self.client.set(key, value)
        self.log.debug("create - done")

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
    """AWS S3 class for file operations using AWS S3 bucket"""

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
