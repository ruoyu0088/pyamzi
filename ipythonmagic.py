from IPython.core import magic_arguments
from IPython.core.magic import Magics, magics_class, cell_magic, line_cell_magic, line_magic
from .pyamzi import Engine
from .utils import find_files

name_argument = magic_arguments.argument('-n', '--name',
            help='Specify a name for logic server engine')

@magics_class
class AmziMagics(Magics):
    def __init__(self, shell):
        super(AmziMagics, self).__init__(shell)
        self.engines = {}

    def get_engine(self, args):
        if isinstance(args, dict):
            name = args.get("name", None)
        else:
            name = getattr(args, "name", None)
        if name is None:
            name = "default"

        if name not in self.engines:
            self.engines[name] = eng = Engine(name)
            eng.load(find_files("dummy.xpl")[0])
        return self.engines[name]

    @magic_arguments.magic_arguments()
    @name_argument
    @cell_magic
    def prolog(self, line, cell):
        args = magic_arguments.parse_argstring(self.prolog, line)
        eng = self.get_engine(args)
        eng.assert_program(cell)

    def _line_cell_help(self, line, cell):
        opts, stmt = self.parse_options(line,'n:tcp:qo',
                                        posix=False, strict=False)
        eng = self.get_engine(opts)
        code = cell if cell is not None else stmt
        return eng, code

    @line_cell_magic
    def query(self, line='', cell=None):
        eng, code = self._line_cell_help(line, cell)
        res, term = eng.call_str(code)
        return res, term

    @line_cell_magic
    def findall(self, line='', cell=None):
        eng, code = self._line_cell_help(line, cell)
        res = eng.find_all(code)
        return res

    @line_magic
    def engine(self, line):
        line = line.strip()
        name = None if line == "" else line
        return self.get_engine({"name":name})


def load_ipython_extension(ip):
    ip.register_magics(AmziMagics)