import os
import sys


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from lit_wiki.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
