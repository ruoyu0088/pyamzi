import os
import re
from collections import namedtuple
from io import StringIO
from ._amzi import ffi
from . import funcexport
from .utils import split_clauses, find_files


lib = ffi.dlopen(find_files("amzi.dll")[0])


RC_FUNCS = {
    "lsInitW",
    "lsLoadW",
    "lsGetArg",
    "lsGetFAW",
    "lsTermToStrW",
    "lsStrToTermW",
    "lsGetTerm",
    "lsGetHead",
    "lsClearCall",
    "lsClose",
    "lsSetStream",
    "lsSetOutputW",
    "lsAssertzStrW",
    "lsAssertaStrW",
    "lsInitPredsW",
    "lsAddPredW",
    "lsGetParm",
    "lsMakeAtomW",
    "lsMakeStrW",
    "lsMakeInt",
    "lsMakeFloat",
    "lsMakeList",
    "lsPushList",
    "lsMakeFAW",
    "lsSetInput",
}


def convert_atom(buf):
    s = ffi.string(buf)
    if s == "[]":
        return []
    else:
        return s


class AmziError(Exception):
    pass


class Struct(namedtuple("Struct", "functor arguments")):
    def __str__(self):
        return "{}({})".format(self.functor, ", ".join(map(str, self.arguments)))

class StreamInput:
    def __init__(self, eng):
        self.getc = ffi.callback("int(void *)")(self._getc)
        self.ungetc = ffi.callback("int(void *, int)")(self._ungetc)
        eng.ls_set_input(self.getc, self.ungetc)

    def _getc(self, void):
        return 0

    def _ungetc(self, void, c):
        return 0


class StringInput(StreamInput):
    def __init__(self, eng):
        self.buffer = StringIO("")
        super().__init__(eng)

    def _getc(self, void):
        s = self.buffer.read(1)
        if s:
            return ord(s)
        else:
            return 0

    def _ungetc(self, void, c):
        self.buffer.seek(-2, os.SEEK_SET)
        return ord(self.buffer.read(1))

    def set_text(self, text):
        self.buffer = StringIO(text)


class StreamOutput:
    def __init__(self, eng):
        self.putc = ffi.callback("void(void *, int)")(self._putc)
        self.puts = ffi.callback("void(void *, wchar_t *)")(self._puts)
        eng.ls_set_output(self.putc, self.puts)
        self.mute = False

    def _putc(self, void, c):
        if not self.mute:
            print(chr(c), end='')

    def _puts(self, void, s):
        if not self.mute:
            print(ffi.string(s), end='')


class StringOutput(StreamOutput):
    def __init__(self, eng):
        self.buffer = StringIO()
        super().__init__(eng)

    def _putc(self, void, c):
        if not self.mute:
            self.buffer.write(chr(c))

    def _puts(self, void, s):
        if not self.mute:
            self.buffer.write(ffi.string(s))

    def get_value(self):
        return self.buffer.getvalue()

    def read(self):
        return self.buffer.read()


class Term:
    def __init__(self, eng, term_ptr):
        self.eng = eng
        self._term_id = term_ptr
        self._functor = None
        self._arity = None
        self._type_id = None

    @property
    def type_id(self):
        if self._type_id is None:
            self._type_id = self.eng.ls_get_term_type(self.ID)
        return self._type_id

    @property
    def ID(self):
        return self._term_id[0]

    @property
    def address(self):
        return self._term_id

    @property
    def functor(self):
        if self._functor is None:
            self._get_functor()
        return self._functor

    @property
    def arguments(self):
        args = []
        for i in range(self.arity):
            term = self.get_arg_term(i)
            if term is not None:
                term = term.to_object()
            args.append(term)
        return tuple(args)

    @property
    def arity(self):
        if self._arity is None:
            self._get_functor()
        return self._arity

    @property
    def head(self):
        term_ptr = ffi.new("TERMptr")
        self.eng.ls_get_head(self.ID, lib.cTERM, term_ptr)
        if term_ptr[0] == ffi.NULL:
            return None
        return self.eng._make_term_object(term_ptr)

    @property
    def tail(self):
        term_ptr = ffi.new("TERMptr")
        term_ptr[0] = self.eng.ls_get_tail(self.ID)
        if term_ptr[0] == ffi.NULL:
            return None
        return self.eng._make_term_object(term_ptr)

    @property
    def is_list(self):
        return self.type_id == lib.pLIST

    @property
    def is_struct(self):
        return self.type_id == lib.pSTRUCT

    @property
    def is_var(self):
        return self.type_id == lib.pVAR

    @property
    def is_addr(self):
        return self.type_id == lib.pADDR

    @property
    def is_atom(self):
        return self.type_id == lib.pATOM

    @property
    def is_int(self):
        return self.type_id == lib.pINT

    @property
    def is_float(self):
        return self.type_id == lib.pFLOAT

    @property
    def is_str(self):
        return self.type_id == lib.pSTR

    def unify(self, term):
        return bool(self.eng.ls_unify(self.ID, term.ID))

    def to_object(self):
        return self.eng.term_to_object(self)

    def _get_functor(self):
        arity = ffi.new("ARITY *")
        self.eng.ls_get_fa(self.ID, self.eng.buffer, arity)
        functor = ffi.string(self.eng.buffer)
        self._functor = functor
        self._arity = int(arity[0])

    def _get_arg_types(self):
        return [self.eng.ls_get_arg_type(self.ID, i)
                    for i in range(1, self.arity + 1)]

    def get_arg_term(self, i):
        term_ptr = ffi.new("TERMptr")
        self.eng.ls_get_arg(self.ID, i+1, lib.cTERM, term_ptr)
        if term_ptr[0] == ffi.NULL:
            return None
        return self.eng._make_term_object(term_ptr)

    def __str__(self):
        buf = self.eng.buffer
        length = self.eng.buffer_size
        res = self.eng.ls_term_to_str(self.ID, buf, length)
        return ffi.string(buf)

    def __repr__(self):
        return str(self)


class Engine:
    buffer_size = 65536

    def __init__(self, name):
        self.name = name
        self._eng_id = ffi.new("ENGidptr")
        lib.lsInitW(self._eng_id, name)
        self._register_lib_functions()

        self.buffer = ffi.new("wchar_t[]", self.buffer_size)
        self._wchar_t_cache = {}
        self._object_cahce = {}
        self.preds_table = {
            "pytrue": (2, ffi.callback("int(void *)")(self.cb_pytrue)),
            "pybind": (3, ffi.callback("int(void *)")(self.cb_pybind)),
            "pygetobj":  (3, ffi.callback("int(void *)")(self.cb_pygetobj)),
            "pydelobj": (1, ffi.callback("int(void *)")(self.cb_pydelobj)),
        }

        self.type_map = {
            lib.pATOM: [lib.cWSTR, "wchar_t *", convert_atom],
            lib.pSTR: [lib.cWSTR, "wchar_t *", ffi.string],
            lib.pINT: [lib.cINT, "int *", lambda o: int(o[0])],
            lib.pFLOAT: [lib.cDOUBLE, "double *", lambda o: float(o[0])],
            lib.pADDR: [lib.cADDR, "ssize_t *", self._get_pyobject]
        }
        self._preds_table = self.make_preds_table(self.preds_table)
        self.ls_init_preds(self._preds_table)

    def _register_lib_functions(self):
        for name in dir(lib):
            if name.startswith("ls"):
                self._add_lib_func(name, rc=name in RC_FUNCS)

    def _add_lib_func(self, name, rc=True):
        func_name = name
        if func_name.startswith("ls"):
            func_name = func_name[2:]
        if func_name.endswith("W"):
            func_name = func_name[:-1]
        func_name = "_".join(x.lower() for x in re.split("([A-Z][a-z]+)", func_name) if x)
        func_name = "ls_" + func_name
        lib_func = getattr(lib, name)
        id_ = self.ID
        def func(*args):
            res = lib_func(id_, *args)
            if rc and res != 0:
                error = self.get_error()
                raise AmziError("Error when call {}({}): {}".format(name, args, error))
            return res
        setattr(self, func_name, func)

    def get_wchar_array(self, name, cache=False):
        if name not in self._wchar_t_cache:
            arr = ffi.new("wchar_t[]", name)
            if cache:
                self._wchar_t_cache[name] = arr
            return arr
        return self._wchar_t_cache[name]

    def make_preds_table(self, preds):
        table = ffi.new("PRED_INITW[]", len(preds) + 1)
        for i, (key, item) in enumerate(preds.items()):
            name = self.get_wchar_array(key, cache=True)
            table[i].Pname = name
            table[i].Parity = item[0]
            table[i].Pfunc = item[1]
        return table

    def _pycall_help(self):
        arg0 = self.get_parm_term(0)
        arg1 = self.get_parm_term(1)
        funcname = arg0.to_object()
        funcargs = arg1.to_object()
        if not isinstance(funcargs, list):
            funcargs = [funcargs]
        func = getattr(funcexport, funcname)
        res = func(*funcargs)
        return res

    def cb_pybind(self, _):
        try:
            obj = self._pycall_help()
        except:
            return False
        term = ffi.new("TERMptr")
        self.ls_str_to_term(term, "{}".format(obj))
        res = self.ls_unify_parm(3, lib.cTERM, term)
        return bool(res)

    def cb_pygetobj(self, _):
        obj = self._pycall_help()
        addr = ffi.new("ssize_t *")
        addr[0] = id(obj)
        res = self.ls_unify_parm(3, lib.cADDR, addr)
        self._object_cahce[id(obj)] = obj
        return bool(res)

    def cb_pydelobj(self, _):
        addr = self.get_param_addr(0)
        if addr in self._object_cahce:
            del self._object_cahce[addr]
            return True
        else:
            return False

    def cb_pytrue(self, _):
        return bool(self._pycall_help())

    @property
    def ID(self):
        return self._eng_id[0]

    def load(self, filename, output=StreamOutput):
        self.ls_load(filename)
        self.ls_set_stream(lib.CUR_OUT, 3)
        self.ls_set_stream(lib.CUR_IN, 3)
        self.ls_set_stream(lib.CUR_ERR, 3)
        self.ls_set_stream(lib.USER_OUT, 3)
        self.ls_set_stream(lib.USER_IN, 3)
        self.ls_set_stream(lib.USER_ERR, 3)
        self.output_stream = output(self)
        self.input_stream = StringInput(self)

    def main(self):
        return self.ls_main()

    @property
    def cached_object(self):
        return self._object_cahce

    @property
    def output(self):
        return self.output_stream

    @output.setter
    def output(self, value):
        self.output_stream = value(self)

    @property
    def input(self):
        return self.input_stream

    def consult(self, filename):
        self.exec_str("consult(`{}`)".format(filename))

    def _assert_help(self, loc, term_str):
        func = getattr(lib, "lsAssert{}StrW".format(loc))
        res = func(self.ID, term_str)
        return bool(res)

    def assertz(self, term_str):
        return self._assert_help("z", term_str)

    def asserta(self, term_str):
        return self._assert_help("a", term_str)

    def assert_program(self, program):
        for clause in split_clauses(program):
            clause = clause.strip()
            if clause:
                self.assertz(clause)

    def _consult_str_help(self, command, program):
        program += "\nquit.\n"
        self.input.set_text(program)
        mute = self.output.mute
        self.output.mute = True
        self.exec_str(command)
        self.output.mute = mute

    def consult_str(self, program):
        self._consult_str_help("consult(user)", program)

    def reconsult_str(self, program):
        self._consult_str_help("reconsult(user)", program)

    def close(self):
        self.ls_close()

    def get_param_addr(self, i):
        addr = ffi.new("ssize_t *")
        self.ls_get_parm(i+1, lib.cADDR, addr)
        return int(addr[0])

    def get_parm_term(self, i):
        term_ptr = ffi.new("TERMptr")
        self.ls_get_parm(i+1, lib.cTERM, term_ptr)
        return self._make_term_object(term_ptr)

    def make_term(self, term_str):
        term = ffi.new("TERMptr")
        self.ls_str_to_term(term, term_str)
        return self._make_term_object(term)

    def _call_exec_help(self, funcname, term_str):
        term = ffi.new("TERMptr")
        res = getattr(lib, funcname)(self.ID, term, term_str)
        return bool(res), self._make_term_object(term)

    def call_str(self, term_str):
        return self._call_exec_help("lsCallStrW", term_str)

    def exec_str(self, term_str):
        return self._call_exec_help("lsExecStrW", term_str)

    def query_one(self, query):
        term_str = "varlist_query(`{}`, L, Z)".format(query)
        res, term = self.exec_str(term_str)
        if not res:
            return None
        query_res = term.get_arg_term(2).to_object()
        return dict(zip(query_res[::2], query_res[1::2]))

    def query_all(self, query):
        term_str = "varlist_query(`{}`, L, Z)".format(query)
        res, term = self.call_str(term_str)
        query_term = term.get_arg_term(2)
        if not res:
            return
        while True:
            query_res = query_term.to_object()
            yield dict(zip(query_res[::2], query_res[1::2]))
            if not self.redo():
                break

    def redo(self):
        res = self.ls_redo()
        return bool(res)

    def clear_call(self):
        res = self.ls_clear_call()
        return bool(res)

    def find_all(self, term_str):
        list_res = []
        res, term = self.call_str(term_str)
        if not res or term is None:
            return list_res
        list_res.append(term.to_object())
        while self.redo():
            list_res.append(term.to_object())
        return list_res

    def _make_term_object(self, term):
        return Term(self, term) if term[0] != ffi.NULL else None

    def _get_pyobject(self, addr):
        addr = int(addr[0])
        return self._object_cahce.get(addr, None)

    def term_to_object(self, term):
        type_id = term.type_id

        if term.is_list:
            head = term.head
            if head is None:
                return []
            list_res = []
            while True:
                list_res.append(term.head.to_object())
                term = term.tail
                if term is None:
                    break
            return list_res

        elif term.is_struct:
            return Struct(term.functor, term.arguments)

        elif term.is_var:
            return term

        if type_id in self.type_map:
            c_type, ffi_type, cast_func = self.type_map[type_id]
            self.ls_get_term(term.ID, c_type, self.buffer)
            ffi_obj = ffi.cast(ffi_type, self.buffer)
            return cast_func(ffi_obj)
        else:
            raise ValueError("Unknown Term type: {}".format(type_id))

    def object_to_term(self, obj):
        if isinstance(obj, str):
            term = ffi.new("TERMptr")
            func = self.ls_make_atom if re.match(r"^\w+$", obj) is not None else self.ls_make_str
            wchar_obj = self.get_wchar_array(obj)
            res = func(term, wchar_obj)
            return self._make_term_object(term)
        elif isinstance(obj, int):
            term = ffi.new("TERMptr")
            self.ls_make_int(term, obj)
            return self._make_term_object(term)
        elif isinstance(obj, float):
            term = ffi.new("TERMptr")
            self.ls_make_float(term, obj)
            return self._make_term_object(term)
        elif isinstance(obj, list):
            list_term = ffi.new("TERMptr")
            self.ls_make_list(list_term)
            for element in reversed(obj):
                element_term = self.object_to_term(element)
                self.ls_push_list(list_term, element_term.ID)
            return self._make_term_object(list_term)
        elif isinstance(obj, Struct):
            struct_term = ffi.new("TERMptr")
            functor = self.get_wchar_array(obj.functor)
            self.ls_make_fa(struct_term, functor, len(obj.arguments))
            for i, arg_obj in enumerate(obj.arguments, 1):
                arg_term = self.object_to_term(arg_obj)
                self.ls_unify_arg(struct_term, i, lib.cTERM, arg_term.address)
            return self._make_term_object(struct_term)

    def get_error(self):
        self.ls_get_except_msg(self.buffer, self.buffer_size)
        return ffi.string(self.buffer)


if __name__ == '__main__':
    eng = Engine("test")
    eng.load(find_files("dummy.xpl"))
