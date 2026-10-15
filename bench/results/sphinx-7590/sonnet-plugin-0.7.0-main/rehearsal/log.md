$ ls .rehearsal; grep -n "class ASTNumberLiteral\|class ASTStringLiteral\|class ASTCharLiteral\|def _parse_literal\|_integer_literal_re\|_float_literal_re\|_char_literal_re" sphinx/domains/cpp.py
active
base
fixtures
scaffold
825:class ASTNumberLiteral(ASTLiteral):
841:class ASTStringLiteral(ASTLiteral):
858:class ASTCharLiteral(ASTLiteral):
4646:    def _parse_literal(self) -> ASTLiteral:

$ python3 -c '
from sphinx.domains.cpp import DefinitionParser
from sphinx.config import Config
c=Config()
p=DefinitionParser("constexpr auto planck_constant = 6.62607015e-34q_J * 1q_s",location=None,config=c)
print(p.parse_declaration("member","member"))
'; sed -n 820,880p sphinx/domains/cpp.py; sed -n 4640,4720p sphinx/domains/cpp.py
Traceback (most recent call last):
  File "<string>", line 2, in <module>
  File "/testbed/sphinx/domains/__init__.py", line 16, in <module>
    from docutils import nodes
ModuleNotFoundError: No module named 'docutils'
    def describe_signature(self, signode: TextElement, mode: str,
                           env: "BuildEnvironment", symbol: "Symbol") -> None:
        signode.append(nodes.Text(str(self)))
class ASTNumberLiteral(ASTLiteral):
    def __init__(self, data: str) -> None:
        self.data = data
    def _stringify(self, transform: StringifyTransform) -> str:
        return self.data
    def get_id(self, version: int) -> str:
        return "L%sE" % self.data
    def describe_signature(self, signode: TextElement, mode: str,
                           env: "BuildEnvironment", symbol: "Symbol") -> None:
        txt = str(self)
        signode.append(nodes.Text(txt, txt))
class ASTStringLiteral(ASTLiteral):
    def __init__(self, data: str) -> None:
        self.data = data
    def _stringify(self, transform: StringifyTransform) -> str:
        return self.data
    def get_id(self, version: int) -> str:
        # note: the length is not really correct with escaping
        return "LA%d_KcE" % (len(self.data) - 2)
    def describe_signature(self, signode: TextElement, mode: str,
                           env: "BuildEnvironment", symbol: "Symbol") -> None:
        txt = str(self)
        signode.append(nodes.Text(txt, txt))
class ASTCharLiteral(ASTLiteral):
    def __init__(self, prefix: str, data: str) -> None:
        self.prefix = prefix  # may be None when no prefix
        self.data = data
        assert prefix in _id_char_from_prefix
        self.type = _id_char_from_prefix[prefix]
        decoded = data.encode().decode('unicode-escape')
        if len(decoded) == 1:
            self.value = ord(decoded)
  -> RemovedInSphinx40Warning() = None  [sphinx/deprecation.py:22]
  -> RemovedInSphinx50Warning() = None  [sphinx/deprecation.py:26]
  -> _ModuleWrapper() = None  [sphinx/deprecation.py:45]
  -> DeprecatedDict() = <cell>  [sphinx/deprecation.py:79]
  -> <module>() = None  [sphinx/deprecation.py:55]
  -> <module>() = None  [sphinx/__init__.py:62]
  -> <module>() raised ModuleNotFoundError: No module named 'docutils'  [sphinx/domains/__init__.py:16]

$ ls /opt/*/envs 2>/dev/null; ls -d .venv /opt/* 2>/dev/null; command -v -a python python3 pytest; conda env list 2>/dev/null
testbed
/opt/miniconda3
/bin/bash: line 1: command: -a: invalid option
command: usage: command [-pVv] command [arg ...]
# conda environments:
#
base                     /opt/miniconda3
testbed               *  /opt/miniconda3/envs/testbed

$ /opt/miniconda3/envs/testbed/bin/python -c '
from sphinx.domains.cpp import DefinitionParser
from sphinx.config import Config
c=Config()
p=DefinitionParser("constexpr auto planck_constant = 6.62607015e-34q_J * 1q_s",location=None,config=c)
print(p.parse_declaration("member","member"))
' 2>&1 | tail -8; grep -n "literal_re\|^_identifier_re\|identifier_re =" sphinx/domains/cpp.py | head -30
    attr = self._parse_attribute()
  File "/testbed/sphinx/util/cfamily.py", line 422, in _parse_attribute
    for id in self.id_attributes:
  File "/testbed/sphinx/domains/cpp.py", line 4621, in id_attributes
    return self.config.cpp_id_attributes
  File "/testbed/sphinx/config.py", line 250, in __getattr__
    raise AttributeError(__('No such config value: %s') % name)
AttributeError: No such config value: cpp_id_attributes
36:    identifier_re, anon_identifier_re, integer_literal_re, octal_literal_re,
37:    hex_literal_re, binary_literal_re, float_literal_re,
38:    char_literal_re
4661:        for regex in [float_literal_re, binary_literal_re, hex_literal_re,
4662:                      integer_literal_re, octal_literal_re]:
4674:        if self.match(char_literal_re):
  -> _TranslationProxy.data() = 'No such config value: %s'  [sphinx/locale/__init__.py:47]
  -> _TranslationProxy.__mod__(other='cpp_id_attributes') = 'No such config value: cpp_id_attributes'  [sphinx/locale/__init__.py:74]
  -> Config.__getattr__(name='cpp_id_attributes') raised AttributeError: No such config value: cpp_id_attributes  [sphinx/config.py:250]
  -> DefinitionParser.id_attributes() raised AttributeError: No such config value: cpp_id_attributes  [sphinx/domains/cpp.py:4621]
  -> DefinitionParser._parse_attribute() raised AttributeError: No such config value: cpp_id_attributes  [sphinx/util/cfamily.py:422]
  -> DefinitionParser._parse_decl_specs_simple(outer='member', typed=True) raised AttributeError: No such config value: cpp_id_attributes  [sphinx/domains/cpp.py:5624]
  -> DefinitionParser._parse_decl_specs(outer='member', typed=True) raised AttributeError: No such config value: cpp_id_attributes  [sphinx/domains/cpp.py:5650]
  -> DefinitionParser._parse_type(named=True, outer='member') raised AttributeError: No such config value: cpp_id_attributes  [sphinx/domains/cpp.py:5960]
  -> DefinitionParser._parse_type_with_init(named=True, outer='member') raised AttributeError: No such config value: cpp_id_attributes  [sphinx/domains/cpp.py:5969]
  -> DefinitionParser.parse_declaration(objectType='member', directiveType='member') raised AttributeError: No such config value: cpp_id_attributes  [sphinx/domains/cpp.py:6301]

$ /opt/miniconda3/envs/testbed/bin/python -c '
from sphinx.domains.cpp import DefinitionParser, CPPDomain
from sphinx.config import Config
c=Config()
CPPDomain.get_name
c.add("cpp_id_attributes",[],"env",())
c.add("cpp_paren_attributes",[],"env",())
p=DefinitionParser("constexpr auto planck_constant = 6.62607015e-34q_J * 1q_s",location=None,config=c)
print(p.parse_declaration("member","member"))
' 2>&1 | tail -5
Traceback (most recent call last):
  File "<string>", line 5, in <module>
AttributeError: type object 'CPPDomain' has no attribute 'get_name'
  -> Symbol.__setattr__(key='docname', value=None) = None  [sphinx/domains/cpp.py:3669]
  -> Symbol.__setattr__(key='isRedeclaration', value=False) = None  [sphinx/domains/cpp.py:3669]
  -> Symbol._assert_invariants() = None  [sphinx/domains/cpp.py:3660]
  -> Symbol.__setattr__(key='_children', value=[]) = None  [sphinx/domains/cpp.py:3669]
  -> Symbol.__setattr__(key='_anonChildren', value=[]) = None  [sphinx/domains/cpp.py:3669]
  -> Symbol._add_template_and_function_params() = None  [sphinx/domains/cpp.py:3744]
  -> Symbol.__init__(parent=None, identOrOp=None, templateParams=None, templateArgs=None, declaration=None) = None  [sphinx/domains/cpp.py:3696]
  -> CPPDomain() = None  [sphinx/domains/cpp.py:7262]
  -> <module>() = None  [sphinx/domains/cpp.py:7276]
  -> Config.__init__(config={}, overrides={}) = None  [sphinx/config.py:168]

$ /opt/miniconda3/envs/testbed/bin/python -c '
from sphinx.domains.cpp import DefinitionParser
from sphinx.config import Config
c=Config()
c.add("cpp_id_attributes",[],"env",())
c.add("cpp_paren_attributes",[],"env",())
p=DefinitionParser("constexpr auto planck_constant = 6.62607015e-34q_J * 1q_s",location=None,config=c)
print(p.parse_declaration("member","member"))
' 2>&1 | tail -6; grep -n "_re = \|def _parse_string" -A2 sphinx/util/cfamily.py | sed -n 1,60p
constexpr auto planck_constant = 6.62607015e-34
30:_whitespace_re = re.compile(r'(?u)\s+')
31:anon_identifier_re = re.compile(r'(@[a-zA-Z0-9_])[a-zA-Z0-9_]*\b')
32:identifier_re = re.compile(r'''(?x)
33-    (   # This 'extends' _anon_identifier_re with the ordinary identifiers,
34-        # make sure they are in sync.
--
40:integer_literal_re = re.compile(r'[1-9][0-9]*')
41:octal_literal_re = re.compile(r'0[0-7]*')
42:hex_literal_re = re.compile(r'0[xX][0-9a-fA-F][0-9a-fA-F]*')
43:binary_literal_re = re.compile(r'0[bB][01][01]*')
44:float_literal_re = re.compile(r'''(?x)
45-    [+-]?(
46-    # decimal
--
56:char_literal_re = re.compile(r'''(?x)
57-    ((?:u8)|u|U|L)?
58-    '(
  -> DefinitionParser._parse_initializer_list(name='braced-init-list', open='{', close='}') = [None, None]  [sphinx/domains/cpp.py:4779]
  -> DefinitionParser._parse_braced_init_list() = None  [sphinx/domains/cpp.py:4828]
  -> DefinitionParser.match(regex=<Pattern>) = False  [sphinx/util/cfamily.py:291]
  -> DefinitionParser.skip_ws() = False  [sphinx/util/cfamily.py:304]
  -> DefinitionParser.skip_string(string='(') = False  [sphinx/util/cfamily.py:298]
  -> DefinitionParser.match(regex=<Pattern>) = False  [sphinx/util/cfamily.py:291]
  -> DefinitionParser.skip_ws() = False  [sphinx/util/cfamily.py:304]
  -> DefinitionParser.skip_string(string='++') = False  [sphinx/util/cfamily.py:298]
  -> DefinitionParser.skip_string(string='--') = False  [sphinx/util/cfamily.py:298]
  -> DefinitionParser.skip_string(string='*') = False  [sphinx/util/cfamily.py:298]

$ cat >> .rehearsal/REHEARSAL.md <<'EOF'
### S1: parse the report's declaration
- cmd: testbed python, DefinitionParser("constexpr auto planck_constant = 6.62607015e-34q_J * 1q_s").parse_declaration
- saw: output `constexpr auto planck_constant = 6.62607015e-34` -- literal stops before `q_J`, rest unparsed
- means: _parse_literal has `# TODO: user-defined lit`; number/string/char literals never take a ud-suffix
repro: /opt/miniconda3/envs/testbed/bin/python -c 'from sphinx.domains.cpp import DefinitionParser; from sphinx.config import Config; c=Config(); c.add("cpp_id_attributes",[],"env",()); c.add("cpp_paren_attributes",[],"env",()); p=DefinitionParser("constexpr auto planck_constant = 6.62607015e-34q_J * 1q_s",location=None,config=c); print(p.parse_declaration("member","member")); p.assert_end()'
EOF
grep -n "ASTPointerLiteral\|_id_char_from_prefix" sphinx/domains/cpp.py | head; grep -n "Literal" doc/usage/restructuredtext/domains.rst CHANGES | head
518:_id_char_from_prefix = {
792:class ASTPointerLiteral(ASTLiteral):
862:        assert prefix in _id_char_from_prefix
863:        self.type = _id_char_from_prefix[prefix]
4656:            return ASTPointerLiteral()
CHANGES:776:* ``sphinx.directives.LiteralInclude``
CHANGES:1032:* ``sphinx.domains.cpp.UnsupportedMultiCharacterCharLiteral.decoded``

