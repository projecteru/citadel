# coding: utf-8
from citadel.libs.utils import to_number


class Combo(object):

    def __init__(self, label, cpu, memory):
        self.label = label
        self.cpu = cpu
        self.memory_str = memory
        self.memory = to_number(memory)

    @classmethod
    def get(cls, label):
        for c in ALL_COMBOS:
            if c.label == label:
                return c
        return None


ALL_COMBOS = [
    Combo(u'穷哭', 0.5, '512MB'),
    Combo(u'凄惨', 1, '1GB'),
    Combo(u'一般', 2, '4GB'),
    Combo(u'不错', 4, '8GB'),
    Combo(u'厉害', 8, '16GB'),
]
