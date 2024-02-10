import logging
import os

from memcache import Client
from utils import AWSS3, FileSystem, Mem, Replica, show_image

logging.basicConfig(level=logging.INFO)

FS = FileSystem()
client = Client(["localhost"], debug=0)
MEM = Mem(client)
AWS = AWSS3()
log = logging.getLogger("main")


def file_system(filename: str | None = None, img: bool = False):
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
    if img:
        show_image(T)
    FS.create("F", T)
    log.info("file F created")
    T2 = FS.read("F")
    log.info("read file F: %s", T2[:10])
    if img:
        show_image(T2)


def memcached(filename: str | None = None, img: bool = False):
    log = logging.getLogger("memcached")
    log.info("Memcached")
    if not filename:
        filename = "assets/image.jpg"
    log.info("filename: %s", filename)
    T = FS.read(filename)
    log.info("read file: %s", T[:10])
    if img:
        show_image(T)
    MEM.create("K", T)
    log.info("key K created")
    T2 = MEM.read("K")
    if not T2:
        log.error("key K not found")
        return
    log.info("read key K: %s", T2[:10])
    if img:
        show_image(T2)


def aws_program(filename: str | None = None, img: bool = False):
    log.info("AWS program")
    log.info("list: %s", AWS.list())
    if not filename:
        filename = AWS.list()[0]
    log.info("filename: %s", filename)
    T = AWS.read(filename)
    log.info("read file: %s", T[:10])
    if img:
        show_image(T)
    AWS.create("new_file_s3.jpg", T)
    log.info("file new_file_s3 created")
    T2 = AWS.read("new_file_s3.jpg")
    log.info("read file new_file_s3: %s", T2[:10])
    if img:
        show_image(T2)


if __name__ == "__main__":
    log.info("Start the program")
    # file_system()
    # memcached("assets/image_small.jpg")
    # aws_program()
    # print(AWS.list())
    # print(AWS.delete("image_small_auto_tiering.jpg"))
    # print(MEM.create("K", b"\xff\xd8\xff\xe0\x00\x10JFIF"))
    # print(MEM.read("K"))

    #####? Replica manual testing
    # replica = Replica(FS, AWS)
    # content = replica.read("ouvrez_moi.png")
    # if content:
    #     log.info("read file ouvrez_moi.png: %s", content[:10])
    #     show_image(content)
    # replica.create("ouvrez_moi_copy.png", content)
    # log.info("file ouvrez_moi_copy.png created")
    # log.info(AWS.list())
    # replica.delete("ouvrez_moi_copy.png")
    # log.info("file ouvrez_moi_copy.png deleted")
    # log.info(AWS.list())
