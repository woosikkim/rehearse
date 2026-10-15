$ ls .rehearsal; grep -n "def get_unpacked_marks" -B3 -A25 src/_pytest/mark/structures.py; grep -rn "get_unpacked_marks\|pytestmark" src/_pytest --include=*.py | grep -v "^src/_pytest/mark/structures.py"
active
base
fixtures
scaffold
355-        return self.with_args(*args, **kwargs)
356-
357-
358:def get_unpacked_marks(obj: object) -> Iterable[Mark]:
359-    """Obtain the unpacked marks that are stored on an object."""
360-    mark_list = getattr(obj, "pytestmark", [])
361-    if not isinstance(mark_list, list):
362-        mark_list = [mark_list]
363-    return normalize_mark_list(mark_list)
364-
365-
366-def normalize_mark_list(
367-    mark_list: Iterable[Union[Mark, MarkDecorator]]
368-) -> Iterable[Mark]:
369-    """
370-    Normalize an iterable of Mark or MarkDecorator objects into a list of marks
371-    by retrieving the `mark` attribute on MarkDecorator instances.
372-
373-    :param mark_list: marks to normalize
374-    :returns: A new list of the extracted Mark objects
375-    """
376-    for mark in mark_list:
377-        mark_obj = getattr(mark, "mark", mark)
378-        if not isinstance(mark_obj, Mark):
379-            raise TypeError(f"got {repr(mark_obj)} instead of Mark")
380-        yield mark_obj
381-
382-
383-def store_mark(obj, mark: Mark) -> None:
src/_pytest/python.py:66:from _pytest.mark.structures import get_unpacked_marks
src/_pytest/python.py:314:                self.own_markers.extend(get_unpacked_marks(self.obj))
src/_pytest/python.py:1717:        self.own_markers.extend(get_unpacked_marks(self.obj))
src/_pytest/config/__init__.py:354:    known_marks: set[str] = {m.name for m in getattr(method, "pytestmark", [])}
src/_pytest/terminal.py:1345:        # Folding reports with global pytestmark variable.
src/_pytest/terminal.py:1351:            and "pytestmark" not in keywords

$ mkdir -p .rehearsal/scaffold/t && cat > .rehearsal/scaffold/t/test_mro.py <<'EOF'
import pytest

@pytest.mark.foo
class Foo: pass

@pytest.mark.bar
class Bar: pass

class TestDings(Foo, Bar):
    def test_dings(self): pass
EOF
python -m pytest .rehearsal/scaffold/t -q --collect-only -m bar 2>&1 | tail -5; sed -n 380,400p src/_pytest/mark/structures.py; sed -n 305,318p src/_pytest/python.py
/opt/miniconda3/bin/python: No module named pytest
        yield mark_obj
def store_mark(obj, mark: Mark) -> None:
    """Store a Mark on an object.
    This is used to implement the Mark declarations/decorators correctly.
    """
    assert isinstance(mark, Mark), mark
    # Always reassign name to avoid updating pytestmark in a reference that
    # was only borrowed.
    obj.pytestmark = [*get_unpacked_marks(obj), mark]
# Typing for builtin pytest marks. This is cheating; it gives builtin marks
# special privilege, and breaks modularity. But practicality beats purity...
if TYPE_CHECKING:
    from _pytest.scope import _ScopeName
    class _SkipMarkDecorator(MarkDecorator):
        @overload  # type: ignore[override,misc,no-overload-impl]
    @property
    def obj(self):
        """Underlying Python object."""
        obj = getattr(self, "_obj", None)
        if obj is None:
            self._obj = obj = self._getobj()
            # XXX evil hack
            # used to avoid Function marker duplication
            if self._ALLOW_MARKERS:
                self.own_markers.extend(get_unpacked_marks(self.obj))
                # This assumes that `obj` is called before there is a chance
                # to add custom keys to `self.keywords`, so no fear of overriding.
                self.keywords.update((mark.name, mark) for mark in self.own_markers)
        return obj

$ sed -n 1,50p src/_pytest/mark/structures.py | grep -n import
1:import collections.abc
2:import inspect
3:import warnings
4:from typing import Any
5:from typing import Callable
6:from typing import Collection
7:from typing import Iterable
8:from typing import Iterator
9:from typing import List
10:from typing import Mapping
11:from typing import MutableMapping
12:from typing import NamedTuple
13:from typing import Optional
14:from typing import overload
15:from typing import Sequence
16:from typing import Set
17:from typing import Tuple
18:from typing import Type
19:from typing import TYPE_CHECKING
20:from typing import TypeVar
21:from typing import Union
23:import attr
25:from .._code import getfslineno
26:from ..compat import ascii_escaped
27:from ..compat import final
28:from ..compat import NOTSET
29:from ..compat import NotSetType
30:from _pytest.config import Config
31:from _pytest.deprecated import check_ispytest
32:from _pytest.outcomes import fail
33:from _pytest.warning_types import PytestUnknownMarkWarning
36:    from ..nodes import Node
49:    from ..nodes import Collector

$ ls /opt /opt/miniconda3/envs 2>&1; which -a python python3 pytest
Exit code 1
/opt:
miniconda3
/opt/miniconda3/envs:
testbed
/opt/miniconda3/bin/python
/usr/bin/python
/bin/python
/opt/miniconda3/bin/python3
/usr/bin/python3
/bin/python3

$ /opt/miniconda3/envs/testbed/bin/python -m pytest .rehearsal/scaffold/t -q --collect-only -m bar 2>&1 | tail -5; /opt/miniconda3/envs/testbed/bin/python -m pytest .rehearsal/scaffold/t -q --collect-only -m foo 2>&1 | tail -5
no tests collected (1 deselected) in 0.00s
.rehearsal/scaffold/t/test_mro.py::TestDings::test_dings
1 test collected in 0.00s

