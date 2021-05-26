
from jedi import Script
from jedi.api import Project
from jedi.api.classes import Name

simple_proj = Project('./tests/examples/simple/')
assert simple_proj

s = Script(path='./tests/examples/simple/__init__.py', project=simple_proj)
assert s

cls: Name = s.infer(10, 9)[0]
assert cls.is_definition()
assert cls.full_name == '__main__.SimpleClass'

import_proj = Project('./tests/examples/two_files/')
a = Script(path="./tests/examples/two_files/a.py", project=import_proj)
b = Script(path="./tests/examples/two_files/b.py", project=import_proj)

b.get_names()

from jedi import Script
from jedi.api import Project
from jedi.api.classes import Name
import_proj = Project('./')
a = Script(path="./a.py", project=import_proj)
b = Script(path="./b.py", project=import_proj)


class JSONData:
    ...

from typing import Protocol

class NamedProtocol(Protocol):
    name: str

class Something:
    name: str

class Other:
    name: str

def this_actually_only_wants_something(x: NamedProtocol):
    return x.name

with open('asdf') as f:
    this_expects_number(f.read())
