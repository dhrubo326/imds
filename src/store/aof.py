"""
aof.py – Append Only File persistence logic.
"""

class AOF:
    def __init__(self, file_name):
        self.file_name = file_name

    def append(self, command):
        with open(self.file_name, 'a') as f:
            f.write(command + '\n')
