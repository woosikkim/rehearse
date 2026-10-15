$ ls .rehearsal 2>&1; grep -n "isproperty\|def isattributedescriptor\|class PropertyDocumenter" -r sphinx/util/inspect.py sphinx/ext/autodoc/__init__.py | head -30
active
base
fixtures
scaffold
sphinx/util/inspect.py:298:def isattributedescriptor(obj: Any) -> bool:
sphinx/util/inspect.py:386:def isproperty(obj: Any) -> bool:
sphinx/ext/autodoc/__init__.py:2651:class PropertyDocumenter(DocstringStripSignatureMixin, ClassLevelDocumenter):  # type: ignore
sphinx/ext/autodoc/__init__.py:2664:        return inspect.isproperty(member) and isinstance(parent, ClassDocumenter)

$ python3 --version; sed -n 380,395p sphinx/util/inspect.py; sed -n 2645,2720p sphinx/ext/autodoc/__init__.py
Python 3.11.5
        # objects (see https://github.com/sphinx-doc/sphinx/issues/6605)
        return True
    else:
        return False
def isproperty(obj: Any) -> bool:
    """Check if the object is property."""
    if sys.version_info >= (3, 8):
        from functools import cached_property  # cached_property is available since py3.8
        if isinstance(obj, cached_property):
            return True
    return isinstance(obj, property)
        if more_content is None:
            more_content = StringList()
        self.update_content(more_content)
        super().add_content(more_content, no_docstring)
class PropertyDocumenter(DocstringStripSignatureMixin, ClassLevelDocumenter):  # type: ignore
    """
    Specialized Documenter subclass for properties.
    """
    objtype = 'property'
    member_order = 60
    # before AttributeDocumenter
    priority = AttributeDocumenter.priority + 1
    @classmethod
    def can_document_member(cls, member: Any, membername: str, isattr: bool, parent: Any
                            ) -> bool:
        return inspect.isproperty(member) and isinstance(parent, ClassDocumenter)
    def document_members(self, all_members: bool = False) -> None:
        pass
    def get_real_modname(self) -> str:
        real_modname = self.get_attr(self.parent or self.object, '__module__', None)
        return real_modname or self.modname
    def add_directive_header(self, sig: str) -> None:
        super().add_directive_header(sig)
        sourcename = self.get_sourcename()
        if inspect.isabstractmethod(self.object):
            self.add_line('   :abstractmethod:', sourcename)
        if safe_getattr(self.object, 'fget', None) and self.config.autodoc_typehints != 'none':
            try:

$ mkdir -p .rehearsal/scaffold/docs && cat > .rehearsal/scaffold/docs/conf.py <<'EOF'
import os, sys
sys.path.insert(0, os.path.abspath('..'))
extensions = ['sphinx.ext.autodoc']
EOF
cat > .rehearsal/scaffold/mod.py <<'EOF'
class A:
    """A."""

    @classmethod
    @property
    def f(cls):
        """Some class property."""
        return "property"

    @property
    def g(self):
        """Regular property."""
        return 1
EOF
cat > .rehearsal/scaffold/docs/index.rst <<'EOF'
T
=

.. autoclass:: mod.A
   :members:
EOF
cat > .rehearsal/REHEARSAL.md <<'EOF'
# Rehearsal: autodoc @classmethod @property
repro: python3 -m sphinx -b text -q .rehearsal/scaffold/docs .rehearsal/out
EOF
python3 -m sphinx -b text -q .rehearsal/scaffold/docs .rehearsal/out; cat .rehearsal/out/index.txt
Exit code 1
Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "/testbed/sphinx/__main__.py", line 13, in <module>
    from sphinx.cmd.build import main
  File "/testbed/sphinx/cmd/build.py", line 21, in <module>
    from docutils.utils import SystemMessage
ModuleNotFoundError: No module named 'docutils'
cat: .rehearsal/out/index.txt: No such file or directory
  -> RemovedInSphinx50Warning() = None  [sphinx/deprecation.py:18]
  -> RemovedInSphinx60Warning() = None  [sphinx/deprecation.py:22]
  -> _ModuleWrapper() = None  [sphinx/deprecation.py:46]
  -> DeprecatedDict() = <cell>  [sphinx/deprecation.py:87]
  -> <module>() = None  [sphinx/deprecation.py:63]
  -> <module>() = None  [sphinx/__init__.py:57]
  -> <module>() = None  [sphinx/cmd/__init__.py:1]
  -> <module>() raised ModuleNotFoundError: No module named 'docutils'  [sphinx/cmd/build.py:21]
  -> <module>() raised ModuleNotFoundError: No module named 'docutils'  [sphinx/__main__.py:13]

$ ls -d /opt/*/envs/* .venv 2>&1 | head; command -v -a python python3; conda env list 2>&1 | head
ls: cannot access '.venv': No such file or directory
/opt/miniconda3/envs/testbed
/bin/bash: line 1: command: -a: invalid option
command: usage: command [-pVv] command [arg ...]
# conda environments:
#
base                     /opt/miniconda3
testbed               *  /opt/miniconda3/envs/testbed

$ P=/opt/miniconda3/envs/testbed/bin/python; $P --version; $P -m sphinx -b text -q .rehearsal/scaffold/docs .rehearsal/out; cat .rehearsal/out/index.txt
Python 3.9.20
T
*
class mod.A
   property g
      Regular property.
  -> SphinxLoggerAdapter.log(level=10, msg='[app] setting up extension: %r') = None  [sphinx/util/logging.py:123]
  -> is_translator_registered(catalog='sphinx', namespace='console') = True  [sphinx/locale/__init__.py:191]
  -> get_translator(catalog='sphinx', namespace='console') = <NullTranslations>  [sphinx/locale/__init__.py:187]
  -> gettext(message='while setting up extension %s:') = 'while setting up extension %s:'  [sphinx/locale/__init__.py:234]
  -> MessagePrefixFilter.__init__(prefix='while setting up extension sphinx.builders.changes:') = None  [sphinx/util/logging.py:441]
  -> prefixed_warnings(prefix='while setting up extension sphinx.builders.changes:') = None  [sphinx/util/logging.py:326]
  -> _ModuleWrapper.__getattr__(name='__spec__') = <ModuleSpec>  [sphinx/deprecation.py:48]
  -> _ModuleWrapper.__getattr__(name='__path__') raised AttributeError: module 'sphinx.util.typing' has no attribute '__path__'  [sphinx/deprecation.py:48]
  -> _ModuleWrapper.__getattr__(name='OptionSpec') = <_GenericAlias>  [sphinx/deprecation.py:48]
  -> is_translator_registered(catalog='sphinx', namespace='general') = True  [sphinx/locale/__init__.py:191]

$ grep -n "def get_class_members" -A60 sphinx/ext/autodoc/importer.py | head -90; grep -n "def isclassmethod\|def isstaticmethod" -A22 sphinx/util/inspect.py | head -60
240:def get_class_members(subject: Any, objpath: List[str], attrgetter: Callable
241-                      ) -> Dict[str, "ObjectMember"]:
242-    """Get members and attributes of target class."""
243-    from sphinx.ext.autodoc import INSTANCEATTR, ObjectMember
244-
245-    # the members directly defined in the class
246-    obj_dict = attrgetter(subject, '__dict__', {})
247-
248-    members: Dict[str, ObjectMember] = {}
249-
250-    # enum members
251-    if isenumclass(subject):
252-        for name, value in subject.__members__.items():
253-            if name not in members:
254-                members[name] = ObjectMember(name, value, class_=subject)
255-
256-        superclass = subject.__mro__[1]
257-        for name in obj_dict:
258-            if name not in superclass.__dict__:
259-                value = safe_getattr(subject, name)
260-                members[name] = ObjectMember(name, value, class_=subject)
261-
262-    # members in __slots__
263-    try:
264-        __slots__ = getslots(subject)
265-        if __slots__:
266-            from sphinx.ext.autodoc import SLOTSATTR
267-
268-            for name, docstring in __slots__.items():
269-                members[name] = ObjectMember(name, SLOTSATTR, class_=subject,
270-                                             docstring=docstring)
271-    except (TypeError, ValueError):
272-        pass
273-
274-    # other members
275-    for name in dir(subject):
276-        try:
277-            value = attrgetter(subject, name)
278-            if ismock(value):
279-                value = undecorate(value)

$ grep -n "class PyProperty" -A45 sphinx/domains/python.py; grep -n "classmethod" sphinx/domains/python.py | head -20
849:class PyProperty(PyObject):
850-    """Description of an attribute."""
851-
852-    option_spec = PyObject.option_spec.copy()
853-    option_spec.update({
854-        'abstractmethod': directives.flag,
855-        'type': directives.unchanged,
856-    })
857-
858-    def handle_signature(self, sig: str, signode: desc_signature) -> Tuple[str, str]:
859-        fullname, prefix = super().handle_signature(sig, signode)
860-
861-        typ = self.options.get('type')
862-        if typ:
863-            signode += addnodes.desc_annotation(typ, ': ' + typ)
864-
865-        return fullname, prefix
866-
867-    def get_signature_prefix(self, sig: str) -> str:
868-        prefix = ['property']
869-        if 'abstractmethod' in self.options:
870-            prefix.insert(0, 'abstract')
871-
872-        return ' '.join(prefix) + ' '
873-
874-    def get_index_text(self, modname: str, name_cls: Tuple[str, str]) -> str:
875-        name, cls = name_cls
876-        try:
877-            clsname, attrname = name.rsplit('.', 1)
878-            if modname and self.env.config.add_module_names:
879-                clsname = '.'.join([modname, clsname])
880-        except ValueError:
881-            if modname:
882-                return _('%s (in module %s)') % (name, modname)
883-            else:
884-                return name
885-
886-        return _('%s (%s property)') % (attrname, clsname)
887-
888-

