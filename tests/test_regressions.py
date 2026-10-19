from __future__ import annotations

import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from itertools import product
from pathlib import Path
from tempfile import TemporaryDirectory

from cyk import CYKParser, Grammar, to_cnf
from main import run, tokenize


ROOT = Path(__file__).resolve().parents[1]
Word = tuple[str, ...]


def bounded_language(grammar: Grammar, max_length: int) -> set[Word]:
    """Deriva cadenas por punto fijo, sin usar CNF ni el algoritmo CYK."""
    languages: dict[str, set[Word]] = {symbol: set() for symbol in grammar.nonterminals}
    changed = True
    while changed:
        changed = False
        for lhs, rhs in grammar.iter_productions():
            fragments: set[Word] = {()}
            for symbol in rhs:
                suffixes = languages[symbol] if symbol in languages else {(symbol,)}
                fragments = {
                    prefix + suffix
                    for prefix in fragments
                    for suffix in suffixes
                    if len(prefix) + len(suffix) <= max_length
                }
            new_words = fragments - languages[lhs]
            if new_words:
                languages[lhs].update(new_words)
                changed = True
    return languages[grammar.start]


class ConversionRegressionTests(unittest.TestCase):
    def test_conversion_preserves_bounded_languages(self) -> None:
        examples = {
            "inicio anulable recursivo": "S -> S A | ε\nA -> a",
            "anulables repetidos": "S -> A A A\nA -> a | ε",
            "ciclos unitarios": "S -> A\nA -> B | a\nB -> A | b",
            "simbolos inutiles": "S -> A | Dead\nA -> a\nDead -> Dead\nUnused -> z",
            "terminales mixtos y regla larga": "S -> a B c D\nB -> b\nD -> d",
            "lenguaje vacio": "S -> S",
            "nombres auxiliares ocupados": "S -> _T A | _B A B\nA -> a\nB -> b",
            "terminal con nombre del nuevo inicio": "S -> S S | S_START | ε",
            "simbolo solo anulable": "S -> A B\nA -> ε\nB -> b",
            "marcadores citados como terminales": "S -> 'e' | 'epsilon'",
        }
        for name, text in examples.items():
            with self.subTest(case=name):
                original = Grammar.from_text(text)
                converted = to_cnf(original)
                expected = bounded_language(original, 4)
                self.assertEqual(bounded_language(converted.grammar, 4), expected)
                parser = CYKParser(converted.grammar)
                for length in range(5):
                    for word in product(sorted(original.terminals), repeat=length):
                        result = parser.parse(word)
                        self.assertEqual(result.accepted, word in expected, (name, word))
                        if result.tree is not None:
                            self.assertEqual(result.tree.yield_tokens(), word)

    def test_supplied_arithmetic_reference_matches_original(self) -> None:
        original = Grammar.from_file(ROOT / "grammars" / "arithmetic.cfg")
        reference = Grammar.from_file(ROOT / "grammars" / "arithmetic_cnf_reference.cfg")
        expected = bounded_language(original, 5)
        self.assertEqual(bounded_language(reference, 5), expected)
        parsers = (CYKParser(to_cnf(original).grammar), CYKParser(reference))
        for length in range(6):
            for word in product(sorted(original.terminals), repeat=length):
                for parser in parsers:
                    result = parser.parse(word)
                    self.assertEqual(result.accepted, word in expected, word)
                    if result.tree is not None:
                        self.assertEqual(result.tree.yield_tokens(), word)

    def test_grammar_productions_cannot_be_replaced(self) -> None:
        grammar = Grammar.from_text("S -> a")
        with self.assertRaises(TypeError):
            grammar.productions["S"] = frozenset({("b",)})  # type: ignore[index]

    def test_empty_language_can_be_exported_and_loaded(self) -> None:
        grammar = to_cnf(Grammar.from_text("S -> S")).grammar
        restored = Grammar.from_text(grammar.to_text())
        self.assertEqual(restored, grammar)
        self.assertFalse(CYKParser(restored).parse([]).accepted)
        self.assertFalse(CYKParser(restored).parse(["a"]).accepted)

    def test_literal_epsilon_markers_survive_text_round_trip(self) -> None:
        grammar = Grammar.from_text("S -> 'e' | 'epsilon' | '∅' | ε")
        restored = Grammar.from_text(grammar.to_text())
        self.assertEqual(restored, grammar)
        parser = CYKParser(restored)
        for word in ((), ("e",), ("epsilon",), ("∅",)):
            self.assertTrue(parser.parse(word).accepted)

    def test_cyk_rejects_grammar_outside_cnf(self) -> None:
        with self.assertRaises(ValueError):
            CYKParser(Grammar.from_text("S -> A\nA -> a"))

    def test_conversion_uses_stable_helper_names(self) -> None:
        first = Grammar.from_text("S -> a A c | b A d\nA -> x")
        second = Grammar.from_text("S -> b A d | a A c\nA -> x")
        self.assertEqual(to_cnf(first).grammar.to_text(), to_cnf(second).grammar.to_text())

    def test_ambiguous_grammar_returns_a_complete_tree(self) -> None:
        parser = CYKParser(to_cnf(Grammar.from_text("S -> S S | a")).grammar)
        first = parser.parse(("a", "a", "a"))
        second = parser.parse(("a", "a", "a"))
        self.assertIsNotNone(first.tree)
        assert first.tree is not None
        self.assertEqual(first.tree.yield_tokens(), ("a", "a", "a"))
        self.assertEqual(first.tree, second.tree)


class InputAndCLIRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.grammar = Grammar.from_file(ROOT / "grammars" / "english.cfg")
        cls.parser = CYKParser(to_cnf(cls.grammar).grammar)

    def test_unknown_underscore_is_not_silently_removed(self) -> None:
        for sentence in ("she_eats a cake", "she eats_a cake", "she eats a cake_"):
            with self.subTest(sentence=sentence):
                tokens = tokenize(sentence, self.grammar.terminals)
                self.assertIn("_", tokens)
                self.assertFalse(self.parser.parse(tokens).accepted)

    def test_capitals_and_final_punctuation_are_supported(self) -> None:
        tokens = tokenize("  SHE eats a cake!  ", self.grammar.terminals)
        self.assertEqual(tokens, ["she", "eats", "a", "cake"])
        self.assertTrue(self.parser.parse(tokens).accepted)

    def test_empty_english_input_is_rejected(self) -> None:
        self.assertFalse(self.parser.parse([]).accepted)

    def test_all_report_examples_have_expected_verdicts(self) -> None:
        examples = {
            "She eats a cake with a fork.": True,
            "The cat drinks the beer.": True,
            "He cooks.": True,
            "A dog eats the soup in the oven.": True,
            "Cake she eats a.": False,
            "She likes cake.": False,
            "The cat the beer drinks.": False,
            "She eats with.": False,
        }
        for sentence, expected in examples.items():
            with self.subTest(sentence=sentence):
                tokens = tokenize(sentence, self.grammar.terminals)
                result = self.parser.parse(tokens)
                self.assertEqual(result.accepted, expected)
                self.assertEqual(self.grammar.start in result.table[0][-1], expected)

    def test_punctuation_defined_as_a_terminal_is_preserved(self) -> None:
        grammar = Grammar.from_text("S -> hello .")
        tokens = tokenize("hello.", grammar.terminals)
        self.assertEqual(tokens, ["hello", "."])
        self.assertTrue(CYKParser(to_cnf(grammar).grammar).parse(tokens).accepted)

    def test_cli_prints_verdict_time_tree_and_table(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            status = run(["The cat drinks the beer", "--show-table"])
        self.assertEqual(status, 0)
        for expected in ("Resultado: SÍ", "Tiempo CYK:", " ns)", "Arbol sintactico:", "Tabla CYK:"):
            self.assertIn(expected, output.getvalue())

    def test_saved_cnf_can_be_loaded_and_used(self) -> None:
        with TemporaryDirectory() as folder:
            destination = Path(folder) / "nested" / "grammar.cfg"
            with redirect_stdout(io.StringIO()):
                status = run(["she cooks", "--save-cnf", str(destination)])
            self.assertEqual(status, 0)
            parser = CYKParser(Grammar.from_file(destination))
            self.assertTrue(parser.parse(["she", "cooks"]).accepted)

    def test_missing_grammar_reports_error(self) -> None:
        with TemporaryDirectory() as folder:
            error = io.StringIO()
            with redirect_stderr(error):
                status = run(["she cooks", "--grammar", str(Path(folder) / "missing.cfg")])
        self.assertEqual(status, 2)
        self.assertIn("Error de gramatica:", error.getvalue())

    def test_invalid_utf8_reports_error(self) -> None:
        with TemporaryDirectory() as folder:
            source = Path(folder) / "invalid.cfg"
            source.write_bytes(b"S -> \xff")
            error = io.StringIO()
            with redirect_stderr(error):
                status = run(["a", "--grammar", str(source)])
        self.assertEqual(status, 2)
        self.assertIn("Error de gramatica:", error.getvalue())

    def test_unwritable_cnf_destination_reports_error(self) -> None:
        with TemporaryDirectory() as folder:
            error = io.StringIO()
            with redirect_stderr(error):
                status = run(["she cooks", "--save-cnf", folder])
        self.assertEqual(status, 2)
        self.assertIn("No se pudo guardar", error.getvalue())


if __name__ == "__main__":
    unittest.main()
