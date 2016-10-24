from collections import defaultdict
from os import path
from glob import glob


def split_clauses(program):
    in_parenthese = False
    in_quote = False
    pos = 0
    program = program + " "
    for i, c in enumerate(program):
        if not in_quote and c == "(":
            in_parenthese = True
        elif in_parenthese and c == ")":
            in_parenthese = False
        elif not in_quote and c == '`':
            in_quote = True
        elif in_quote and c == '`':
            in_quote = False

        if c == "." and not program[i-1].isdigit() and not program[i+1].isdigit():
            yield program[pos:i]
            pos = i + 1
    yield program[pos:]


def find_files(fn):
    folder = path.dirname(path.abspath(__file__))
    return glob(path.join(folder, "**/{}".format(fn)), recursive=True)

