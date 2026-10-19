"""Modelo y lector de gramaticas libres de contexto."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import AbstractSet, Iterable, Mapping


EPSILON_MARKERS = {"", "e", "epsilon", "eps", "ε", "λ"}


class GrammarError(ValueError):
    """Indica que la representacion textual de una gramatica no es valida."""


@dataclass(frozen=True)
class Grammar:
    """CFG inmutable; cada produccion es una tupla y () representa epsilon."""

    start: str
    productions: Mapping[str, AbstractSet[tuple[str, ...]]]

    def __post_init__(self) -> None:
        frozen = {
            lhs: frozenset(tuple(rhs) for rhs in alternatives)
            for lhs, alternatives in self.productions.items()
        }
        if not self.start:
            raise GrammarError("El simbolo inicial no puede estar vacio.")
        if self.start not in frozen:
            raise GrammarError(
                f"El simbolo inicial {self.start!r} no tiene producciones."
            )
        if any(not lhs for lhs in frozen) or any(
            not symbol
            for rules in frozen.values()
            for rhs in rules
            for symbol in rhs
        ):
            raise GrammarError("Los simbolos de la gramatica no pueden estar vacios.")
        object.__setattr__(self, "productions", MappingProxyType(frozen))

    @property
    def nonterminals(self) -> frozenset[str]:
        return frozenset(self.productions)

    @property
    def terminals(self) -> frozenset[str]:
        nts = self.nonterminals
        return frozenset(
            symbol
            for alternatives in self.productions.values()
            for rhs in alternatives
            for symbol in rhs
            if symbol not in nts
        )

    @property
    def production_count(self) -> int:
        return sum(len(alternatives) for alternatives in self.productions.values())

    def iter_productions(self) -> Iterable[tuple[str, tuple[str, ...]]]:
        order = [self.start, *sorted(self.nonterminals - {self.start})]
        for lhs in order:
            for rhs in sorted(self.productions[lhs], key=lambda item: (len(item), item)):
                yield lhs, rhs

    def to_text(self) -> str:
        lines: list[str] = []
        order = [self.start, *sorted(self.nonterminals - {self.start})]
        for lhs in order:
            alternatives = sorted(
                self.productions[lhs], key=lambda item: (len(item), item)
            )
            if not alternatives:
                lines.append(f"{lhs} -> ∅")
                continue
            rendered = [
                " ".join(
                    f"'{symbol}'" if _is_epsilon(symbol) or symbol == "∅" else symbol
                    for symbol in rhs
                ) if rhs else "ε"
                for rhs in alternatives
            ]
            lines.append(f"{lhs} -> {' | '.join(rendered)}")
        return "\n".join(lines)

    @classmethod
    def from_text(cls, text: str, start: str | None = None) -> "Grammar":
        # Identificamos los no terminales por sus lados izquierdos.
        parsed_lines: list[tuple[int, str, str]] = []
        lhs_order: list[str] = []

        for number, original in enumerate(text.splitlines(), 1):
            line = original.split("#", 1)[0].strip()
            if not line:
                continue
            if "->" in line:
                lhs, rhs_text = line.split("->", 1)
            elif "→" in line:
                lhs, rhs_text = line.split("→", 1)
            else:
                raise GrammarError(
                    f"Linea {number}: se esperaba '->' o '→' en {original!r}."
                )
            lhs = lhs.strip()
            if not lhs or any(char.isspace() for char in lhs):
                raise GrammarError(
                    f"Linea {number}: el lado izquierdo debe ser un solo simbolo."
                )
            if lhs not in lhs_order:
                lhs_order.append(lhs)
            parsed_lines.append((number, lhs, rhs_text.strip()))

        if not parsed_lines:
            raise GrammarError("La gramatica no contiene producciones.")

        productions: dict[str, set[tuple[str, ...]]] = {
            lhs: set() for lhs in lhs_order
        }
        for number, lhs, rhs_text in parsed_lines:
            for raw_alternative in rhs_text.split("|"):
                raw_alternative = raw_alternative.strip()
                if raw_alternative == "∅":
                    continue
                if _is_epsilon(raw_alternative):
                    productions[lhs].add(())
                    continue
                raw_symbols = tuple(raw_alternative.split())
                if any(_is_epsilon(symbol) for symbol in raw_symbols):
                    raise GrammarError(
                        f"Linea {number}: epsilon debe aparecer solo en su alternativa."
                    )
                symbols = tuple(_unquote(part) for part in raw_symbols)
                productions[lhs].add(symbols)

        initial = start or lhs_order[0]
        return cls(initial, {lhs: frozenset(rules) for lhs, rules in productions.items()})

    @classmethod
    def from_file(cls, path: str | Path, start: str | None = None) -> "Grammar":
        source = Path(path)
        try:
            text = source.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError) as exc:
            raise GrammarError(f"No se pudo leer la gramatica {source}: {exc}") from exc
        return cls.from_text(text, start=start)


def _unquote(symbol: str) -> str:
    if len(symbol) >= 2 and symbol[0] == symbol[-1] and symbol[0] in {'"', "'"}:
        return symbol[1:-1]
    return symbol


def _is_epsilon(value: str) -> bool:
    """Reconoce marcadores sin confundir el no terminal ``E`` con ``e``."""

    stripped = value.strip()
    return stripped in {"", "e", "ε", "λ"} or stripped.casefold() in {
        "epsilon",
        "eps",
    }
