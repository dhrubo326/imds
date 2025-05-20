"""
sorted_set.py – Contains SortedSet, SkipList, and SkipListNode implementations.
This version augments the skip list with span information so that range_query() and get_rank() 
run in O(log n) time on average.
"""

from .lru_cache import LRUNode
import random

class SkipListNode:
    def __init__(self, score, member, level):
        self.score = score
        self.member = member
        self.forward = [None] * (level + 1)
        # Span for each level: number of nodes skipped by the forward pointer
        self.span = [0] * (level + 1)

class SkipList:
    def __init__(self, max_level=32, p=0.25):
        self.max_level = max_level
        self.p = p
        self.level = 0          # Current highest level of the list
        self.length = 0         # Total number of elements
        # Create a header node with negative infinity score.
        self.header = SkipListNode(-float('inf'), None, self.max_level)
        for i in range(self.max_level + 1):
            self.header.span[i] = 0

    def random_level(self):
        lvl = 0
        while random.random() < self.p and lvl < self.max_level:
            lvl += 1
        return lvl

    def insert(self, score, member):
        # print(f"Type of score: {type(score)}")
        update = [None] * (self.max_level + 1)
        rank = [0] * (self.max_level + 1)
        current = self.header
        # Traverse from the highest level down to level 0.
        for i in range(self.level, -1, -1):
            # For the top level, rank[i] is 0.
            rank[i] = 0 if i == self.level else rank[i+1]
            while (current.forward[i] is not None and 
                   (current.forward[i].score < score or 
                    (current.forward[i].score == score and current.forward[i].member < member))):
                rank[i] += current.span[i]
                current = current.forward[i]
            update[i] = current

        lvl = self.random_level()
        if lvl > self.level:
            for i in range(self.level + 1, lvl + 1):
                update[i] = self.header
                # When no element exists at this level, span is the entire list length.
                update[i].span[i] = self.length + 1
                rank[i] = 0
            self.level = lvl

        new_node = SkipListNode(score, member, lvl)
        # At level 0, the new node should be inserted after update[0] 
        # and span is set appropriately.
        for i in range(lvl + 1):
            new_node.forward[i] = update[i].forward[i]
            update[i].forward[i] = new_node

            # The new node spans the gap that remains after (rank[0] - rank[i]) nodes.
            new_node.span[i] = update[i].span[i] - (rank[0] - rank[i])
            # Now update the span of update[i] to be exactly the gap to new_node.
            update[i].span[i] = (rank[0] - rank[i]) + 1

        # For levels above new_node.level, increment the span.
        for i in range(lvl + 1, self.level + 1):
            update[i].span[i] += 1

        self.length += 1

    def remove(self, score, member):
        update = [None] * (self.max_level + 1)
        current = self.header
        for i in range(self.level, -1, -1):
            while (current.forward[i] is not None and 
                   (current.forward[i].score < score or 
                    (current.forward[i].score == score and current.forward[i].member < member))):
                current = current.forward[i]
            update[i] = current

        current = current.forward[0]
        if current is None or current.score != score or current.member != member:
            return False

        for i in range(self.level + 1):
            if update[i].forward[i] != current:
                update[i].span[i] -= 1
            else:
                update[i].span[i] += current.span[i] - 1
                update[i].forward[i] = current.forward[i]

        while self.level > 0 and self.header.forward[self.level] is None:
            self.level -= 1

        self.length -= 1
        return True

    def range_query(self, start_score, end_score):
        results = []
        current = self.header.forward[0]
        # Skip nodes with scores less than start_score.
        while current is not None and current.score < start_score:
            current = current.forward[0]
        # Collect nodes until score exceeds end_score.
        while current is not None and current.score <= end_score:
            results.append((current.score, current.member))
            current = current.forward[0]
        return results

    def get_rank(self, score, member):
        rank = 0
        current = self.header
        for i in range(self.level, -1, -1):
            while (current.forward[i] is not None and 
                   (current.forward[i].score < score or 
                    (current.forward[i].score == score and current.forward[i].member <= member))):
                rank += current.span[i]
                current = current.forward[i]
        if current and current.score == score and current.member == member:
            return rank - 1  # Rank is 0-indexed.
        return None

    def print_level0(self):
        """Print all nodes in level 0 in the format 'score: member'."""
        current = self.header.forward[0]
        print("now skip list: ")
        while current is not None:
            print(f"{current.score}: {current.member}")
            current = current.forward[0]

class SortedSet(LRUNode):
    """
    SortedSet implements sorted set operations using a skip list for ordering and a dictionary for fast lookups.
    Inherits from LRUNode so that it can participate in the unified LRU cache.
    """
    def __init__(self, key):
        super().__init__(key)
        self.skiplist = SkipList()
        self.members = {}  # maps member -> score

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
