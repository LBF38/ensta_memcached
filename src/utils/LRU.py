from typing import Dict, Optional


class Node:
    """Node class for doubly linked list

    Args:
        value (str): value of the node
        prev (Optional["Node"], optional): previous node. Defaults to None.
        next (Optional["Node"], optional): next node. Defaults to None.
    """

    def __init__(
        self, value: str, prev: Optional["Node"] = None, next: Optional["Node"] = None
    ) -> None:
        self.value = value
        self.prev = prev
        self.next = next


class LRU:
    """Least Recently Used Cache

    This class represents a Least Recently Used (LRU) cache implementation.
    It provides methods for creating, reading, and deleting key-value pairs.
    The cache has a specified capacity, and when the capacity is exceeded,
    the least recently used item is evicted from the cache.
    """

    def __init__(self, capacity: int = 10) -> None:
        self.__head: Node | None = None
        self.__tail: Node | None = None
        self.__capacity = capacity
        self.__length = 0
        self.__lookup: Dict[str, Node] = {}
        self.__reverseLookup: Dict[Node, str] = {}

    def create(self, key: str, value: str) -> str | None:
        # does it exist ?
        node = self.__lookup.get(key)
        if node is None:
            node = self.__createNode(value)
            self.__length += 1
            self.__prepend(node)
            del_value = self.__trimCache()

            self.__lookup[key] = node
            self.__reverseLookup[node] = key
            return del_value
        else:
            self.__detach(node)
            self.__prepend(node)
            node.value = value

    def read(self, key: str):
        node = self.__lookup.get(key)
        if node is None:
            return

        self.__detach(node)
        self.__prepend(node)

        return node.value

    def delete(self, key: str):
        node = self.__lookup.get(key)
        if node is None:
            return

        self.__detach(node)
        self.__length -= 1
        del self.__lookup[key]
        del self.__reverseLookup[node]

    def __detach(self, node: Node):
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

    def __prepend(self, node: Node):
        if not self.__head:
            self.__head = self.__tail = node
            return
        node.next = self.__head
        self.__head.prev = node
        self.__head = node

    def __trimCache(self) -> str | None:
        if self.__length <= self.__capacity:
            return
        tail = self.__tail
        self.__detach(tail)
        del self.__lookup[self.__reverseLookup[tail]]
        del self.__reverseLookup[tail]
        self.__length -= 1
        return tail.value

    def __createNode(self, value: bytes):
        return Node(value, None, None)
