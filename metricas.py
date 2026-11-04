from collections import Counter
from pathlib import Path
from lark import Lark

grammar = Path(__file__).with_name("studylang.lark").read_text(encoding="utf-8")
parser = Lark(grammar, parser="lalr", lexer="basic")
rules = parser.rules

# Number of productions
n_productions = len(rules)

# Number of non-terminals and productions per non-terminal
productions_per_symbol = Counter(rule.origin.name for rule in rules)
n_nonterminals = len(productions_per_symbol)

# Number of terminals in the compiled grammar
n_terminals = len(parser.terminals)

# Length of each production's right-hand side
rhs_lengths = [len(rule.expansion) for rule in rules]

# Unitary productions: A -> B, where B is a non-terminal
n_unitary = sum(len(rule.expansion) == 1 and not rule.expansion[0].is_term for rule in rules)

# Directly recursive non-terminals
directly_recursive = {
    rule.origin.name
    for rule in rules
    if any(
        not symbol.is_term and symbol.name == rule.origin.name
        for symbol in rule.expansion
    )
}

print("Terminals:", n_terminals)
print("Non-terminals:", n_nonterminals)
print("Productions:", n_productions)
print("Unitary productions:", n_unitary)
print("Directly recursive non-terminals:", len(directly_recursive))
print("Average RHS length:", sum(rhs_lengths) / len(rhs_lengths))
print("Maximum RHS length:", max(rhs_lengths))
print("Average productions per non-terminal:", sum(productions_per_symbol.values()) / len(productions_per_symbol))
print("Maximum productions per non-terminal:", max(productions_per_symbol.values()))

# Distinct non-terminal dependencies: A -> B
edges = {
    (rule.origin.name, symbol.name)
    for rule in rules
    for symbol in rule.expansion
    if not symbol.is_term
}

nonterminals = {name for name in productions_per_symbol}

in_degree = Counter(b for a, b in edges)
out_degree = Counter(a for a, b in edges)

print("Average in-degree:", sum(in_degree[n] for n in nonterminals) / len(nonterminals))
print("Average out-degree:", sum(out_degree[n] for n in nonterminals) / len(nonterminals))

# Access the generated LALR parse table (Lark internals)
parse_table = parser.parser.parser._parse_table

states = parse_table.states

n_states = len(states)
n_entries = sum(len(actions) for actions in states.values())

print("LALR states:", n_states)
print("Action/goto table entries:", n_entries)