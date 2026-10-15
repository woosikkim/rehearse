repro: /opt/miniconda3/envs/testbed/bin/python -m sphinx -q -b text .rehearsal/scaffold/docs .rehearsal/scaffold/out
### S1: autoclass Derived :inherited-members: omits Base.attr (#: comment)
- saw: fixtures/before.txt has no attr
- means: attr_docs keyed (Derived, attr) not found; base-class comment ignored, has_doc False
- fix: get_class_members attaches docstring from base-class analyzers via mro
repro: /opt/miniconda3/envs/testbed/bin/python -m sphinx -q -E -a -b text .rehearsal/scaffold/docs .rehearsal/scaffold/out 2>/dev/null; cat .rehearsal/scaffold/out/index.txt
