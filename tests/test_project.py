from __future__ import annotations

import unittest
from pathlib import Path

from cyk import (
    CYKParser,
    CYKResult,
    Grammar,
    eliminate_epsilon,
    eliminate_unit,
    is_cnf,
    remove_useless,
    to_cnf,
)
from main import tokenize


ROOT = Path(__file__).resolve().parents[1]


class EnglishGrammarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.conversion = to_cnf(Grammar.from_file(ROOT / "grammars" / "english.cfg"))
        cls.parser = CYKParser(cls.conversion.grammar)

    def parse(self, sentence: str) -> CYKResult:
        tokens = tokenize(sentence, self.conversion.grammar.terminals)
        return self.parser.parse(tokens)

    def test_example_with_prepositional_phrase_is_accepted(self) -> None:
        result = self.parse("She eats a cake with a fork.")
        self.assertTrue(result.accepted)
        self.assertIsNotNone(result.tree)
        assert result.tree is not None
        self.assertEqual(
            result.tree.yield_tokens(),
            ("she", "eats", "a", "cake", "with", "a", "fork"),
        )

    def test_example_with_noun_subject_is_accepted(self) -> None:
        self.assertTrue(self.parse("The cat drinks the beer").accepted)

    def test_intransitive_example_is_accepted_by_given_grammar(self) -> None:
        self.assertTrue(self.parse("he cooks").accepted)

    def test_bad_word_order_is_rejected(self) -> None:
        self.assertFalse(self.parse("cake she eats a").accepted)

    def test_unknown_word_is_rejected(self) -> None:
        self.assertFalse(self.parse("she likes cake").accepted)

    def test_english_grammar_is_cnf(self) -> None:
        self.assertTrue(is_cnf(self.conversion.grammar))


class SimplificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.grammar = Grammar.from_text(
            """
            S -> A B | U
            A -> a | e
            B -> b
            U -> V
            V -> c
            Dead -> Dead
            """
        )

    def test_epsilon_elimination_adds_nullable_variant(self) -> None:
        result = eliminate_epsilon(self.grammar)
        self.assertIn(("B",), result.productions["S"])
        self.assertNotIn((), result.productions["A"])

    def test_unit_elimination_removes_unit_rules(self) -> None:
        result = eliminate_unit(eliminate_epsilon(self.grammar))
        for alternatives in result.productions.values():
            self.assertFalse(
                any(len(rhs) == 1 and rhs[0] in result.nonterminals for rhs in alternatives)
            )
        self.assertIn(("c",), result.productions["S"])

    def test_useless_elimination_removes_dead_symbol(self) -> None:
        result = remove_useless(eliminate_unit(eliminate_epsilon(self.grammar)))
        self.assertNotIn("Dead", result.nonterminals)


class ArithmeticConversionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        grammar = Grammar.from_file(ROOT / "grammars" / "arithmetic.cfg")
        cls.conversion = to_cnf(grammar)
        cls.parser = CYKParser(cls.conversion.grammar)

    def parse(self, expression: str) -> CYKResult:
        return self.parser.parse(tokenize(expression, self.conversion.grammar.terminals))

    def test_conversion_produces_cnf(self) -> None:
        self.assertTrue(is_cnf(self.conversion.grammar))

    def test_expression_is_accepted(self) -> None:
        self.assertTrue(self.parse("id + id * id").accepted)
        self.assertTrue(self.parse("(id+id)*id").accepted)

    def test_incomplete_expression_is_rejected(self) -> None:
        self.assertFalse(self.parse("id + * id").accepted)


if __name__ == "__main__":
    unittest.main()
