$ ls .rehearsal; grep -n "alias of\|class DataDocumenter\|class GenericAliasMixin\|class NewTypeMixin\|class TypeVarMixin\|class UninitializedGlobalVariableMixin\|def update_content\|def get_doc" sphinx/ext/autodoc/__init__.py
active
base
fixtures
scaffold
552:    def get_doc(self, ignore: int = None) -> Optional[List[List[str]]]:
1236:    def get_doc(self, ignore: int = None) -> List[List[str]]:
1676:    def get_doc(self, ignore: int = None) -> Optional[List[List[str]]]:
1728:                more_content = StringList([_('alias of %s') % restify(self.object)], source='')
1767:class DataDocumenterMixinBase:
1784:    def update_content(self, more_content: StringList) -> None:
1789:class GenericAliasMixin(DataDocumenterMixinBase):
1799:    def update_content(self, more_content: StringList) -> None:
1801:            more_content.append(_('alias of %s') % restify(self.object), '')
1807:class NewTypeMixin(DataDocumenterMixinBase):
1817:    def update_content(self, more_content: StringList) -> None:
1820:            more_content.append(_('alias of %s') % supertype, '')
1826:class TypeVarMixin(DataDocumenterMixinBase):
1836:    def get_doc(self, ignore: int = None) -> Optional[List[List[str]]]:
1850:    def update_content(self, more_content: StringList) -> None:
1862:            more_content.append(_('alias of TypeVar(%s)') % ", ".join(attrs), '')
1868:class UninitializedGlobalVariableMixin(DataDocumenterMixinBase):
1902:    def get_doc(self, ignore: int = None) -> Optional[List[List[str]]]:
1909:class DataDocumenter(GenericAliasMixin, NewTypeMixin, TypeVarMixin,
2001:    def get_doc(self, ignore: int = None) -> Optional[List[List[str]]]:
2211:    def get_doc(self, ignore: int = None) -> Optional[List[List[str]]]:
2266:    def get_doc(self, ignore: int = None) -> Optional[List[List[str]]]:
2305:    def get_doc(self, ignore: int = None) -> Optional[List[List[str]]]:
2423:    def get_doc(self, ignore: int = None) -> Optional[List[List[str]]]:
2574:    def get_doc(self, ignore: int = None) -> Optional[List[List[str]]]:
2663:def get_documenters(app: Sphinx) -> Dict[str, Type[Documenter]]:

$ grep -n "more_content" sphinx/ext/autodoc/__init__.py | sed -n 1,40p; ls .rehearsal/base .rehearsal/scaffold
598:    def add_content(self, more_content: Optional[StringList], no_docstring: bool = False
637:        if more_content:
638:            for line, src in zip(more_content.data, more_content.items):
890:    def generate(self, more_content: Optional[StringList] = None, real_modname: str = None,
895:        If *more_content* is given, include that content. If *real_modname* is
973:        self.add_content(more_content)
1724:    def add_content(self, more_content: Optional[StringList], no_docstring: bool = False
1728:                more_content = StringList([_('alias of %s') % restify(self.object)], source='')
1732:        super().add_content(more_content)
1739:    def generate(self, more_content: Optional[StringList] = None, real_modname: str = None,
1746:        return super().generate(more_content=more_content,
1784:    def update_content(self, more_content: StringList) -> None:
1799:    def update_content(self, more_content: StringList) -> None:
1801:            more_content.append(_('alias of %s') % restify(self.object), '')
1802:            more_content.append('', '')
1804:        super().update_content(more_content)
1817:    def update_content(self, more_content: StringList) -> None:
1820:            more_content.append(_('alias of %s') % supertype, '')
1821:            more_content.append('', '')
1823:        super().update_content(more_content)
1850:    def update_content(self, more_content: StringList) -> None:
1862:            more_content.append(_('alias of TypeVar(%s)') % ", ".join(attrs), '')
1863:            more_content.append('', '')
1865:        super().update_content(more_content)
2009:    def add_content(self, more_content: Optional[StringList], no_docstring: bool = False
2015:        if not more_content:
2016:            more_content = StringList()
2018:        self.update_content(more_content)
2019:        super().add_content(more_content, no_docstring=no_docstring)
2590:    def add_content(self, more_content: Optional[StringList], no_docstring: bool = False
2596:        if more_content is None:
2597:            more_content = StringList()
2598:        self.update_content(more_content)
2599:        super().add_content(more_content, no_docstring)
.rehearsal/base
.rehearsal/scaffold:

$ mkdir -p .rehearsal/scaffold/proj && cd .rehearsal/scaffold/proj && cat > file.py <<'EOF'
from pathlib import Path
from typing import Any, Callable, Dict, Union

ScaffoldOpts = Dict[str, Any]
"""Dictionary doc."""

FileContents = Union[str, None]
"""Contents doc."""

FileOp = Callable[[Path, FileContents, ScaffoldOpts], Union[Path, None]]
"""FileOp doc."""
EOF
printf "extensions=['sphinx.ext.autodoc']\n" > conf.py
printf "T\n=\n\n.. automodule:: file\n   :members:\n" > index.rst
cd /testbed && python -m sphinx -q -b text .rehearsal/scaffold/proj .rehearsal/out && cat .rehearsal/out/index.txt | tee .rehearsal/fixtures/before.txt
Exit code 1
Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "/testbed/sphinx/__main__.py", line 13, in <module>
    from sphinx.cmd.build import main
  File "/testbed/sphinx/cmd/build.py", line 21, in <module>
    from docutils.utils import SystemMessage
ModuleNotFoundError: No module named 'docutils'
  -> RemovedInSphinx40Warning() = None  [sphinx/deprecation.py:18]
  -> RemovedInSphinx50Warning() = None  [sphinx/deprecation.py:22]
  -> RemovedInSphinx60Warning() = None  [sphinx/deprecation.py:26]
  -> _ModuleWrapper() = None  [sphinx/deprecation.py:50]
  -> DeprecatedDict() = <cell>  [sphinx/deprecation.py:91]
  -> <module>() = None  [sphinx/deprecation.py:67]
  -> <module>() = None  [sphinx/__init__.py:46]
  -> <module>() = None  [sphinx/cmd/__init__.py:1]
  -> <module>() raised ModuleNotFoundError: No module named 'docutils'  [sphinx/cmd/build.py:21]
  -> <module>() raised ModuleNotFoundError: No module named 'docutils'  [sphinx/__main__.py:13]

$ cd /testbed; ls /opt; conda env list 2>/dev/null; ls .venv 2>/dev/null; which -a python python3
miniconda3
# conda environments:
#
base                     /opt/miniconda3
testbed               *  /opt/miniconda3/envs/testbed
/opt/miniconda3/bin/python
/usr/bin/python
/bin/python
/opt/miniconda3/bin/python3
/usr/bin/python3
/bin/python3

$ cd /testbed; P=/opt/miniconda3/envs/testbed/bin/python; $P -m sphinx -q -b text .rehearsal/scaffold/proj .rehearsal/out && cat .rehearsal/out/index.txt | tee .rehearsal/fixtures/before.txt
WARNING: autodoc: failed to import module 'file'; the following exception was raised:
No module named 'file'
T
*
  -> SphinxLoggerAdapter.log(level=10, msg='[app] setting up extension: %r') = None  [sphinx/util/logging.py:123]
  -> is_translator_registered(catalog='sphinx', namespace='console') = True  [sphinx/locale/__init__.py:191]
  -> get_translator(catalog='sphinx', namespace='console') = <NullTranslations>  [sphinx/locale/__init__.py:187]
  -> gettext(message='while setting up extension %s:') = 'while setting up extension %s:'  [sphinx/locale/__init__.py:234]
  -> MessagePrefixFilter.__init__(prefix='while setting up extension sphinx.builders.changes:') = None  [sphinx/util/logging.py:441]
  -> prefixed_warnings(prefix='while setting up extension sphinx.builders.changes:') = None  [sphinx/util/logging.py:326]
  -> _ModuleWrapper.__getattr__(name='__spec__') = <ModuleSpec>  [sphinx/deprecation.py:52]
  -> _ModuleWrapper.__getattr__(name='__path__') raised AttributeError: module 'sphinx.util.typing' has no attribute '__path__'  [sphinx/deprecation.py:52]
  -> _ModuleWrapper.__getattr__(name='OptionSpec') = <_GenericAlias>  [sphinx/deprecation.py:52]
  -> is_translator_registered(catalog='sphinx', namespace='general') = True  [sphinx/locale/__init__.py:191]

$ cd /testbed; P=/opt/miniconda3/envs/testbed/bin/python; printf "import os, sys\nsys.path.insert(0, os.path.abspath('.'))\nextensions=['sphinx.ext.autodoc']\n" > .rehearsal/scaffold/proj/conf.py; $P -m sphinx -q -E -b text .rehearsal/scaffold/proj .rehearsal/out && cat .rehearsal/out/index.txt | tee .rehearsal/fixtures/before.txt
T
*
file.FileContents
   Contents doc.
   alias of "Optional"["str"]
file.FileOp
   FileOp doc.
   alias of "Callable"[["pathlib.Path", "Optional"["str"],
   "Dict"["str", "Any"]], "Optional"["pathlib.Path"]]
file.ScaffoldOpts
   Dictionary doc.
   alias of "Dict"["str", "Any"]
  -> SphinxLoggerAdapter.log(level=10, msg='[app] setting up extension: %r') = None  [sphinx/util/logging.py:123]
  -> is_translator_registered(catalog='sphinx', namespace='console') = True  [sphinx/locale/__init__.py:191]
  -> get_translator(catalog='sphinx', namespace='console') = <NullTranslations>  [sphinx/locale/__init__.py:187]
  -> gettext(message='while setting up extension %s:') = 'while setting up extension %s:'  [sphinx/locale/__init__.py:234]
  -> MessagePrefixFilter.__init__(prefix='while setting up extension sphinx.builders.changes:') = None  [sphinx/util/logging.py:441]
  -> prefixed_warnings(prefix='while setting up extension sphinx.builders.changes:') = None  [sphinx/util/logging.py:326]
  -> _ModuleWrapper.__getattr__(name='__spec__') = <ModuleSpec>  [sphinx/deprecation.py:52]
  -> _ModuleWrapper.__getattr__(name='__path__') raised AttributeError: module 'sphinx.util.typing' has no attribute '__path__'  [sphinx/deprecation.py:52]
  -> _ModuleWrapper.__getattr__(name='OptionSpec') = <_GenericAlias>  [sphinx/deprecation.py:52]
  -> is_translator_registered(catalog='sphinx', namespace='general') = True  [sphinx/locale/__init__.py:191]

