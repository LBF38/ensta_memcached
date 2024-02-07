import os
from memcache import Client
from PIL import Image
import io


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
    def list(self):
        pass

    def create(self):
        pass

    def read(self):
        pass

    def delete(self):
        pass
