$ ls .rehearsal; grep -n "alias of\|class GenericAliasMixin\|class TypeVarMixin\|class UninitializedGlobalVariableMixin\|class DataDocumenter\|class ClassDocumenter\|def update_content\|def get_doc\|def should_suppress" sphinx/ext/autodoc/__init__.py
active
base
fixtures
scaffold
552:    def get_doc(self, ignore: int = None) -> Optional[List[List[str]]]:
1236:    def get_doc(self, ignore: int = None) -> List[List[str]]:
1426:class ClassDocumenter(DocstringSignatureMixin, ModuleLevelDocumenter):  # type: ignore
1676:    def get_doc(self, ignore: int = None) -> Optional[List[List[str]]]:
1728:                more_content = StringList([_('alias of %s') % restify(self.object)], source='')
1767:class DataDocumenterMixinBase:
1776:    def should_suppress_directive_header(self) -> bool:
1780:    def should_suppress_value_header(self) -> bool:
1784:    def update_content(self, more_content: StringList) -> None:
1789:class GenericAliasMixin(DataDocumenterMixinBase):
1795:    def should_suppress_directive_header(self) -> bool:
1799:    def update_content(self, more_content: StringList) -> None:
1801:            more_content.append(_('alias of %s') % restify(self.object), '')
1813:    def should_suppress_directive_header(self) -> bool:
1817:    def update_content(self, more_content: StringList) -> None:
1820:            more_content.append(_('alias of %s') % supertype, '')
1826:class TypeVarMixin(DataDocumenterMixinBase):
1832:    def should_suppress_directive_header(self) -> bool:
1836:    def get_doc(self, ignore: int = None) -> Optional[List[List[str]]]:
1850:    def update_content(self, more_content: StringList) -> None:
1862:            more_content.append(_('alias of TypeVar(%s)') % ", ".join(attrs), '')
1868:class UninitializedGlobalVariableMixin(DataDocumenterMixinBase):
1898:    def should_suppress_value_header(self) -> bool:
1902:    def get_doc(self, ignore: int = None) -> Optional[List[List[str]]]:
1909:class DataDocumenter(GenericAliasMixin, NewTypeMixin, TypeVarMixin,
1947:    def should_suppress_value_header(self) -> bool:
2001:    def get_doc(self, ignore: int = None) -> Optional[List[List[str]]]:
2211:    def get_doc(self, ignore: int = None) -> Optional[List[List[str]]]:
2262:    def should_suppress_value_header(self) -> bool:
2266:    def get_doc(self, ignore: int = None) -> Optional[List[List[str]]]:
2298:    def should_suppress_directive_header(self) -> bool:
2305:    def get_doc(self, ignore: int = None) -> Optional[List[List[str]]]:
2370:    def should_suppress_value_header(self) -> bool:
2419:    def should_suppress_value_header(self) -> bool:
2423:    def get_doc(self, ignore: int = None) -> Optional[List[List[str]]]:
2522:    def should_suppress_value_header(self) -> bool:

$ grep -n "update_content" sphinx/ext/autodoc/__init__.py | tail -5; sed -n 1960,2030p sphinx/ext/autodoc/__init__.py
1823:        super().update_content(more_content)
1850:    def update_content(self, more_content: StringList) -> None:
1865:        super().update_content(more_content)
2018:        self.update_content(more_content)
2598:        self.update_content(more_content)
        sourcename = self.get_sourcename()
        if self.options.annotation is SUPPRESS or self.should_suppress_directive_header():
            pass
        elif self.options.annotation:
            self.add_line('   :annotation: %s' % self.options.annotation,
                          sourcename)
        else:
            # obtain annotation for this data
            annotations = get_type_hints(self.parent, None, self.config.autodoc_type_aliases)
            if self.objpath[-1] in annotations:
                objrepr = stringify_typehint(annotations.get(self.objpath[-1]))
                self.add_line('   :type: ' + objrepr, sourcename)
            try:
                if self.options.no_value or self.should_suppress_value_header():
                    pass
                else:
                    objrepr = object_description(self.object)
                    self.add_line('   :value: ' + objrepr, sourcename)
            except ValueError:
                pass
    def document_members(self, all_members: bool = False) -> None:
        pass
    def get_real_modname(self) -> str:
        real_modname = self.get_attr(self.parent or self.object, '__module__', None)
        return real_modname or self.modname
    def get_module_comment(self, attrname: str) -> Optional[List[str]]:
        try:
            analyzer = ModuleAnalyzer.for_module(self.modname)
            analyzer.analyze()
            key = ('', attrname)
            if key in analyzer.attr_docs:
                return list(analyzer.attr_docs[key])
        except PycodeError:
            pass
        return None

$ mkdir -p .rehearsal/scaffold/p && cd .rehearsal/scaffold/p && cat > file.py <<'EOF'
from pathlib import Path
from typing import Any, Callable, Dict, Union

ScaffoldOpts = Dict[str, Any]
"""Doc of opts."""

FileContents = Union[str, None]
"""Doc of contents."""

FileOp = Callable[[Path, FileContents, ScaffoldOpts], Union[Path, None]]
"""Doc of fileop."""
EOF
printf "extensions=['sphinx.ext.autodoc']\nimport sys,os\nsys.path.insert(0,os.path.abspath('.'))\n" > conf.py
printf "T\n=\n\n.. automodule:: file\n   :members:\n" > index.rst
cd /testbed && python -m sphinx -q -b text .rehearsal/scaffold/p .rehearsal/out && cat .rehearsal/out/index.txt
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

$ cd /testbed; ls /opt/*/envs 2>/dev/null; ls -d .venv /opt/* 2>/dev/null; which -a python python3; conda env list 2>/dev/null
testbed
/opt/miniconda3
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

$ cd /testbed; P=/opt/miniconda3/envs/testbed/bin/python; $P -m sphinx -q -b text .rehearsal/scaffold/p .rehearsal/out && cat .rehearsal/out/index.txt
T
*
file.FileContents
   Doc of contents.
   alias of "Optional"["str"]
file.FileOp
   Doc of fileop.
   alias of "Callable"[["pathlib.Path", "Optional"["str"],
   "Dict"["str", "Any"]], "Optional"["pathlib.Path"]]
file.ScaffoldOpts
   Doc of opts.
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

$ cd /testbed; P=/opt/miniconda3/envs/testbed/bin/python; printf 'class Foo:\n    """Foo doc"""\n\nBar = Foo\n"""Doc of Bar alias."""\n' >> .rehearsal/scaffold/p/file.py; $P -m sphinx -q -E -b text .rehearsal/scaffold/p .rehearsal/out && tail -12 .rehearsal/out/index.txt
   alias of "Callable"[["pathlib.Path", "Optional"["str"],
   "Dict"["str", "Any"]], "Optional"["pathlib.Path"]]
class file.Foo
   Foo doc
file.ScaffoldOpts
   Doc of opts.
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

$ cd /testbed; P=/opt/miniconda3/envs/testbed/bin/python; printf "T\n=\n\n.. autoclass:: file.Bar\n" > .rehearsal/scaffold/p/index.rst; $P -m sphinx -q -E -b text .rehearsal/scaffold/p .rehearsal/out && cat .rehearsal/out/index.txt
T
*
file.Bar
   Doc of Bar alias.
   alias of "file.Foo"
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

$ cd /testbed; P=/opt/miniconda3/envs/testbed/bin/python; printf "T\n=\n\n.. automodule:: file\n   :members:\n   :undoc-members:\n" > .rehearsal/scaffold/p/index.rst; $P -m sphinx -q -E -b text .rehearsal/scaffold/p .rehearsal/out && tail -8 .rehearsal/out/index.txt; $P -c "import sys;print(sys.version)"; sed -n 1676,1684p sphinx/ext/autodoc/__init__.py
   Foo doc
file.ScaffoldOpts
   Doc of opts.
   alias of "Dict"["str", "Any"]
3.9.20 (main, Oct  3 2024, 07:27:41) 
[GCC 11.2.0]
    def get_doc(self, ignore: int = None) -> Optional[List[List[str]]]:
        if self.doc_as_attr:
            # Don't show the docstring of the class when it is an alias.
            return None
        lines = getattr(self, '_new_docstrings', None)
        if lines is not None:
            return lines
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

$ cd /testbed; grep -n "doc_as_attr" sphinx/ext/autodoc/__init__.py; grep -n "def check_module" -A22 sphinx/ext/autodoc/__init__.py | head -40
1468:                self.doc_as_attr = (self.objpath[-1] != self.object.__name__)
1470:                self.doc_as_attr = True
1569:        if self.doc_as_attr:
1631:        if self.doc_as_attr:
1639:        if not self.doc_as_attr and canonical_fullname and self.fullname != canonical_fullname:
1643:        if not self.doc_as_attr and self.options.show_inheritance:
1677:        if self.doc_as_attr:
1726:        if self.doc_as_attr:
1735:        if self.doc_as_attr:
453:    def check_module(self) -> bool:
454-        """Check if *self.object* is really defined in the module given by
455-        *self.modname*.
456-        """
457-        if self.options.imported_members:
458-            return True
459-
460-        subject = inspect.unpartial(self.object)
461-        modname = self.get_attr(subject, '__module__', None)
462-        if modname and modname != self.modname:
463-            return False
464-        return True
465-
466-    def format_args(self, **kwargs: Any) -> str:
467-        """Format the argument signature of *self.object*.
468-
469-        Should return None if the object does not have a signature.
470-        """
471-        return None
472-
473-    def format_name(self) -> str:
474-        """Format the name of *self.object*.
475-

$ cd /testbed; head -12 .rehearsal/out/index.txt
T
*
file.Bar
   Doc of Bar alias.
   alias of "file.Foo"
file.FileContents
   Doc of contents.

