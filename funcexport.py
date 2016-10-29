from math import *
from operator import *
from random import *
from glob import glob

range = range
iter = iter
next = next


def import_module(module_path, name=None):
    import importlib
    try:
        if name is None:
            name = module_path.split(".")[-1]
        module = importlib.import_module(module_path)
        globals()[name] = module
        return True
    except Exception:
        return False


def from_import(module_path, *names):
    import importlib
    try:
        module = importlib.import_module(module_path)
        for name in names:
            globals()[name] = getattr(module, name)
        return True
    except Exception:
        return False