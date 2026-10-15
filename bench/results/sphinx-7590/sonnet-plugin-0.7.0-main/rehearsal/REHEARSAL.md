### S1: parse the report's declaration
- cmd: testbed python, DefinitionParser("constexpr auto planck_constant = 6.62607015e-34q_J * 1q_s").parse_declaration
- saw: output `constexpr auto planck_constant = 6.62607015e-34` -- literal stops before `q_J`, rest unparsed
- means: _parse_literal has `# TODO: user-defined lit`; number/string/char literals never take a ud-suffix
repro: /opt/miniconda3/envs/testbed/bin/python -c 'from sphinx.domains.cpp import DefinitionParser; from sphinx.config import Config; c=Config(); c.add("cpp_id_attributes",[],"env",()); c.add("cpp_paren_attributes",[],"env",()); p=DefinitionParser("constexpr auto planck_constant = 6.62607015e-34q_J * 1q_s",location=None,config=c); print(p.parse_declaration("member","member")); p.assert_end()'
