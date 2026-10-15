$ ls .rehearsal; grep -n "pytestmark\|def get_unpacked_marks\|def store_mark" -n src/_pytest/mark/structures.py; grep -rn "get_unpacked_marks" src | head
active
fixtures
scaffold
358:def get_unpacked_marks(obj: object) -> Iterable[Mark]:
360:    mark_list = getattr(obj, "pytestmark", [])
383:def store_mark(obj, mark: Mark) -> None:
389:    # Always reassign name to avoid updating pytestmark in a reference that
391:    obj.pytestmark = [*get_unpacked_marks(obj), mark]
src/_pytest/python.py:66:from _pytest.mark.structures import get_unpacked_marks
src/_pytest/python.py:314:                self.own_markers.extend(get_unpacked_marks(self.obj))
src/_pytest/python.py:1717:        self.own_markers.extend(get_unpacked_marks(self.obj))
src/_pytest/mark/structures.py:358:def get_unpacked_marks(obj: object) -> Iterable[Mark]:
src/_pytest/mark/structures.py:391:    obj.pytestmark = [*get_unpacked_marks(obj), mark]

$ python3 -m pytest .rehearsal/scaffold -m bar --collect-only -q -p no:cacheprovider 2>&1 | tail -5
/opt/miniconda3/bin/python3: No module named pytest

$ ls -d /opt/miniconda3/envs/* ; which -a pytest python
Exit code 1
/opt/miniconda3/envs/testbed
/opt/miniconda3/bin/python
/usr/bin/python
/bin/python

$ P=/opt/miniconda3/envs/testbed/bin/python; $P -m pytest .rehearsal/scaffold -m bar --collect-only -q -p no:cacheprovider 2>&1 | tail -5; $P -m pytest .rehearsal/scaffold -m foo --collect-only -q -p no:cacheprovider 2>&1 | tail -5
no tests collected (1 deselected) in 0.00s
.rehearsal/scaffold/test_mro.py::TestDings::test_dings
1 test collected in 0.00s

$ grep -n "^from typing\|    List,$" src/_pytest/mark/structures.py | head
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

