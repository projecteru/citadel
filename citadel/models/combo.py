# coding: utf-8

import re
import types


_UNIT = re.compile(r'^(\d+)([kKmMgG][bB])$')
_UNIT_DICT = {
    'kb': 1024,
    'mb': 1024 * 1024,
    'gb': 1024 * 1024 * 1024,
}


def to_number(memory):
    """把字符串的内存转成数字.
    可以是纯数字, 纯数字的字符串, 也可以是带单位的字符串.
    如果出错会返回负数, 让部署的时候出错.
    因为0是不限制, 不能便宜了出错的容器..."""
    if isinstance(memory, (types.IntType, types.LongType)):
        return memory
    if isinstance(memory, basestring) and memory.isdigit():
        return int(memory)

    r = _UNIT.match(memory)
    if not r:
        return -1

    number = r.group(1)
    unit = r.group(2).lower()
    return int(number) * _UNIT_DICT.get(unit, -1)


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
