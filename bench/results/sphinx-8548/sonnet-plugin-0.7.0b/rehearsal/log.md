$ ls .rehearsal 2>&1; grep -n "inherited_members\|attr_docs\|def get_attribute_comment\|analyzer" sphinx/ext/autodoc/__init__.py | head -80
active
fixtures
scaffold
119:def inherited_members_option(arg: Any) -> Union[object, Set[str]]:
350:        # the module analyzer to get at attribute docs, or None
351:        self.analyzer = None        # type: ModuleAnalyzer
582:        if self.analyzer:
583:            return '%s:docstring of %s' % (self.analyzer.srcname, fullname)
597:        if self.analyzer:
598:            attr_docs = self.analyzer.find_attr_docs()
601:                if key in attr_docs:
605:                    docstrings = [list(attr_docs[key])]
635:        members = get_object_members(self.object, self.objpath, self.get_attr, self.analyzer)
648:        elif self.options.inherited_members:
672:                    if cls.__name__ == self.options.inherited_members and cls != self.object:
687:        if self.analyzer:
688:            attr_docs = self.analyzer.find_attr_docs()
690:            attr_docs = {}
749:            elif (namespace, membername) in attr_docs:
812:        want_all = all_members or self.options.inherited_members or \
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
970:        'noindex': bool_option, 'inherited-members': inherited_members_option,
1298:        if (self.analyzer and
1299:                '.'.join(self.objpath) in self.analyzer.overloads and
1322:            for overload in self.analyzer.overloads.get('.'.join(self.objpath)):
1394:        'noindex': bool_option, 'inherited-members': inherited_members_option,
1548:                    analyzer = ModuleAnalyzer.for_module(cls.__module__)
1549:                    analyzer.analyze()
1551:                    if qualname in analyzer.overloads:

$ mkdir -p .rehearsal/scaffold/docs && cd .rehearsal/scaffold && cat > target.py <<'EOF'
class Base:
    #: base attr doc
    attr = 1

class Derived(Base):
    pass
EOF
cat > docs/conf.py <<'EOF'
import sys, os
sys.path.insert(0, os.path.abspath('..'))
extensions = ['sphinx.ext.autodoc']
EOF
cat > docs/index.rst <<'EOF'
t
=

.. autoclass:: target.Derived
   :members:
   :inherited-members:
EOF
cd /testbed && python -m sphinx -q -b text .rehearsal/scaffold/docs .rehearsal/scaffold/out 2>&1 | tail -5; cat .rehearsal/scaffold/out/index.txt | tee .rehearsal/fixtures/before.txt; sed -n 590,615p sphinx/ext/autodoc/__init__.py; sed -n 740,760p sphinx/ext/autodoc/__init__.py
  File "/testbed/sphinx/__main__.py", line 13, in <module>
    from sphinx.cmd.build import main
  File "/testbed/sphinx/cmd/build.py", line 21, in <module>
    from docutils.utils import SystemMessage
ModuleNotFoundError: No module named 'docutils'
cat: .rehearsal/scaffold/out/index.txt: No such file or directory
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
                if self.options.special_members and membername in self.options.special_members:
                    if membername == '__doc__':
                        keep = False
                    elif is_filtered_inherited_member(membername):
                        keep = False
                    else:
                        keep = has_doc or self.options.undoc_members
                else:
                    keep = False
            elif (namespace, membername) in attr_docs:
                if want_all and isprivate:

$ cd /testbed; ls /opt/*/envs 2>&1; conda env list 2>&1 | head; ls .venv 2>&1 | head -3; which -a python python3
testbed
# conda environments:
#
base                     /opt/miniconda3
testbed               *  /opt/miniconda3/envs/testbed
ls: cannot access '.venv': No such file or directory
/opt/miniconda3/bin/python
/usr/bin/python
/bin/python
/opt/miniconda3/bin/python3
/usr/bin/python3
/bin/python3

$ cd /testbed; P=/opt/miniconda3/envs/testbed/bin/python; $P -m sphinx -q -b text .rehearsal/scaffold/docs .rehearsal/scaffold/out 2>&1 | tail -5; cat .rehearsal/scaffold/out/index.txt | tee .rehearsal/fixtures/before.txt
WARNING: while setting up extension sphinx.addnodes: node class 'meta' is already registered, its visitors will be overridden
t
*
class target.Derived

$ cd /testbed; sed -n 683,740p sphinx/ext/autodoc/__init__.py; grep -n "class ObjectMember" -A12 sphinx/ext/autodoc/importer.py; grep -n "def get_class_members" -A60 sphinx/ext/autodoc/importer.py
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

$ cd /testbed; sed -n 640,682p sphinx/ext/autodoc/__init__.py; sed -n 760,800p sphinx/ext/autodoc/__init__.py; sed -n 308,330p sphinx/ext/autodoc/importer.py
            selected = []
            for name in self.options.members:  # type: str
                if name in members:
                    selected.append((name, members[name].value))
                else:
                    logger.warning(__('missing attribute %s in object %s') %
                                   (name, self.fullname), type='autodoc')
            return False, selected
        elif self.options.inherited_members:
            return False, [(m.name, m.value) for m in members.values()]
        else:
            return False, [(m.name, m.value) for m in members.values()
                           if m.directly_defined]
    def filter_members(self, members: ObjectMembers, want_all: bool
                       ) -> List[Tuple[str, Any, bool]]:
        """Filter the given member list.
        Members are skipped if
        - they are private (except if given explicitly or the private-members
          option is set)
        - they are special methods (except if given explicitly or the
          special-members option is set)
        - they are undocumented (except if the undoc-members option is set)
        The user can override the skipping decision by connecting to the
        ``autodoc-skip-member`` event.
        """
        def is_filtered_inherited_member(name: str) -> bool:
            if inspect.isclass(self.object):
                for cls in self.object.__mro__:
                    if cls.__name__ == self.options.inherited_members and cls != self.object:
                        # given member is a member of specified *super class*
                        return True
                    elif name in cls.__dict__:
                        return False
                    elif name in self.get_attr(cls, '__annotations__', {}):
                        return False
            return False
        ret = []
                if has_doc or self.options.undoc_members:
                    if self.options.private_members is None:
                        keep = False

$ cd /testbed; grep -n "ClassAttribute\b" -B2 -A12 sphinx/ext/autodoc/importer.py | sed -n 1,40p; grep -n "^from\|^import" sphinx/ext/autodoc/importer.py
242-
243-
244:class ClassAttribute:
245-    """The attribute of the class."""
246-
247-    def __init__(self, cls: Any, name: str, value: Any, docstring: Optional[str] = None):
248-        self.class_ = cls
249-        self.name = name
250-        self.value = value
251-        self.docstring = docstring
252-
253-
254-def get_class_members(subject: Any, objpath: List[str], attrgetter: Callable,
255:                      analyzer: ModuleAnalyzer = None) -> Dict[str, ClassAttribute]:
256-    """Get members and attributes of target class."""
257-    from sphinx.ext.autodoc import INSTANCEATTR
258-
259-    # the members directly defined in the class
260-    obj_dict = attrgetter(subject, '__dict__', {})
261-
262:    members = {}  # type: Dict[str, ClassAttribute]
263-
264-    # enum members
265-    if isenumclass(subject):
266-        for name, value in subject.__members__.items():
267-            if name not in members:
268:                members[name] = ClassAttribute(subject, name, value)
269-
270-        superclass = subject.__mro__[1]
271-        for name in obj_dict:
272-            if name not in superclass.__dict__:
273-                value = safe_getattr(subject, name)
274:                members[name] = ClassAttribute(subject, name, value)
275-
276-    # members in __slots__
277-    try:
278-        __slots__ = getslots(subject)
279-        if __slots__:
280-            from sphinx.ext.autodoc import SLOTSATTR
281-

