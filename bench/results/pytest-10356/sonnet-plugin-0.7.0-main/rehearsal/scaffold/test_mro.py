import pytest

@pytest.mark.foo
class Foo: pass

@pytest.mark.bar
class Bar: pass

class TestDings(Foo, Bar):
    def test_dings(self, request):
        print("MARKS", [m.name for m in request.node.iter_markers()])
