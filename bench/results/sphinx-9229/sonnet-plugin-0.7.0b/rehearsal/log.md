$ ls .rehearsal; grep -n "alias of\|class DataDocumenter\|class GenericAliasMixin\|class TypeVarMixin\|class UninitializedGlobalVariableMixin" sphinx/ext/autodoc/__init__.py
active
fixtures
scaffold
1728:                more_content = StringList([_('alias of %s') % restify(self.object)], source='')
1767:class DataDocumenterMixinBase:
1789:class GenericAliasMixin(DataDocumenterMixinBase):
1801:            more_content.append(_('alias of %s') % restify(self.object), '')
1820:            more_content.append(_('alias of %s') % supertype, '')
1826:class TypeVarMixin(DataDocumenterMixinBase):
1862:            more_content.append(_('alias of TypeVar(%s)') % ", ".join(attrs), '')
1868:class UninitializedGlobalVariableMixin(DataDocumenterMixinBase):
1909:class DataDocumenter(GenericAliasMixin, NewTypeMixin, TypeVarMixin,

$ sed -n 1905,2010p sphinx/ext/autodoc/__init__.py
        else:
            return super().get_doc(ignore)  # type: ignore
class DataDocumenter(GenericAliasMixin, NewTypeMixin, TypeVarMixin,
                     UninitializedGlobalVariableMixin, ModuleLevelDocumenter):
    """
    Specialized Documenter subclass for data items.
    """
    objtype = 'data'
    member_order = 40
    priority = -10
    option_spec: OptionSpec = dict(ModuleLevelDocumenter.option_spec)
    option_spec["annotation"] = annotation_option
    option_spec["no-value"] = bool_option
    @classmethod
    def can_document_member(cls, member: Any, membername: str, isattr: bool, parent: Any
                            ) -> bool:
        return isinstance(parent, ModuleDocumenter) and isattr
    def update_annotations(self, parent: Any) -> None:
        """Update __annotations__ to support type_comment and so on."""
        annotations = dict(inspect.getannotations(parent))
        parent.__annotations__ = annotations
        try:
            analyzer = ModuleAnalyzer.for_module(self.modname)
            analyzer.analyze()
            for (classname, attrname), annotation in analyzer.annotations.items():
                if classname == '' and attrname not in annotations:
                    annotations[attrname] = annotation
        except PycodeError:
            pass
    def import_object(self, raiseerror: bool = False) -> bool:
        ret = super().import_object(raiseerror)
        if self.parent:
            self.update_annotations(self.parent)
        return ret
    def should_suppress_value_header(self) -> bool:
        if super().should_suppress_value_header():
            return True
        else:
            doc = self.get_doc()
            docstring, metadata = separate_metadata('\n'.join(sum(doc, [])))

$ sed -n 2010,2035p sphinx/ext/autodoc/__init__.py; grep -n "update_content\|class AttributeDocumenter" sphinx/ext/autodoc/__init__.py
                    ) -> None:
        # Disable analyzing variable comment on Documenter.add_content() to control it on
        # DataDocumenter.add_content()
        self.analyzer = None
        if not more_content:
            more_content = StringList()
        self.update_content(more_content)
        super().add_content(more_content, no_docstring=no_docstring)
class NewTypeDataDocumenter(DataDocumenter):
    """
    Specialized Documenter subclass for NewTypes.
    Note: This must be invoked before FunctionDocumenter because NewType is a kind of
    function object.
    """
    objtype = 'newtypedata'
    directivetype = 'data'
    priority = FunctionDocumenter.priority + 1
    @classmethod
    def can_document_member(cls, member: Any, membername: str, isattr: bool, parent: Any
1784:    def update_content(self, more_content: StringList) -> None:
1799:    def update_content(self, more_content: StringList) -> None:
1804:        super().update_content(more_content)
1817:    def update_content(self, more_content: StringList) -> None:
1823:        super().update_content(more_content)
1850:    def update_content(self, more_content: StringList) -> None:
1865:        super().update_content(more_content)
2018:        self.update_content(more_content)
2430:class AttributeDocumenter(GenericAliasMixin, NewTypeMixin, SlotsMixin,  # type: ignore
2598:        self.update_content(more_content)

$ mkdir -p .rehearsal/scaffold/p && cd .rehearsal/scaffold/p && cat > file.py <<'EOF'
from pathlib import Path
from typing import Any, Callable, Dict, Union

ScaffoldOpts = Dict[str, Any]
"""Dict doc."""

FileContents = Union[str, None]
"""Union doc."""

FileOp = Callable[[Path, FileContents, ScaffoldOpts], Union[Path, None]]
"""Callable doc."""
EOF
cat > conf.py <<'EOF'
extensions = ['sphinx.ext.autodoc']
EOF
cat > index.rst <<'EOF'
t
=

.. automodule:: file
   :members:
EOF
cd /testbed && python -m sphinx -b text -q .rehearsal/scaffold/p .rehearsal/out && cat .rehearsal/out/index.txt
Exit code 1
Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "/testbed/sphinx/__main__.py", line 13, in <module>
    from sphinx.cmd.build import main
  File "/testbed/sphinx/cmd/build.py", line 21, in <module>
    from docutils.utils import SystemMessage
ModuleNotFoundError: No module named 'docutils'

$ cd /testbed; ls /opt 2>/dev/null; conda env list 2>/dev/null; ls .venv 2>/dev/null; which -a python python3
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

$ cd /testbed; P=/opt/miniconda3/envs/testbed/bin/python; $P -m sphinx -b text -q .rehearsal/scaffold/p .rehearsal/out && cat .rehearsal/out/index.txt
WARNING: autodoc: failed to import module 'file'; the following exception was raised:
No module named 'file'
t
*

$ cd /testbed; cat > .rehearsal/scaffold/p/conf.py <<'EOF'
import os, sys
sys.path.insert(0, os.path.abspath('.'))
extensions = ['sphinx.ext.autodoc']
EOF
P=/opt/miniconda3/envs/testbed/bin/python; $P -m sphinx -b text -q .rehearsal/scaffold/p .rehearsal/out && cat .rehearsal/out/index.txt
t
*
file.FileContents
   Union doc.
   alias of "Optional"["str"]
file.FileOp
   Callable doc.
   alias of "Callable"[["pathlib.Path", "Optional"["str"],
   "Dict"["str", "Any"]], "Optional"["pathlib.Path"]]
file.ScaffoldOpts
   Dict doc.
   alias of "Dict"["str", "Any"]

$ cd /testbed/.rehearsal/scaffold/p && cat > file.py <<'EOF'
from pathlib import Path
from typing import Any, Callable, Dict, Union

# Signatures for the documentation purposes

ScaffoldOpts = Dict[str, Any]
"""Dictionary with PyScaffold's options, see ``pyscaffold.api.create_project``.
Should be treated as immutable (if required, copy before changing).
"""

FileContents = Union[str, None]
"""When the file content is ``None``, the file should not be written to
disk (empty files are represented by an empty string ``""`` as content).
"""

FileOp = Callable[[Path, FileContents, ScaffoldOpts], Union[Path, None]]
"""Signature of functions considered file operations::

    Callable[[Path, FileContents, ScaffoldOpts], Union[Path, None]]

- **path** (:obj:`pathlib.Path`): file path.
"""
EOF
cd /testbed; /opt/miniconda3/envs/testbed/bin/python -m sphinx -b text -q -E .rehearsal/scaffold/p .rehearsal/out && cat .rehearsal/out/index.txt
t
*
file.FileContents
   When the file content is "None", the file should not be written to
   disk (empty files are represented by an empty string """" as
   content).
   alias of "Optional"["str"]
file.FileOp
   Signature of functions considered file operations:
      Callable[[Path, FileContents, ScaffoldOpts], Union[Path, None]]
   * **path** ("pathlib.Path"): file path.
   alias of "Callable"[["pathlib.Path", "Optional"["str"],
   "Dict"["str", "Any"]], "Optional"["pathlib.Path"]]
file.ScaffoldOpts
   Dictionary with PyScaffold's options, see
   "pyscaffold.api.create_project". Should be treated as immutable (if
   required, copy before changing).
   alias of "Dict"["str", "Any"]

$ cd /testbed; cat > .rehearsal/scaffold/p/index.rst <<'EOF'
t
=

.. automodule:: file
   :members:
   :undoc-members:
   :show-inheritance:

.. autodata:: file.FileContents
.. autodata:: file.FileOp
EOF
/opt/miniconda3/envs/testbed/bin/python -m sphinx -b text -q -E .rehearsal/scaffold/p .rehearsal/out && cat .rehearsal/out/index.txt | head -60
/testbed/.rehearsal/scaffold/p/file.py:docstring of file.FileContents:1: WARNING: duplicate object description of file.FileContents, other instance in index, use :noindex: for one of them
/testbed/.rehearsal/scaffold/p/file.py:docstring of file.FileOp:1: WARNING: duplicate object description of file.FileOp, other instance in index, use :noindex: for one of them
t
*
file.FileContents
   When the file content is "None", the file should not be written to
   disk (empty files are represented by an empty string """" as
   content).
   alias of "Optional"["str"]
file.FileOp
   Signature of functions considered file operations:
      Callable[[Path, FileContents, ScaffoldOpts], Union[Path, None]]
   * **path** ("pathlib.Path"): file path.
   alias of "Callable"[["pathlib.Path", "Optional"["str"],
   "Dict"["str", "Any"]], "Optional"["pathlib.Path"]]
file.ScaffoldOpts
   Dictionary with PyScaffold's options, see
   "pyscaffold.api.create_project". Should be treated as immutable (if
   required, copy before changing).
   alias of "Dict"["str", "Any"]
file.FileContents
   When the file content is "None", the file should not be written to
   disk (empty files are represented by an empty string """" as
   content).
   alias of "Optional"["str"]
file.FileOp
   Signature of functions considered file operations:
      Callable[[Path, FileContents, ScaffoldOpts], Union[Path, None]]
   * **path** ("pathlib.Path"): file path.
   alias of "Callable"[["pathlib.Path", "Optional"["str"],
   "Dict"["str", "Any"]], "Optional"["pathlib.Path"]]

$ cd /testbed/.rehearsal/scaffold/p && cat > file.py <<'EOF'
class Foo:
    """Foo class doc."""

Bar = Foo
"""Bar alias doc."""
EOF
cat > index.rst <<'EOF'
t
=

.. automodule:: file
   :members:
   :undoc-members:
EOF
cd /testbed; /opt/miniconda3/envs/testbed/bin/python -m sphinx -b text -q -E .rehearsal/scaffold/p .rehearsal/out && cat .rehearsal/out/index.txt
t
*
file.Bar
   Bar alias doc.
   alias of "file.Foo"
class file.Foo
   Foo class doc.

$ cd /testbed/.rehearsal/scaffold/p && cat > file.py <<'EOF'
from collections import OrderedDict

Bar = OrderedDict
"""Bar alias doc."""
EOF
cd /testbed; /opt/miniconda3/envs/testbed/bin/python -m sphinx -b text -q -E .rehearsal/scaffold/p .rehearsal/out && cat .rehearsal/out/index.txt
t
*
file.Bar
   alias of "collections.OrderedDict"

$ cd /testbed; grep -n "self.analyzer\|def get_doc\|def add_content\|def generate\|doc_as_attr" sphinx/ext/autodoc/__init__.py | sed -n 1,80p
360:        self.analyzer: ModuleAnalyzer = None
552:    def get_doc(self, ignore: int = None) -> Optional[List[List[str]]]:
593:        if self.analyzer:
594:            return '%s:docstring of %s' % (self.analyzer.srcname, fullname)
598:    def add_content(self, more_content: Optional[StringList], no_docstring: bool = False
608:        if self.analyzer:
609:            attr_docs = self.analyzer.find_attr_docs()
650:        members = get_object_members(self.object, self.objpath, self.get_attr, self.analyzer)
704:        if self.analyzer:
705:            attr_docs = self.analyzer.find_attr_docs()
872:            if self.analyzer:
874:                tagorder = self.analyzer.tagorder
890:    def generate(self, more_content: Optional[StringList] = None, real_modname: str = None,
923:            self.analyzer = ModuleAnalyzer.for_module(self.real_modname)
926:            self.analyzer.find_attr_docs()
930:            self.analyzer = None
935:            self.directive.record_dependencies.add(self.analyzer.srcname)
1052:        if self.analyzer:
1053:            attr_docs = self.analyzer.attr_docs
1236:    def get_doc(self, ignore: int = None) -> List[List[str]]:
1319:        if (self.analyzer and
1320:                '.'.join(self.objpath) in self.analyzer.overloads and
1345:            for overload in self.analyzer.overloads.get('.'.join(self.objpath)):
1468:                self.doc_as_attr = (self.objpath[-1] != self.object.__name__)
1470:                self.doc_as_attr = True
1569:        if self.doc_as_attr:
1631:        if self.doc_as_attr:
1635:        if self.analyzer and '.'.join(self.objpath) in self.analyzer.finals:
1639:        if not self.doc_as_attr and canonical_fullname and self.fullname != canonical_fullname:
1643:        if not self.doc_as_attr and self.options.show_inheritance:
1676:    def get_doc(self, ignore: int = None) -> Optional[List[List[str]]]:
1677:        if self.doc_as_attr:
1724:    def add_content(self, more_content: Optional[StringList], no_docstring: bool = False
1726:        if self.doc_as_attr:
1735:        if self.doc_as_attr:
1739:    def generate(self, more_content: Optional[StringList] = None, real_modname: str = None,
1836:    def get_doc(self, ignore: int = None) -> Optional[List[List[str]]]:
1902:    def get_doc(self, ignore: int = None) -> Optional[List[List[str]]]:
2001:    def get_doc(self, ignore: int = None) -> Optional[List[List[str]]]:
2009:    def add_content(self, more_content: Optional[StringList], no_docstring: bool = False

$ cd /testbed; sed -n 596,625p sphinx/ext/autodoc/__init__.py; sed -n 905,935p sphinx/ext/autodoc/__init__.py; sed -n 1674,1690p sphinx/ext/autodoc/__init__.py
            return 'docstring of %s' % fullname
    def add_content(self, more_content: Optional[StringList], no_docstring: bool = False
                    ) -> None:
        """Add content from docstrings, attribute documentation and user."""
        if no_docstring:
            warnings.warn("The 'no_docstring' argument to %s.add_content() is deprecated."
                          % self.__class__.__name__,
                          RemovedInSphinx50Warning, stacklevel=2)
        # set sourcename and add content from attribute documentation
        sourcename = self.get_sourcename()
        if self.analyzer:
            attr_docs = self.analyzer.find_attr_docs()
            if self.objpath:
                key = ('.'.join(self.objpath[:-1]), self.objpath[-1])
                if key in attr_docs:
                    no_docstring = True
                    # make a copy of docstring for attributes to avoid cache
                    # the change of autodoc-process-docstring event.
                    docstrings = [list(attr_docs[key])]
                    for i, line in enumerate(self.process_doc(docstrings)):
                        self.add_line(line, sourcename, i)
        # add content from docstrings
        if not no_docstring:
            docstrings = self.get_doc()
            if docstrings is None:
                # Do not call autodoc-process-docstring on get_doc() returns None.
                   'in the document, or giving an explicit module name)') %
                self.name, type='autodoc')
            return
        # now, import the module and get object to document
        if not self.import_object():
            return
        # If there is no real module defined, figure out which to use.
        # The real module is used in the module analyzer to look up the module
        # where the attribute documentation would actually be found in.
        # This is used for situations where you have a module that collects the
        # functions and classes of internal submodules.
        guess_modname = self.get_real_modname()
        self.real_modname: str = real_modname or guess_modname
        # try to also get a source code analyzer for attribute docs

