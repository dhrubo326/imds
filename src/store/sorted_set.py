"""
sorted_set.py – Contains SortedSet, SkipList, and SkipListNode implementations.
"""

import random

class SkipListNode:
    def __init__(self, score, member, level):
        self.score = score
        self.member = member
        # Forward pointers for each level.
        self.forward = [None] * (level + 1)

class SkipList:
    def __init__(self, max_level=16, p=0.5):
        self.max_level = max_level
        self.p = p
        self.level = 0  # Current highest level.
        self.header = SkipListNode(-float('inf'), None, self.max_level)

    def random_level(self):
        lvl = 0
        while random.random() < self.p and lvl < self.max_level:
            lvl += 1
        return lvl

    def insert(self, score, member):
        update = [None] * (self.max_level + 1)
        current = self.header
        for i in range(self.level, -1, -1):
            while current.forward[i] is not None and (
                  current.forward[i].score < score or
                 (current.forward[i].score == score and current.forward[i].member < member)):
                current = current.forward[i]
            update[i] = current
        lvl = self.random_level()
        if lvl > self.level:
            for i in range(self.level + 1, lvl + 1):
                update[i] = self.header
            self.level = lvl
        new_node = SkipListNode(score, member, lvl)
        for i in range(lvl + 1):
            new_node.forward[i] = update[i].forward[i]
            update[i].forward[i] = new_node

    def remove(self, score, member):
        update = [None] * (self.max_level + 1)
        current = self.header
        for i in range(self.level, -1, -1):
            while current.forward[i] is not None and (
                  current.forward[i].score < score or
                 (current.forward[i].score == score and current.forward[i].member < member)):
                current = current.forward[i]
            update[i] = current
        current = current.forward[0]
        if current is not None and current.score == score and current.member == member:
            for i in range(self.level + 1):
                if update[i].forward[i] != current:
                    break
                update[i].forward[i] = current.forward[i]
            while self.level > 0 and self.header.forward[self.level] is None:
                self.level -= 1
            return True
        return False

    def range_query(self, start_score, end_score):
        result = []
        current = self.header.forward[0]
        while current is not None and current.score < start_score:
            current = current.forward[0]
        while current is not None and current.score <= end_score:
            result.append((current.score, current.member))
            current = current.forward[0]
        return result

    def get_rank(self, score, member):
        # Current implementation: linear scan on level 0.
        rank = 0
        current = self.header.forward[0]
        while current is not None:
            if current.score == score and current.member == member:
                return rank
            rank += 1
            current = current.forward[0]
        return None

class SortedSet(LRUNode):
    """
    SortedSet implements sorted set operations using a skip list for ordering and a dictionary for fast lookups.
    Inherits from LRUNode (from lru_cache) to allow unified LRU management.
    """
    def __init__(self, key):
        # key identifies the sorted set.
        super().__init__(key)
        self.key = key
        self.skiplist = SkipList()
        self.members = {}  # Maps member -> score.

    def zadd(self, score, member):
        if member in self.members:
            old_score = self.members[member]
            self.skiplist.remove(old_score, member)
        self.skiplist.insert(score, member)
        self.members[member] = score
        return "OK"

    def zrange(self, start_score, end_score):
        return self.skiplist.range_query(start_score, end_score)

    def zrank(self, member):
        if member not in self.members:
            return None
        score = self.members[member]
        return self.skiplist.get_rank(score, member)

    def zrem(self, member):
        if member not in self.members:
            return None
        score = self.members[member]
        result = self.skiplist.remove(score, member)
        del self.members[member]
        return result
