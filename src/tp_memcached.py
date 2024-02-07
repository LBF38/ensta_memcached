from random import randint, seed
from time import sleep
import time

# from pymemcache.client.base import Client
from memcache import Client

client = Client(["localhost"], debug=0)  # for memcache
# client = Client("localhost")  # for pymemcache
# client.set("some_key", "some_value")
# result = client.get("some_key")
# print(result)


def f(x):
    sleep(1)
    return x * x


def fc(x):
    cached_value = client.get(f"{x}")
    if cached_value is None:
        value = f(x)
        client.set(f"{x}", value)
        return value
    return cached_value


if __name__ == "__main__":
    n = 50
    r_max = 50
    s = 45
    seed(s)
    start = time.time()
    for i in range(n):
        print("f: ", f(randint(0, r_max)))
    print("f time: ", time.time() - start)
    start = time.time()
    seed(s)
    for i in range(n):
        print("fc: ", fc(randint(0, r_max)))
    print("fc time: ", time.time() - start)
