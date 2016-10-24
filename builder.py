import os
from os import path
import subprocess
from glob import glob
from .utils import find_files


cmp_path = find_files("acmp.exe")[0]
lnk_path = find_files("alnk.exe")[0]


class Builder:
    def __init__(self, folder):
        self.folder = path.abspath(folder)
        self.xpl_filename = path.join(self.folder, path.basename(folder) + ".xpl")
        self.pro_files = self.find("*.pro")

    def load(self):
        xpl_fn = self.xpl_filename
        last_pro_time = max(os.stat(fn).st_mtime for fn in self.pro_files)
        if not path.exists(xpl_fn) or last_pro_time > os.stat(xpl_fn).st_mtime:
            self.build()
            return self.load()
        else:
            return xpl_fn

    def build(self):
        for pro_fn in self.pro_files:
            plm_fn = pro_fn.replace(".pro", ".plm")
            if not path.exists(plm_fn) or os.stat(plm_fn) < os.stat(pro_fn):
                cmd = [cmp_path, pro_fn]
                subprocess.call(cmd)
        plm_files = self.find("*.plm")
        subprocess.call([lnk_path, self.xpl_filename] + plm_files)

    def find(self, pattern):
        return glob(path.join(self.folder, pattern))

def main():
    import sys
    builder = Builder(sys.argv[1])
    print(builder.load())


if __name__ == '__main__':
    import sys
    sys.exit(int(main() or 0))
