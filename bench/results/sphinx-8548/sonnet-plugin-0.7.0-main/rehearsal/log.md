$ ls .rehearsal 2>&1; grep -n "attr_docs\|analyzer\|find_attr_docs\|def get_attr_docs\|namespace" sphinx/ext/autodoc/__init__.py | head -80
active
base
fixtures
scaffold
350:        # the module analyzer to get at attribute docs, or None
351:        self.analyzer = None        # type: ModuleAnalyzer
582:        if self.analyzer:
583:            return '%s:docstring of %s' % (self.analyzer.srcname, fullname)
597:        if self.analyzer:
598:            attr_docs = self.analyzer.find_attr_docs()
601:                if key in attr_docs:
605:                    docstrings = [list(attr_docs[key])]
635:        members = get_object_members(self.object, self.objpath, self.get_attr, self.analyzer)
685:        namespace = '.'.join(self.objpath)  # will be empty for modules
687:        if self.analyzer:
688:            attr_docs = self.analyzer.find_attr_docs()
690:            attr_docs = {}
749:            elif (namespace, membername) in attr_docs:
807:        # set current namespace for finding members
853:            if self.analyzer:
854:                # sort by source order, by virtue of the module analyzer
855:                tagorder = self.analyzer.tagorder
895:        # The real module is used in the module analyzer to look up the module
902:        # try to also get a source code analyzer for attribute docs
904:            self.analyzer = ModuleAnalyzer.for_module(self.real_modname)
907:            self.analyzer.find_attr_docs()
909:            logger.debug('[autodoc] module analyzer failed: %s', exc)
911:            self.analyzer = None
916:            self.directive.filename_set.add(self.analyzer.srcname)
921:                analyzer = ModuleAnalyzer.for_module(guess_modname)
922:                self.directive.filename_set.add(analyzer.srcname)
1298:        if (self.analyzer and
1299:                '.'.join(self.objpath) in self.analyzer.overloads and
1322:            for overload in self.analyzer.overloads.get('.'.join(self.objpath)):
1548:                    analyzer = ModuleAnalyzer.for_module(cls.__module__)
1549:                    analyzer.analyze()
1551:                    if qualname in analyzer.overloads:
1552:                        return analyzer.overloads.get(qualname)
1553:                    elif qualname in analyzer.tagorder:
1568:        if self.analyzer and '.'.join(self.objpath) in self.analyzer.finals:

$ sed -n 590,615p sphinx/ext/autodoc/__init__.py; sed -n 680,700p sphinx/ext/autodoc/__init__.py; sed -n 740,760p sphinx/ext/autodoc/__init__.py; sed -n 2150,2185p sphinx/ext/autodoc/__init__.py
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
            if not docstrings:
                # append at least a dummy docstring, so that the event
                # autodoc-process-docstring is fired and can add some
            return False
        ret = []
        # search for members in source code too
        namespace = '.'.join(self.objpath)  # will be empty for modules
        if self.analyzer:
            attr_docs = self.analyzer.find_attr_docs()
        else:
            attr_docs = {}
        # process members and determine which to skip
        for obj in members:
            membername, member = obj
            # if isattr is True, the member is documented as an attribute
            if member is INSTANCEATTR:
                isattr = True
            else:
                isattr = False
                if self.options.special_members and membername in self.options.special_members:

$ ls -R .rehearsal | head -30; cat .rehearsal/REHEARSAL.md 2>/dev/null | head; ls tests/roots/test-ext-autodoc/target | head -40
.rehearsal:
active
base
commands.jsonl
fixtures
log.md
scaffold
trace.offset
written
.rehearsal/fixtures:
.rehearsal/scaffold:
TYPE_CHECKING.py
__init__.py
abstractmethods.py
annotated.py
annotations.py
autoclass_content.py
bound_method.py
cached_property.py
callable.py
classes.py
coroutine.py
cython.pyx
decorator.py
descriptor.py
docstring_signature.py
enums.py
final.py
functions.py
generic_class.py
genericalias.py
imported_members.py
inheritance.py
methods.py
name_conflict
name_mangling.py
need_mocks.py
overload.py
overload2.py
partialfunction.py

$ mkdir -p .rehearsal/scaffold/proj && cd .rehearsal/scaffold/proj && cat > mod.py <<'EOF'
class Base:
    attr1 = 'a'  #: base attr1 doc

    def __init__(self):
        self.attr2 = 1  #: base attr2 doc


class Derived(Base):
    """Derived doc"""
EOF
cat > conf.py <<'EOF'
import os, sys
sys.path.insert(0, os.path.abspath('.'))
extensions = ['sphinx.ext.autodoc']
EOF
cat > index.rst <<'EOF'
t
=

.. autoclass:: mod.Derived
   :members:
   :inherited-members:
EOF
cd /testbed && python3 -m sphinx -q -b text .rehearsal/scaffold/proj .rehearsal/out 2>&1 | tail -5; cat .rehearsal/out/index.txt
Exit code 1
  File "/testbed/sphinx/__main__.py", line 13, in <module>
    from sphinx.cmd.build import main
  File "/testbed/sphinx/cmd/build.py", line 21, in <module>
    from docutils.utils import SystemMessage
ModuleNotFoundError: No module named 'docutils'
cat: .rehearsal/out/index.txt: No such file or directory
  -> RemovedInSphinx40Warning() = None  [sphinx/deprecation.py:22]
  -> RemovedInSphinx50Warning() = None  [sphinx/deprecation.py:26]
  -> RemovedInSphinx60Warning() = None  [sphinx/deprecation.py:30]
  -> _ModuleWrapper() = None  [sphinx/deprecation.py:54]
  -> DeprecatedDict() = <cell>  [sphinx/deprecation.py:95]
  -> <module>() = None  [sphinx/deprecation.py:71]
  -> <module>() = None  [sphinx/__init__.py:62]
  -> <module>() = None  [sphinx/cmd/__init__.py:1]
  -> <module>() raised ModuleNotFoundError: No module named 'docutils'  [sphinx/cmd/build.py:21]
  -> <module>() raised ModuleNotFoundError: No module named 'docutils'  [sphinx/__main__.py:13]

$ cd /testbed; ls -d .venv /opt/*/envs/* 2>&1 | head; conda env list 2>&1 | head; which -a python python3 pytest
Exit code 1
ls: cannot access '.venv': No such file or directory
/opt/miniconda3/envs/testbed
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

$ cd /testbed; P=/opt/miniconda3/envs/testbed/bin/python; $P -m sphinx -q -b text .rehearsal/scaffold/proj .rehearsal/out 2>&1 | tail -5; cat .rehearsal/out/index.txt | tee .rehearsal/fixtures/before.txt
WARNING: while setting up extension sphinx.addnodes: node class 'meta' is already registered, its visitors will be overridden
t
*
class mod.Derived
   Derived doc
  -> is_node_registered(node=<type>) = False  [sphinx/util/docutils.py:101]
  -> register_node(node=<type>) = None  [sphinx/util/docutils.py:112]
  -> SphinxLoggerAdapter.process(msg='[app] adding translation_handlers: %r, %r', kwargs={}) = ['[app] adding translation_handlers: %r, %r', {'extra': <dict>}]  [sphinx/util/logging.py:140]
  -> SphinxLoggerAdapter.log(level=10, msg='[app] adding translation_handlers: %r, %r') = None  [sphinx/util/logging.py:126]
  -> SphinxComponentRegistry.add_translation_handlers(node=<type>) = None  [sphinx/registry.py:310]
  -> Sphinx.add_node(node=<type>, override=False) = None  [sphinx/application.py:584]
  -> SphinxLoggerAdapter.process(msg='[app] adding node: %r', kwargs={}) = ['[app] adding node: %r', {'extra': <dict>}]  [sphinx/util/logging.py:140]
  -> SphinxLoggerAdapter.log(level=10, msg='[app] adding node: %r') = None  [sphinx/util/logging.py:126]
  -> is_node_registered(node=<type>) = False  [sphinx/util/docutils.py:101]
  -> register_node(node=<type>) = None  [sphinx/util/docutils.py:112]

$ cd /testbed; sed -n 700,740p sphinx/ext/autodoc/__init__.py; grep -n "def get_class_members" -A60 sphinx/ext/autodoc/importer.py
            doc = getdoc(member, self.get_attr, self.config.autodoc_inherit_docstrings,
                         self.parent, self.object_name)
            if not isinstance(doc, str):
                # Ignore non-string __doc__
                doc = None
            # if the member __doc__ is the same as self's __doc__, it's just
            # inherited and therefore not the member's doc
            cls = self.get_attr(member, '__class__', None)
            if cls:
                cls_doc = self.get_attr(cls, '__doc__', None)
                if cls_doc == doc:
                    doc = None
            if isinstance(obj, ObjectMember) and obj.docstring:
                # hack for ClassDocumenter to inject docstring via ObjectMember
                doc = obj.docstring
            has_doc = bool(doc)
            metadata = extract_metadata(doc)
            if 'private' in metadata:
                # consider a member private if docstring has "private" metadata
                isprivate = True
            elif 'public' in metadata:
                # consider a member public if docstring has "public" metadata
                isprivate = False
            else:
                isprivate = membername.startswith('_')
            keep = False
            if safe_getattr(member, '__sphinx_mock__', None) is not None:
                # mocked module or object
                pass
            elif self.options.exclude_members and membername in self.options.exclude_members:
                # remove members given by exclude-members
                keep = False
            elif want_all and special_member_re.match(membername):
                # special __methods__
                if self.options.special_members and membername in self.options.special_members:
254:def get_class_members(subject: Any, objpath: List[str], attrgetter: Callable,
255-                      analyzer: ModuleAnalyzer = None) -> Dict[str, ClassAttribute]:
256-    """Get members and attributes of target class."""
257-    from sphinx.ext.autodoc import INSTANCEATTR
258-

$ cd /testbed; sed -n 310,345p sphinx/ext/autodoc/importer.py; sed -n 1580,1600p sphinx/ext/autodoc/__init__.py
    if analyzer:
        # append instance attributes (cf. self.attr1) if analyzer knows
        namespace = '.'.join(objpath)
        for (ns, name), docstring in analyzer.attr_docs.items():
            if namespace == ns and name not in members:
                members[name] = ClassAttribute(subject, name, INSTANCEATTR,
                                               '\n'.join(docstring))
    return members
from sphinx.ext.autodoc.mock import (MockFinder, MockLoader, _MockModule, _MockObject,  # NOQA
                                     mock)
deprecated_alias('sphinx.ext.autodoc.importer',
                 {
                     '_MockModule': _MockModule,
                     '_MockObject': _MockObject,
                     'MockFinder': MockFinder,
                     'MockLoader': MockLoader,
                     'mock': mock,
                 },
                 RemovedInSphinx40Warning,
                 {
                     '_MockModule': 'sphinx.ext.autodoc.mock._MockModule',
                     '_MockObject': 'sphinx.ext.autodoc.mock._MockObject',
                     'MockFinder': 'sphinx.ext.autodoc.mock.MockFinder',
                     'MockLoader': 'sphinx.ext.autodoc.mock.MockLoader',
                     'mock': 'sphinx.ext.autodoc.mock.mock',
                 })
                self.add_line('   ' + _('Bases: %s') % ', '.join(bases), sourcename)
            elif hasattr(self.object, '__bases__') and len(self.object.__bases__):
                # A normal class
                bases = [restify(cls) for cls in self.object.__bases__]
                self.add_line('   ' + _('Bases: %s') % ', '.join(bases), sourcename)
    def get_object_members(self, want_all: bool) -> Tuple[bool, ObjectMembers]:
        members = get_class_members(self.object, self.objpath, self.get_attr, self.analyzer)
        if not want_all:
            if not self.options.members:
                return False, []  # type: ignore
            # specific members given
            selected = []
            for name in self.options.members:  # type: str
                if name in members:

$ cd /testbed; grep -n "^import inspect\|import inspect\|PycodeError\|^import\|^from sphinx.util" sphinx/ext/autodoc/__init__.py | head -40
13:import importlib
14:import re
15:import warnings
23:import sphinx
33:from sphinx.pycode import ModuleAnalyzer, PycodeError
34:from sphinx.util import inspect, logging
35:from sphinx.util.docstrings import extract_metadata, prepare_docstring
36:from sphinx.util.inspect import (evaluate_signature, getdoc, object_description, safe_getattr,
38:from sphinx.util.typing import get_type_hints, restify
39:from sphinx.util.typing import stringify as stringify_typehint
905:            # parse right now, to get PycodeErrors on parsing (results will
908:        except PycodeError as exc:
923:            except PycodeError:
1556:                except PycodeError:
2176:                except (AttributeError, PycodeError):
2178:        except (AttributeError, PycodeError):
2307:                except (AttributeError, PycodeError):

$ cd /testbed; grep -n "^def isclass\|^def getmro\|^from inspect\|^import inspect" sphinx/util/inspect.py; grep -n "inspect.getmro\|inspect.isclass" sphinx/ext/autodoc/__init__.py | head -3
14:import inspect
21:from inspect import Parameter, isclass, ismethod, ismethoddescriptor, ismodule  # NOQA
173:def getmro(obj: Any) -> Tuple["Type", ...]:
244:def isclassmethod(obj: Any) -> bool:
670:            if inspect.isclass(self.object):
1959:        if (inspect.isclassmethod(obj) or
2008:        if inspect.isclassmethod(obj):

$ cd /testbed; P=/opt/miniconda3/envs/testbed/bin/python; $P -m sphinx -q -E -b text .rehearsal/scaffold/proj .rehearsal/out 2>&1 | tail -5; cat .rehearsal/out/index.txt
WARNING: while setting up extension sphinx.addnodes: node class 'meta' is already registered, its visitors will be overridden
t
*
class mod.Derived
   Derived doc
  -> is_node_registered(node=<type>) = False  [sphinx/util/docutils.py:101]
  -> register_node(node=<type>) = None  [sphinx/util/docutils.py:112]
  -> SphinxLoggerAdapter.process(msg='[app] adding translation_handlers: %r, %r', kwargs={}) = ['[app] adding translation_handlers: %r, %r', {'extra': <dict>}]  [sphinx/util/logging.py:140]
  -> SphinxLoggerAdapter.log(level=10, msg='[app] adding translation_handlers: %r, %r') = None  [sphinx/util/logging.py:126]
  -> SphinxComponentRegistry.add_translation_handlers(node=<type>) = None  [sphinx/registry.py:310]
  -> Sphinx.add_node(node=<type>, override=False) = None  [sphinx/application.py:584]
  -> SphinxLoggerAdapter.process(msg='[app] adding node: %r', kwargs={}) = ['[app] adding node: %r', {'extra': <dict>}]  [sphinx/util/logging.py:140]
  -> SphinxLoggerAdapter.log(level=10, msg='[app] adding node: %r') = None  [sphinx/util/logging.py:126]
  -> is_node_registered(node=<type>) = False  [sphinx/util/docutils.py:101]
  -> register_node(node=<type>) = None  [sphinx/util/docutils.py:112]

$ cd /testbed/.rehearsal/scaffold/proj; /opt/miniconda3/envs/testbed/bin/python -c 'from sphinx.pycode import ModuleAnalyzer; a=ModuleAnalyzer.for_module("mod"); a.analyze(); print(dict(a.attr_docs))'
cd /testbed; cat >> .rehearsal/REHEARSAL.md <<'EOF'
### S1: analyzer attr_docs for mod (Base/Derived)
- saw: keys are ('Base','attr1'), ('Base','attr2'); filter_members looks up ('Derived', name) -> miss, so inherited attrs dropped
- fix plan: in filter_members, with inherited_members, merge base-class attr_docs into the Derived namespace
repro: /opt/miniconda3/envs/testbed/bin/python -m sphinx -q -E -b text .rehearsal/scaffold/proj .rehearsal/out
EOF
{('Base', 'attr1'): ['base attr1 doc', ''], ('Base', 'attr2'): ['base attr2 doc', '']}
  -> Token.<genexpr>(.0=<tuple_iterator>) = False  [sphinx/pycode/parser.py:124]
  -> Token.<genexpr>(.0=<tuple_iterator>) = None  [sphinx/pycode/parser.py:124]
  -> Token.match() = False  [sphinx/pycode/parser.py:124]
  -> Token.__eq__(other=5) = False  [sphinx/pycode/parser.py:113]
  -> Token.__eq__(other=6) = False  [sphinx/pycode/parser.py:113]
  -> DefinitionFinder.fetch_token() = None  [sphinx/pycode/parser.py:154]
  -> DefinitionFinder.parse() = None  [sphinx/pycode/parser.py:490]
  -> Parser.parse_definition() = None  [sphinx/pycode/parser.py:576]
  -> Parser.parse() = None  [sphinx/pycode/parser.py:559]
  -> ModuleAnalyzer.analyze() = None  [sphinx/pycode/__init__.py:182]

