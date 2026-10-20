"""Interfaz de linea de comandos para el proyecto de CYK."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from cyk import (
    CNFConversion,
    CYKParser,
    CYKResult,
    Grammar,
    GrammarError,
    eliminate_epsilon,
    eliminate_unit,
    remove_useless,
    to_cnf,
)


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_GRAMMAR = PROJECT_ROOT / "grammars" / "english.cfg"
TOKEN_PATTERN = re.compile(r"[^\W_]+(?:'[^\W_]+)?|[^\s]", re.UNICODE)
MENU = """
1. Analizar una frase
2. Ver la simplificacion y conversion a CNF
0. Salir
"""


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


def show_conversion(conversion: CNFConversion) -> None:
    print("\nGramatica en Forma Normal de Chomsky:")
    print(conversion.grammar.to_text())
    print(
        f"\nProducciones: {conversion.original_productions} originales; "
        f"{conversion.simplified_productions} despues de simplificar; "
        f"{conversion.grammar.production_count} en CNF."
    )


def show_cyk_steps(result: CYKResult, grammar: Grammar, *, detailed: bool) -> None:
    if not result.tokens:
        print(f"Entrada vacia: comprobamos si {grammar.start} -> ε existe.")
        return

    binary_rules: dict[tuple[str, str], list[str]] = {}
    for lhs, rhs in grammar.iter_productions():
        if len(rhs) == 2:
            binary_rules.setdefault((rhs[0], rhs[1]), []).append(lhs)

    print("Primero llenamos la diagonal, una palabra por celda:")
    for index, token in enumerate(result.tokens):
        symbols = sorted(result.table[index][index])
        rules = "; ".join(f"{symbol} -> {token}" for symbol in symbols)
        print(f"  [{index + 1},{index + 1}] {token!r}: {rules or 'sin reglas terminales'}")

    for span in range(2, len(result.tokens) + 1):
        print(f"\nCombinamos fragmentos de {span} palabras:")
        for start in range(len(result.tokens) - span + 1):
            end = start + span - 1
            fragment = " ".join(result.tokens[start : end + 1])
            print(f"  [{start + 1},{end + 1}] {fragment!r}")
            for split in range(start, end):
                left = sorted(result.table[start][split])
                right = sorted(result.table[split + 1][end])
                matches = [
                    f"{lhs} -> {first} {second}"
                    for first in left
                    for second in right
                    for lhs in binary_rules.get((first, second), ())
                ]
                if detailed:
                    print(
                        f"    Corte despues de la palabra {split + 1}: "
                        f"{{{', '.join(left) or '∅'}}} + {{{', '.join(right) or '∅'}}}"
                    )
                if matches:
                    print(f"    Reglas aplicables: {'; '.join(matches)}")
                elif detailed:
                    print("    Ninguna regla combina estas dos partes.")
            symbols = ", ".join(sorted(result.table[start][end])) or "∅"
            print(f"    Simbolos de la celda: {{{symbols}}}")


def analyze_sentence(
    sentence: str,
    conversion: CNFConversion,
    *,
    show_table: bool = False,
    show_steps: bool = False,
    source: Grammar | None = None,
) -> CYKResult:
    if show_steps:
        print("\nPASO 1. Revisar la preparacion de la gramatica activa")
        if source is not None:
            show_simplification(source, conversion)
        else:
            show_conversion(conversion)
        print("\nPASO 2. Separar y normalizar la entrada")
    # Normalizamos la frase antes de llenar la tabla.
    tokens = tokenize(sentence, conversion.grammar.terminals)
    if show_steps:
        print(f"Entrada: {sentence!r}")
        print(f"Tokens: {tokens}")
        print("\nPASO 3. Construir y llenar la tabla CYK")
    result = CYKParser(conversion.grammar).parse(tokens)
    # Explicamos la tabla fuera de la medicion para no incluir la impresion.
    if show_steps:
        show_cyk_steps(result, conversion.grammar, detailed=show_table)
        print("\nPASO 4. Comprobar la frase completa")
        if tokens:
            symbols = ", ".join(sorted(result.table[0][-1])) or "∅"
            print(f"Celda [1,{len(tokens)}]: {{{symbols}}}")
            print(f"Buscamos el simbolo inicial {conversion.grammar.start} en esa celda.")
        else:
            print("La entrada vacia se acepta solo si el inicio tiene una regla epsilon.")
    unknown = sorted(set(tokens) - conversion.grammar.terminals)
    print(f"\nFrase normalizada: {' '.join(tokens) if tokens else '(vacia)'}")
    print(f"Resultado: {'SÍ' if result.accepted else 'NO'}")
    print(f"Tiempo CYK: {result.elapsed_ms:.6f} ms ({result.elapsed_ns} ns)")
    if unknown:
        print(f"Tokens que no pertenecen al vocabulario: {', '.join(unknown)}")
    if show_steps:
        print("\nPASO 5. Mostrar el arbol de la derivacion encontrada")
    if result.tree is not None:
        print("\nArbol sintactico:")
        print(result.tree.pretty(conversion.helper_symbols))
        print("\nNotacion parentizada:")
        print(result.tree.bracketed(conversion.helper_symbols))
    else:
        print("Arbol sintactico: no existe para esta gramatica.")
    if show_table:
        print("\nTabla CYK:")
        print(format_table(result))
    return result


def show_simplification(source: Grammar, conversion: CNFConversion) -> None:
    print("\n1. Gramatica original:")
    print(source.to_text())
    without_epsilon = eliminate_epsilon(source)
    print("\n2. Sin producciones epsilon, salvo el inicio si corresponde:")
    print(without_epsilon.to_text())
    without_unit = eliminate_unit(without_epsilon)
    print("\n3. Sin producciones unitarias:")
    print(without_unit.to_text())
    print("\n4. Sin simbolos inutiles:")
    print(remove_useless(without_unit).to_text())
    print("\n5. Conversion final (incluye un inicio nuevo si es necesario):")
    show_conversion(conversion)


def save_cnf(grammar: Grammar, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(grammar.to_text() + "\n", encoding="utf-8")
    print(f"Gramatica CNF guardada en: {destination}")


def run_menu(grammar_path: Path, start: str | None = None) -> int:
    try:
        source = Grammar.from_file(grammar_path, start=start)
        conversion = to_cnf(source)
    except GrammarError as exc:
        print(f"Error de gramatica: {exc}", file=sys.stderr)
        return 2

    try:
        while True:
            print("\n=== PROYECTO 2 - ANALIZADOR CYK ===")
            print(f"Gramatica activa: {grammar_path}")
            print(f"Simbolo inicial: {source.start}")
            print(MENU)
            choice = input("Seleccione una opcion: ").strip()
            if choice == "0":
                print("Hasta luego.")
                return 0
            if choice not in {"1", "2"}:
                print("Opcion no valida. Elija 1, 2 o 0.")
                continue
            # Leemos de nuevo por si editamos las reglas durante la revision.
            try:
                updated = Grammar.from_file(grammar_path, start=start)
                converted = to_cnf(updated)
            except GrammarError as exc:
                print(f"Error de gramatica: {exc}")
                continue
            source, conversion = updated, converted
            if choice == "1":
                sentence = input("Ingrese la frase o expresion: ")
                analyze_sentence(
                    sentence,
                    conversion,
                    show_steps=True,
                    source=source,
                )
            else:
                show_simplification(source, conversion)
    except (EOFError, KeyboardInterrupt):
        print("\nMenu cerrado.")
        return 0


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
        help="Frase que se analizara. Sin argumentos se abre el menu.",
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
    parser.add_argument(
        "--menu", action="store_true", help="Abre el menu interactivo de revision."
    )
    parser.add_argument(
        "--show-steps", action="store_true", help="Explica las etapas y el llenado de CYK."
    )
    return parser


def run(argv: list[str] | None = None) -> int:
    argument_parser = build_argument_parser()
    args = argument_parser.parse_args(argv)
    direct_options = (
        args.show_cnf or args.show_table or args.show_steps or args.save_cnf is not None
    )
    if args.menu and (args.sentence or direct_options):
        argument_parser.error("--menu se usa sin frase ni opciones de salida directa.")
    if args.menu or (not args.sentence and not direct_options):
        return run_menu(args.grammar, start=args.start)
    # Cargamos la gramática y la pasamos a CNF.
    try:
        source = Grammar.from_file(args.grammar, start=args.start)
        conversion = to_cnf(source)
    except GrammarError as exc:
        print(f"Error de gramatica: {exc}", file=sys.stderr)
        return 2

    if args.save_cnf:
        try:
            save_cnf(conversion.grammar, args.save_cnf)
        except OSError as exc:
            print(f"No se pudo guardar la gramatica CNF: {exc}", file=sys.stderr)
            return 2

    if args.show_cnf:
        show_conversion(conversion)

    sentence = " ".join(args.sentence).strip()
    if not sentence:
        try:
            sentence = input("Ingrese una frase en ingles: ").strip()
        except EOFError:
            print("No se recibio ninguna frase.", file=sys.stderr)
            return 2

    analyze_sentence(
        sentence,
        conversion,
        show_table=args.show_table,
        show_steps=args.show_steps,
        source=source,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
