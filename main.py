"""Interfaz de linea de comandos para el proyecto de CYK."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from cyk import CYKParser, CYKResult, Grammar, GrammarError, to_cnf


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_GRAMMAR = PROJECT_ROOT / "grammars" / "english.cfg"
TOKEN_PATTERN = re.compile(r"[^\W_]+(?:'[^\W_]+)?|[^\s]", re.UNICODE)


def tokenize(sentence: str, terminals: frozenset[str]) -> list[str]:
    """Separa palabras/simbolos y normaliza mayusculas sin ocultar errores."""

    raw_tokens = TOKEN_PATTERN.findall(sentence.strip())
    # Conservamos los símbolos desconocidos para que provoquen un rechazo.
    while (
        raw_tokens
        and raw_tokens[-1] in {".", "?", "!"}
        and raw_tokens[-1] not in terminals
    ):
        raw_tokens.pop()

    canonical: dict[str, str] = {}
    for terminal in sorted(terminals):
        canonical.setdefault(terminal.casefold(), terminal)
    return [canonical.get(token.casefold(), token.casefold()) for token in raw_tokens]


def format_table(result: CYKResult) -> str:
    if not result.tokens:
        return "(tabla vacia)"
    lines: list[str] = []
    size = len(result.tokens)
    for span in range(1, size + 1):
        lines.append(f"Longitud {span}:")
        for start in range(size - span + 1):
            end = start + span - 1
            symbols = ", ".join(sorted(result.table[start][end])) or "∅"
            fragment = " ".join(result.tokens[start : end + 1])
            lines.append(f"  [{start + 1},{end + 1}] {fragment!r}: {{{symbols}}}")
    return "\n".join(lines)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Determina con CYK si una frase pertenece al lenguaje de una CFG y "
            "muestra su arbol sintactico."
        )
    )
    parser.add_argument(
        "sentence",
        nargs="*",
        help="Frase que se analizara. Si se omite, el programa la solicita.",
    )
    parser.add_argument(
        "-g",
        "--grammar",
        type=Path,
        default=DEFAULT_GRAMMAR,
        help=f"Archivo CFG (predeterminado: {DEFAULT_GRAMMAR.name}).",
    )
    parser.add_argument(
        "--start",
        help="Simbolo inicial; de forma predeterminada se usa el primer lado izquierdo.",
    )
    parser.add_argument(
        "--show-cnf", action="store_true", help="Muestra la gramatica CNF resultante."
    )
    parser.add_argument(
        "--show-table", action="store_true", help="Muestra la tabla dinamica de CYK."
    )
    parser.add_argument(
        "--save-cnf", type=Path, help="Guarda la gramatica convertida a CNF."
    )
    return parser


def run(argv: list[str] | None = None) -> int:
    args = build_argument_parser().parse_args(argv)
    # Cargamos la gramática y la pasamos a CNF.
    try:
        source = Grammar.from_file(args.grammar, start=args.start)
        conversion = to_cnf(source)
    except GrammarError as exc:
        print(f"Error de gramatica: {exc}", file=sys.stderr)
        return 2

    if args.save_cnf:
        try:
            args.save_cnf.parent.mkdir(parents=True, exist_ok=True)
            args.save_cnf.write_text(conversion.grammar.to_text() + "\n", encoding="utf-8")
        except OSError as exc:
            print(f"No se pudo guardar la gramatica CNF: {exc}", file=sys.stderr)
            return 2
        print(f"Gramatica CNF guardada en: {args.save_cnf}")

    if args.show_cnf:
        print("\nGramatica en Forma Normal de Chomsky:")
        print(conversion.grammar.to_text())
        print(
            f"\nProducciones: {conversion.original_productions} originales; "
            f"{conversion.simplified_productions} despues de simplificar; "
            f"{conversion.grammar.production_count} en CNF."
        )

    sentence = " ".join(args.sentence).strip()
    if not sentence:
        try:
            sentence = input("Ingrese una frase en ingles: ").strip()
        except EOFError:
            print("No se recibio ninguna frase.", file=sys.stderr)
            return 2

    # Normalizamos la frase antes de llenar la tabla.
    tokens = tokenize(sentence, conversion.grammar.terminals)
    result = CYKParser(conversion.grammar).parse(tokens)

    known = conversion.grammar.terminals
    unknown = sorted({token for token in tokens if token not in known})
    print(f"\nFrase normalizada: {' '.join(tokens) if tokens else '(vacia)'}")
    print(f"Resultado: {'SÍ' if result.accepted else 'NO'}")
    print(f"Tiempo CYK: {result.elapsed_ms:.6f} ms ({result.elapsed_ns} ns)")
    if unknown:
        print(f"Tokens que no pertenecen al vocabulario: {', '.join(unknown)}")

    if result.tree is not None:
        print("\nArbol sintactico:")
        print(result.tree.pretty(conversion.helper_symbols))
        print("\nNotacion parentizada:")
        print(result.tree.bracketed(conversion.helper_symbols))
    else:
        print("Arbol sintactico: no existe para esta gramatica.")

    if args.show_table:
        print("\nTabla CYK:")
        print(format_table(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
