import pytest
import uuid
from .pyamzi import Engine, Struct, StringOutput

@pytest.fixture(scope='function')
def eng(request):
    from os import path
    xpl_fn = path.join(path.dirname(__file__), "xpl", "dummy.xpl")
    name = str(uuid.uuid1())
    eng = Engine(name)
    eng.load(xpl_fn)

    def teardown():
        eng.close()

    request.addfinalizer(teardown)

    return eng

def test_terms(eng):
    for obj in [123, 123.5, "abc", "测试"]:
        term = eng.make_term("{}".format(obj))
        assert term.to_object() == obj

    term_list = eng.make_term("[1, 2, 3, [abc, def], xyz]")
    assert term_list.to_object() == [1, 2, 3, ["abc", "def"], "xyz"]

    term_list = eng.make_term("[]")
    assert term_list.to_object() == []

    term_list = eng.make_term("hello(world, 123)")
    assert term_list.to_object() == Struct("hello", ("world", 123))


def test_find_all(eng):
    eng.assert_program("""
    test(x, y).
    test(x, z).
    test(t, x).
    test2(X, Y):-test(X, Y).
    test2(X, Y):-test(Y, X).
    """)
    res = eng.find_all("test2(X, Y)")
    assert len(res) == 6
    res = eng.find_all("test2(x, Y)")
    assert len(res) == 3
    res = eng.find_all("test2(t, X)")
    assert len(res) == 1
    res = eng.find_all("test2(a, b)")
    assert len(res) == 0


def test_pyfunc(eng):
    from math import sin, cos
    eng.assert_program("""
    run_pybind(A, B, C):-
        pybind(sin, 1, A),
        pybind(cos, 1, B),
        pybind(add, [A, B], C).
    """)
    res, term = eng.exec_str("run_pybind(A, B, C)")
    assert res
    obj = term.to_object()
    A, B, C = obj.arguments
    s = sin(1)
    c = cos(1)
    assert abs(A - s) < 1e-6
    assert abs(B - c) < 1e-6
    assert abs(C - s - c) < 1e-6


def test_pyiter(eng):
    eng.output = StringOutput
    eng.assert_program("""
    iter(X):-
        pybind(next, X, Y),
        write(Y), nl,
        iter(X).
    iter(_).

    test_iter(D, E):-
        pygetobj(range, [5, 10], D),
        pygetobj(iter, D, E),
        iter(E),
        pydelobj(D).
    """)
    res, term = eng.call_str("test_iter(X, Y)")
    assert res
    output = eng.output.get_value()
    assert output == "\n".join(map(str, range(5, 10))) + "\n"
    obj = term.to_object()
    assert term.arguments[0] is None #X is deleted
    assert type(term.arguments[1]) == type(iter(range(1)))
    assert len(eng.cached_object) == 1


def test_object_to_term(eng):
    term = eng.object_to_term("hello")
    assert term.is_atom
    assert term.to_object() == "hello"

    term = eng.object_to_term("hello world")
    assert term.is_str
    assert term.to_object() == "hello world"

    term = eng.object_to_term(123)
    assert term.is_int
    assert term.to_object() == 123

    term = eng.object_to_term(123.5)
    assert term.is_float
    assert term.to_object() == 123.5

    alist = [1, "atom", 3, ["x", "y"]]
    term = eng.object_to_term(alist)
    assert term.is_list
    assert term.to_object() == alist
    return

    #TODO: following code causes error sometimes
    astruct = Struct("computer", (1, 2))
    term = eng.object_to_term(astruct)
    assert term.is_struct
    assert term.to_object() == astruct

    astruct = Struct("computer", (1, 2, ["x", "y"]))
    term = eng.object_to_term(astruct)
    assert term.is_struct
    assert term.to_object() == astruct


def test_assert_program(eng):
    eng.output = StringOutput
    test_code = """
    test(a, b).
    test(a, c).
    go:-
        test(a, X),
        write(X),
        write(`1.0 (2.0)`),
        write(`,`),
        write(finished).
    """

    eng.assert_program(test_code)
    res, term = eng.call_str('go')
    assert res
    output = eng.output.get_value()
    assert output == "b1.0 (2.0),finished"


def test_builder():
    from .builder import cmp_path, lnk_path
    assert cmp_path.endswith(".exe")
    assert lnk_path.endswith(".exe")


def test_query(eng):
    test_code = """
    parent(a, b).
    parent(a, c).
    """
    eng.assert_program(test_code)
    assert eng.query_one("parent(X, Y)") == {"X":"a", "Y":"b"}
    assert eng.query_one("parent(b, X)") is None
    assert list(eng.query_all("parent(X, Y)")) == [{"X":"a", "Y":"b"}, {"X":"a", "Y":"c"}]
    assert list(eng.query_all("parent(b, X)")) == []