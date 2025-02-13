"""
unified_store.py – Contains the UnifiedStore class, which combines point queries, sorted sets,
and LRU cache functionality.
"""

from .lru_cache import LRUNode, DoublyLinkedList
from .sorted_set import SortedSet

class UnifiedStore:
    """Unified data structure combining a hash table, sorted sets, and LRU cache."""
    def __init__(self, capacity):
        self.capacity = capacity
        self.hash_table = {}    # For point queries; keys map to LRUNode objects.
        self.sorted_sets = {}   # For sorted sets; keys map to SortedSet objects.
        self.lru_list = DoublyLinkedList()

    def set(self, key, value):
        if key in self.hash_table: 
            node = self.hash_table[key]
            node.value = value
            self.lru_list.move_to_front(node)
        else:
            if len(self.hash_table) >= self.capacity:
                lru_node = self.lru_list.pop_tail()
                if lru_node:
                    del self.hash_table[lru_node.key]
            new_node = LRUNode(key, value)
            self.hash_table[key] = new_node
            self.lru_list.add_to_front(new_node)

    def get(self, key):
        if key in self.hash_table:
            node = self.hash_table[key]
            self.lru_list.move_to_front(node)
            return node.value
        return None

    def delete(self, key):
        if key in self.hash_table:
            node = self.hash_table[key]
            self.lru_list.remove(node)
            del self.hash_table[key]

    def process_zadd(self, key, score, member):
        if key not in self.sorted_sets:
            self.sorted_sets[key] = SortedSet(key)
            self.lru_list.add_to_front(self.sorted_sets[key])
        else:
            self.lru_list.move_to_front(self.sorted_sets[key])
        return self.sorted_sets[key].zadd(score, member)

    def process_zrange(self, key, start, end):
        if key in self.sorted_sets:
            self.lru_list.move_to_front(self.sorted_sets[key])
            return self.sorted_sets[key].zrange(start, end)
        return []

    def process_zrank(self, key, member):
        if key in self.sorted_sets:
            self.lru_list.move_to_front(self.sorted_sets[key])
            return self.sorted_sets[key].zrank(member)
        return None

    def process_zrem(self, key, member):
        if key in self.sorted_sets:
            result = self.sorted_sets[key].zrem(member)
            self.lru_list.remove(self.sorted_sets[key])
            return result
        return None

# Create global instances (you can import these in server.py)
store = UnifiedStore(capacity=1000)
