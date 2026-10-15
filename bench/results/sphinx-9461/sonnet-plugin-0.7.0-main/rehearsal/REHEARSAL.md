# Rehearsal: autodoc @classmethod @property
repro: python3 -m sphinx -b text -q .rehearsal/scaffold/docs .rehearsal/out
### S1: reproduce with scaffold docs project
- cmd: `/opt/miniconda3/envs/testbed/bin/python -m sphinx -b text -q .rehearsal/scaffold/docs .rehearsal/out`
- saw: only `property g` documented; classmethod+property `f` missing
- means: getattr(A,'f') returns the str "property", so PropertyDocumenter.can_document_member (isproperty(member)) is False
- plan: look up raw obj in parent.__dict__; unwrap classmethod.__func__; add :classmethod: option to py:property

repro: /opt/miniconda3/envs/testbed/bin/python -m sphinx -E -a -b text -q .rehearsal/scaffold/docs .rehearsal/out && grep -c "class property f" .rehearsal/out/index.txt
