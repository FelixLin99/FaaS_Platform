# -*- coding:utf-8 -*-
# @Time : 2023/5/16 1:50
# @Author: ShuhuiLin
# @File : serialize.py
import dill
import codecs

def serialize(obj) -> str:
    return codecs.encode(dill.dumps(obj), "base64").decode()


def deserialize(obj: str):
    return dill.loads(codecs.decode(obj.encode(), "base64"))
