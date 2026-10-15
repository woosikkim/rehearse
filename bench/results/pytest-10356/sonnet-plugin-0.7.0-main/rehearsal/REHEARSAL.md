### S1: reproduce
- cmd: get_unpacked_marks on type("T",(F,B),{}) with foo on F, bar on B
- saw: only foo; bar lost (getattr(obj,"pytestmark") follows MRO, first wins)
- fix: collect pytestmark from each class __dict__ over MRO in get_unpacked_marks; store_mark uses consider_mro=False
repro: /opt/miniconda3/envs/testbed/bin/python -c 'import pytest; from _pytest.mark.structures import get_unpacked_marks; F=type("F",(),{"pytestmark":[pytest.mark.foo.mark]}); B=type("B",(),{"pytestmark":[pytest.mark.bar.mark]}); T=type("T",(F,B),{}); print(list(get_unpacked_marks(T)))'
