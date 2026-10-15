$ ls .rehearsal; grep -n "pytestmark\|def get_unpacked_marks\|store_mark" -r src/_pytest/mark/structures.py src/_pytest/python.py | head -30
active
base
fixtures
scaffold
src/_pytest/mark/structures.py:353:                store_mark(func, self.mark)
src/_pytest/mark/structures.py:358:def get_unpacked_marks(obj: object) -> Iterable[Mark]:
src/_pytest/mark/structures.py:360:    mark_list = getattr(obj, "pytestmark", [])
src/_pytest/mark/structures.py:383:def store_mark(obj, mark: Mark) -> None:
src/_pytest/mark/structures.py:389:    # Always reassign name to avoid updating pytestmark in a reference that
src/_pytest/mark/structures.py:391:    obj.pytestmark = [*get_unpacked_marks(obj), mark]

$ sed -n 355,395p src/_pytest/mark/structures.py; grep -rn "get_unpacked_marks" src | grep -v "def "
        return self.with_args(*args, **kwargs)
def get_unpacked_marks(obj: object) -> Iterable[Mark]:
    """Obtain the unpacked marks that are stored on an object."""
    mark_list = getattr(obj, "pytestmark", [])
    if not isinstance(mark_list, list):
        mark_list = [mark_list]
    return normalize_mark_list(mark_list)
def normalize_mark_list(
    mark_list: Iterable[Union[Mark, MarkDecorator]]
) -> Iterable[Mark]:
    """
    Normalize an iterable of Mark or MarkDecorator objects into a list of marks
    by retrieving the `mark` attribute on MarkDecorator instances.
    :param mark_list: marks to normalize
    :returns: A new list of the extracted Mark objects
    """
    for mark in mark_list:
        mark_obj = getattr(mark, "mark", mark)
        if not isinstance(mark_obj, Mark):
            raise TypeError(f"got {repr(mark_obj)} instead of Mark")
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
src/_pytest/python.py:66:from _pytest.mark.structures import get_unpacked_marks
src/_pytest/python.py:314:                self.own_markers.extend(get_unpacked_marks(self.obj))
src/_pytest/python.py:1717:        self.own_markers.extend(get_unpacked_marks(self.obj))
src/_pytest/mark/structures.py:391:    obj.pytestmark = [*get_unpacked_marks(obj), mark]

$ python3 -c 'import pytest; from _pytest.mark.structures import get_unpacked_marks; F=type("F",(),{"pytestmark":[pytest.mark.foo.mark]}); B=type("B",(),{"pytestmark":[pytest.mark.bar.mark]}); T=type("T",(F,B),{}); print(list(get_unpacked_marks(T)))'
Exit code 1
Traceback (most recent call last):
  File "<string>", line 1, in <module>
ModuleNotFoundError: No module named 'pytest'

$ ls -d /testbed/.venv /opt/*/envs 2>&1 | head; which -a python python3; conda env list 2>&1 | head
ls: cannot access '/testbed/.venv': No such file or directory
/opt/miniconda3/envs
/opt/miniconda3/bin/python
/usr/bin/python
/bin/python
/opt/miniconda3/bin/python3
/usr/bin/python3
/bin/python3
# conda environments:
#
base                     /opt/miniconda3
testbed               *  /opt/miniconda3/envs/testbed

$ /opt/miniconda3/envs/testbed/bin/python -c 'import pytest; from _pytest.mark.structures import get_unpacked_marks; F=type("F",(),{"pytestmark":[pytest.mark.foo.mark]}); B=type("B",(),{"pytestmark":[pytest.mark.bar.mark]}); T=type("T",(F,B),{}); print(list(get_unpacked_marks(T)))'
[Mark(name='foo', args=(), kwargs={})]

