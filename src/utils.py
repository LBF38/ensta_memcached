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


class FileSystem:
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


class Mem:
    def __init__(self, client: Client) -> None:
        self.client = client

    def create(self, key, value):
        self.client.set(key, value)

    def read(self, key):
        return self.client.get(key)

    def delete(self, key):
        self.client.delete(key)


class AWSS3:
    def __init__(self) -> None:
        self.ak = os.getenv(ak)
        self.sk = os.getenv(sk)
        self.session = boto3.Session(
            aws_access_key_id=self.ak,
            aws_secret_access_key=self.sk,
        )
        self.s3 = self.session.resource("s3")
        self.bucket = self.s3.Bucket("ensta")

    def list(self):
        logging.info("AWSS3:list - start listing")
        objects = self.bucket.objects.all()
        return [obj.key for obj in objects]

    def create(self, filename: str, data: bytes):
        with open(filename, "rb") as data:
            self.bucket.put_object(Key=filename, Body=data)

    def read(self, filename: str):
        return self.s3.Object("ensta", filename).get()["Body"].read().decode("UTF-8")

    def delete(self):
        logging.warning("AWSS3:delete - Not implemented")
        pass
