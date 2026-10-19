"""Algoritmo CYK con backpointers para reconstruir un arbol sintactico."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter_ns

from .cnf import is_cnf
from .grammar import Grammar


@dataclass(frozen=True)
class ParseNode:
    symbol: str
    children: tuple["ParseNode", ...] = ()
    token: str | None = None

    def yield_tokens(self) -> tuple[str, ...]:
        if self.token is not None:
            return (self.token,)
        return tuple(token for child in self.children for token in child.yield_tokens())

    def pretty(self, hidden_symbols: frozenset[str] = frozenset()) -> str:
        forest = _visible_forest(self, hidden_symbols)
        lines: list[str] = []
        for index, node in enumerate(forest):
            _render_visual(node, "", index == len(forest) - 1, lines, is_root=True)
        return "\n".join(lines)

    def bracketed(self, hidden_symbols: frozenset[str] = frozenset()) -> str:
        forest = _visible_forest(self, hidden_symbols)
        return " ".join(_visual_bracketed(node) for node in forest)


@dataclass(frozen=True)
class CYKResult:
    accepted: bool
    tokens: tuple[str, ...]
    elapsed_ns: int
    tree: ParseNode | None
    table: tuple[tuple[frozenset[str], ...], ...]

    @property
    def elapsed_ms(self) -> float:
        return self.elapsed_ns / 1_000_000


class CYKParser:
    """Parser reutilizable para una gramatica que ya esta en CNF."""

    def __init__(self, grammar: Grammar) -> None:
        if not is_cnf(grammar):
            raise ValueError("CYK requiere una gramatica en Forma Normal de Chomsky.")
        self.grammar = grammar
        terminal_index: dict[str, list[str]] = {}
        binary_index: dict[tuple[str, str], list[str]] = {}
        for lhs, rhs in grammar.iter_productions():
            if len(rhs) == 1 and rhs[0] not in grammar.nonterminals:
                terminal_index.setdefault(rhs[0], []).append(lhs)
            elif len(rhs) == 2:
                binary_index.setdefault((rhs[0], rhs[1]), []).append(lhs)
        self._terminal_index = {
            terminal: tuple(sorted(lhs_values))
            for terminal, lhs_values in terminal_index.items()
        }
        self._binary_index = {
            pair: tuple(sorted(lhs_values)) for pair, lhs_values in binary_index.items()
        }

    def parse(self, tokens: list[str] | tuple[str, ...]) -> CYKResult:
        words = tuple(tokens)
        # Medimos solo la construcción y el llenado de la tabla.
        started = perf_counter_ns()

        if not words:
            accepted = () in self.grammar.productions[self.grammar.start]
            tree = ParseNode(self.grammar.start) if accepted else None
            return CYKResult(
                accepted, words, perf_counter_ns() - started, tree, tuple()
            )

        size = len(words)
        cells: list[list[dict[str, ParseNode]]] = [
            [dict() for _ in range(size)] for _ in range(size)
        ]

        # Llenamos la diagonal con las reglas de cada palabra.
        for index, token in enumerate(words):
            for lhs in self._terminal_index.get(token, ()):
                cells[index][index][lhs] = ParseNode(lhs, token=token)

        # Combinamos fragmentos ya resueltos, de menor a mayor longitud.
        for span in range(2, size + 1):
            for start in range(0, size - span + 1):
                end = start + span - 1
                destination = cells[start][end]
                for split in range(start, end):
                    left = cells[start][split]
                    right = cells[split + 1][end]
                    right_symbols = sorted(right)
                    for left_symbol in sorted(left):
                        for right_symbol in right_symbols:
                            for lhs in self._binary_index.get(
                                (left_symbol, right_symbol), ()
                            ):
                                # Guardamos los hijos para reconstruir el árbol.
                                if lhs not in destination:
                                    destination[lhs] = ParseNode(
                                        lhs,
                                        (left[left_symbol], right[right_symbol]),
                                    )

        elapsed = perf_counter_ns() - started
        # El inicio debe generar la frase completa.
        tree = cells[0][size - 1].get(self.grammar.start)
        public_table = tuple(
            tuple(frozenset(cells[row][column]) for column in range(size))
            for row in range(size)
        )
        return CYKResult(tree is not None, words, elapsed, tree, public_table)


@dataclass(frozen=True)
class _VisualNode:
    label: str
    children: tuple["_VisualNode", ...] = ()


def _visible_forest(node: ParseNode, hidden: frozenset[str]) -> tuple[_VisualNode, ...]:
    if node.token is not None:
        if node.symbol in hidden:
            return (_VisualNode(node.token),)
        return (_VisualNode(node.symbol, (_VisualNode(node.token),)),)

    visible_children = tuple(
        visible
        for child in node.children
        for visible in _visible_forest(child, hidden)
    )
    if node.symbol in hidden:
        return visible_children
    return (_VisualNode(node.symbol, visible_children),)


def _render_visual(
    node: _VisualNode,
    prefix: str,
    is_last: bool,
    lines: list[str],
    *,
    is_root: bool = False,
) -> None:
    connector = "" if is_root else ("└── " if is_last else "├── ")
    lines.append(f"{prefix}{connector}{node.label}")
    child_prefix = prefix if is_root else prefix + ("    " if is_last else "│   ")
    for index, child in enumerate(node.children):
        _render_visual(
            child,
            child_prefix,
            index == len(node.children) - 1,
            lines,
        )


def _visual_bracketed(node: _VisualNode) -> str:
    if not node.children:
        return node.label
    return f"({node.label} {' '.join(_visual_bracketed(child) for child in node.children)})"
