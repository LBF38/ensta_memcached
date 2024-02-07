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
    def list(self, directory: str):
        return os.listdir(directory)

    def create(self, filename: str, data: bytes):
        with open(filename, "wb") as file:
            file.write(data)

    def delete(self, filename: str):
        os.remove(filename)

    def read(self, filename: str):
        with open(filename, "rb") as file:
            return file.read()


class Mem(Storage):
    def __init__(self, client: Client) -> None:
        self.client = client

    def create(self, key: str, value: bytes):
        self.client.set(key, value)

    def read(self, key: str) -> bytes:
        return self.client.get(key).decode("UTF-8")

    def delete(self, key: str):
        self.client.delete(key)


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
        with open(filename, "rb") as data:
            self.bucket.put_object(Key=filename, Body=data)

    def read(self, filename: str):
        self.log.debug("read - filename: %s", filename)
        return self.s3.Object("ensta", filename).get()["Body"].read().decode("UTF-8")

    def delete(self):
        self.log.warning("delete - Not implemented")
        pass
