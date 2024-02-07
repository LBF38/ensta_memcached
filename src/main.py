import logging
import os

from memcache import Client
from utils import AWSS3, FileSystem, Mem, show_image

logging.basicConfig(level=logging.INFO)

FS = FileSystem()
MEM = Mem(Client(["localhost"], debug=0))
AWS = AWSS3()


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
    T2 = MEM.read("K")
    log.info("read key K: %s", T2[:10])
    show_image(T2)


if __name__ == "__main__":
    logging.info("Start the program")
    file_system()
    memcached()
    # print(AWS.list())
