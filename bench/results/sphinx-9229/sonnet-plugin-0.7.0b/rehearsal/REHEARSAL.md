# Rehearsal: autodoc alias-of-class docstring dropped
### S1: scaffold file.py `Bar = OrderedDict` + docstring; sphinx -b text
- saw: only `alias of "collections.OrderedDict"`; same-module alias shows docstring
- means: ClassDocumenter analyzer is for the class's module (collections), not the alias's module; add_content also overwrites more_content
- fix: ClassDocumenter.add_content use ModuleAnalyzer of self.modname; skip "alias of" when comment exists; get_doc returns [] then
repro: /opt/miniconda3/envs/testbed/bin/python -m sphinx -b text -q -E .rehearsal/scaffold/p .rehearsal/out
repro: /opt/miniconda3/envs/testbed/bin/python -m sphinx -b text -q -E .rehearsal/scaffold/p .rehearsal/out && grep -c "Bar alias doc" .rehearsal/out/index.txt
