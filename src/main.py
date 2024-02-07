import os

from utils import FileSystem, Mem, show_image
from memcache import Client

FS = FileSystem()
MEM = Mem(Client(["localhost"], debug=0))


def file_system():
    print("File System")
    os.mkdir("R")
    print(os.listdir("R"))
    T = FS.read("I")
    show_image(T)
    FS.create("F", T)
    T2 = FS.read("F")
    show_image(T2)


def memcached():
    print("Memcached")
    T = MEM.read("I")
    show_image(T)
    MEM.create("K", T)
    T2 = MEM.read("K")
    show_image(T2)


if __name__ == "__main__":
    print("Start the program")
    file_system()
