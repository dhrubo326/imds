"""
lru_cache.py – Contains the base classes for LRU cache functionality.
"""

class LRUNode:
    """Base class for objects that participate in the LRU cache."""
    def __init__(self, key, value=None):
        self.key = key
        self.value = value  # For point query nodes, this is the stored value.
        self.prev = None
        self.next = None

class Node:
    """A simple node for a doubly linked list (used in the LRU cache)."""
    def __init__(self, key, value):
        self.key = key
        self.value = value
        self.prev = None
        self.next = None

class DoublyLinkedList:
    """Doubly linked list implementation for the LRU cache."""
    def __init__(self):
        self.head = Node(None, None)  # Dummy head
        self.tail = Node(None, None)  # Dummy tail
        self.head.next = self.tail
        self.tail.prev = self.head

    def move_to_front(self, node):
        self.remove(node)
        self.add_to_front(node)

    def add_to_front(self, node):
        node.next = self.head.next
        node.prev = self.head
        self.head.next.prev = node
        self.head.next = node

    def remove(self, node):
        node.prev.next = node.next
        node.next.prev = node.prev

    def pop_tail(self):
        if self.tail.prev == self.head:
            return None
        node = self.tail.prev
        self.remove(node)
        return node
