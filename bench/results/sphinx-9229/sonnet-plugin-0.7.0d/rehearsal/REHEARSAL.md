# Rehearsal: alias docstring vs "alias of"
repro: /opt/miniconda3/envs/testbed/bin/python -m sphinx -q -E -b text .rehearsal/scaffold/p .rehearsal/out && cat .rehearsal/out/index.txt
### S1: built scaffold with 3 typing aliases + class alias Bar=Foo with comment
- saw: py3.9 shows comments for all; class alias Bar shows comment AND "alias of file.Foo"
- means: ClassDocumenter (doc_as_attr) always overrides content with "alias of"; fix: skip it when a variable comment exists (and drop class docstring)
