### S1: analyzer attr_docs for mod (Base/Derived)
- saw: keys are ('Base','attr1'), ('Base','attr2'); filter_members looks up ('Derived', name) -> miss, so inherited attrs dropped
- fix plan: in filter_members, with inherited_members, merge base-class attr_docs into the Derived namespace
repro: /opt/miniconda3/envs/testbed/bin/python -m sphinx -q -E -b text .rehearsal/scaffold/proj .rehearsal/out
