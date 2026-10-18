"""Simplificacion y conversion de una CFG a Forma Normal de Chomsky."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

from .grammar import Grammar


@dataclass(frozen=True)
class CNFConversion:
    """Resultado de convertir una gramatica a CNF."""

    grammar: Grammar
    helper_symbols: frozenset[str]
    original_productions: int
    simplified_productions: int


def nullable_symbols(grammar: Grammar) -> frozenset[str]:
    nullable = {
        lhs for lhs, alternatives in grammar.productions.items() if () in alternatives
    }
    changed = True
    while changed:
        changed = False
        for lhs, alternatives in grammar.productions.items():
            if lhs in nullable:
                continue
            if any(rhs and all(symbol in nullable for symbol in rhs) for rhs in alternatives):
                nullable.add(lhs)
                changed = True
                break
    return frozenset(nullable)


def eliminate_epsilon(grammar: Grammar) -> Grammar:
    """Elimina producciones epsilon; conserva S -> epsilon cuando corresponde."""

    nullable = nullable_symbols(grammar)
    result: dict[str, set[tuple[str, ...]]] = {
        lhs: set() for lhs in grammar.nonterminals
    }

    for lhs, alternatives in grammar.productions.items():
        for rhs in alternatives:
            if not rhs:
                continue
            nullable_positions = [
                index for index, symbol in enumerate(rhs) if symbol in nullable
            ]
            for amount in range(len(nullable_positions) + 1):
                for omitted in combinations(nullable_positions, amount):
                    omitted_set = set(omitted)
                    candidate = tuple(
                        symbol for index, symbol in enumerate(rhs) if index not in omitted_set
                    )
                    if candidate or lhs == grammar.start:
                        result[lhs].add(candidate)

    if grammar.start in nullable:
        result[grammar.start].add(())
    return Grammar(grammar.start, result)


def eliminate_unit(grammar: Grammar) -> Grammar:
    """Elimina producciones unitarias de la forma A -> B."""

    nts = grammar.nonterminals
    result: dict[str, set[tuple[str, ...]]] = {lhs: set() for lhs in nts}

    for origin in nts:
        closure = {origin}
        pending = [origin]
        while pending:
            current = pending.pop()
            for rhs in grammar.productions[current]:
                if len(rhs) == 1 and rhs[0] in nts and rhs[0] not in closure:
                    closure.add(rhs[0])
                    pending.append(rhs[0])
        for reachable in closure:
            for rhs in grammar.productions[reachable]:
                if not (len(rhs) == 1 and rhs[0] in nts):
                    result[origin].add(rhs)

    return Grammar(grammar.start, result)


def remove_useless(grammar: Grammar) -> Grammar:
    """Quita simbolos no generadores y luego simbolos inalcanzables."""

    nts = grammar.nonterminals
    generating: set[str] = set()
    changed = True
    while changed:
        changed = False
        for lhs, alternatives in grammar.productions.items():
            if lhs in generating:
                continue
            if any(
                all(symbol not in nts or symbol in generating for symbol in rhs)
                for rhs in alternatives
            ):
                generating.add(lhs)
                changed = True

    if grammar.start not in generating:
        return Grammar(grammar.start, {grammar.start: frozenset()})

    useful_rules: dict[str, set[tuple[str, ...]]] = {
        lhs: {
            rhs
            for rhs in alternatives
            if all(symbol not in nts or symbol in generating for symbol in rhs)
        }
        for lhs, alternatives in grammar.productions.items()
        if lhs in generating
    }

    reachable = {grammar.start}
    pending = [grammar.start]
    while pending:
        lhs = pending.pop()
        for rhs in useful_rules.get(lhs, set()):
            for symbol in rhs:
                if symbol in useful_rules and symbol not in reachable:
                    reachable.add(symbol)
                    pending.append(symbol)

    return Grammar(
        grammar.start,
        {lhs: useful_rules[lhs] for lhs in reachable},
    )


def simplify(grammar: Grammar) -> Grammar:
    """Aplica las tres etapas clasicas de simplificacion de una CFG."""

    return remove_useless(eliminate_unit(eliminate_epsilon(grammar)))


def to_cnf(grammar: Grammar) -> CNFConversion:
    """Convierte una CFG a Forma Normal de Chomsky.

    El lenguaje se preserva, incluyendo epsilon solamente para el simbolo
    inicial. Los simbolos auxiliares creados se reportan para poder ocultarlos
    al imprimir el arbol sintactico.
    """

    original_count = grammar.production_count
    helper_symbols: set[str] = set()
    working = grammar

    appears_on_rhs = any(
        grammar.start in rhs
        for alternatives in grammar.productions.values()
        for rhs in alternatives
    )
    # Solo hace falta un inicio nuevo cuando el inicio original es anulable y
    # tambien aparece a la derecha. En los demas casos conservar su nombre
    # produce arboles mas claros sin violar CNF.
    if grammar.start in nullable_symbols(grammar) and appears_on_rhs:
        new_start = _fresh_symbol(f"{grammar.start}_START", grammar.nonterminals)
        productions = {
            lhs: set(alternatives)
            for lhs, alternatives in grammar.productions.items()
        }
        productions[new_start] = {(grammar.start,)}
        working = Grammar(new_start, productions)

    working = simplify(working)
    simplified_count = working.production_count
    occupied = set(working.nonterminals) | set(working.terminals)
    terminal_helpers: dict[str, str] = {}
    replaced: dict[str, set[tuple[str, ...]]] = {
        lhs: set() for lhs in working.nonterminals
    }

    for lhs, alternatives in working.productions.items():
        for rhs in alternatives:
            if len(rhs) < 2:
                replaced[lhs].add(rhs)
                continue
            new_rhs: list[str] = []
            for symbol in rhs:
                if symbol in working.nonterminals:
                    new_rhs.append(symbol)
                    continue
                helper = terminal_helpers.get(symbol)
                if helper is None:
                    helper = _fresh_symbol("_T", occupied)
                    occupied.add(helper)
                    helper_symbols.add(helper)
                    terminal_helpers[symbol] = helper
                    replaced[helper] = {(symbol,)}
                new_rhs.append(helper)
            replaced[lhs].add(tuple(new_rhs))

    binarized: dict[str, set[tuple[str, ...]]] = {
        lhs: set() for lhs in replaced
    }
    for lhs, alternatives in replaced.items():
        for rhs in alternatives:
            if len(rhs) <= 2:
                binarized[lhs].add(rhs)
                continue
            current_lhs = lhs
            for index in range(len(rhs) - 2):
                helper = _fresh_symbol("_B", occupied)
                occupied.add(helper)
                helper_symbols.add(helper)
                binarized.setdefault(current_lhs, set()).add((rhs[index], helper))
                binarized.setdefault(helper, set())
                current_lhs = helper
            binarized[current_lhs].add((rhs[-2], rhs[-1]))

    cnf = remove_useless(Grammar(working.start, binarized))
    if not is_cnf(cnf):
        raise RuntimeError("Error interno: la conversion no produjo una gramatica CNF.")
    return CNFConversion(
        grammar=cnf,
        helper_symbols=frozenset(helper_symbols & cnf.nonterminals),
        original_productions=original_count,
        simplified_productions=simplified_count,
    )


def is_cnf(grammar: Grammar) -> bool:
    """Comprueba las restricciones de la Forma Normal de Chomsky."""

    nts = grammar.nonterminals
    start_on_rhs = any(
        grammar.start in rhs
        for alternatives in grammar.productions.values()
        for rhs in alternatives
    )
    for lhs, alternatives in grammar.productions.items():
        for rhs in alternatives:
            if not rhs:
                if lhs != grammar.start or start_on_rhs:
                    return False
            elif len(rhs) == 1:
                if rhs[0] in nts:
                    return False
            elif len(rhs) == 2:
                if rhs[0] not in nts or rhs[1] not in nts:
                    return False
            else:
                return False
    return True


def _fresh_symbol(prefix: str, occupied: set[str] | frozenset[str]) -> str:
    if prefix not in occupied:
        return prefix
    counter = 1
    while f"{prefix}{counter}" in occupied:
        counter += 1
    return f"{prefix}{counter}"
