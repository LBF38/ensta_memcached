import logging
import os

from memcache import Client
from utils import AWSS3, FileSystem, Mem, show_image

logging.basicConfig(level=logging.DEBUG)

FS = FileSystem()
client = Client(["localhost"], debug=0)
MEM = Mem(client)
AWS = AWSS3()
log = logging.getLogger("main")


def file_system(filename: str | None = None):
    log = logging.getLogger("file_system")
    log.info("File System")
    if not filename:
        filename = "assets/image.jpg"
    log.info("filename: %s", filename)
    if not os.path.exists("R"):
        os.mkdir("R")
    log.info("list directory R: %s", os.listdir("R"))
    T = FS.read(filename)
    log.info("read file: %s", T[:10])
    show_image(T)
    FS.create("F", T)
    log.info("file F created")
    T2 = FS.read("F")
    log.info("read file F: %s", T2[:10])
    show_image(T2)


def memcached(filename: str | None = None):
    log = logging.getLogger("memcached")
    log.info("Memcached")
    if not filename:
        filename = "assets/image.jpg"
    log.info("filename: %s", filename)
    T = FS.read(filename)
    log.info("read file: %s", T[:10])
    show_image(T)
    MEM.create("K", T)
    log.info("key K created")
    try:
        T2 = MEM.read("K")
    except ValueError as e:
        log.error(e)
        return
    log.info("read key K: %s", T2[:10])
    show_image(T2)


def aws_program(filename: str | None = None):
    log.info("AWS program")
    log.info("list: %s", AWS.list())
    if not filename:
        filename = AWS.list()[0]
    log.info("filename: %s", filename)
    T = AWS.read(filename)
    log.info("read file: %s", T[:10])
    show_image(T)
    AWS.create("new_file_s3.jpg", T)
    log.info("file new_file_s3 created")
    T2 = AWS.read("new_file_s3.jpg")
    log.info("read file new_file_s3: %s", T2[:10])
    show_image(T2)


if __name__ == "__main__":
    log.info("Start the program")
    # file_system()
    # memcached()
    # aws_program()
    # print(AWS.list())
    # print(AWS.delete("new_file_s3.jpg"))
