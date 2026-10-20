from __future__ import annotations

import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from main import PROJECT_ROOT, run


class ConsoleMenuTests(unittest.TestCase):
    def menu(
        self, answers: list[str | BaseException], argv: list[str] | None = None
    ) -> tuple[int, str]:
        output = io.StringIO()
        with patch("builtins.input", side_effect=answers), redirect_stdout(output):
            status = run([] if argv is None else argv)
        return status, output.getvalue()

    def test_menu_has_only_the_required_actions(self) -> None:
        status, output = self.menu(["0"])
        self.assertEqual(status, 0)
        options = [line for line in output.splitlines() if line[:2] in {"0.", "1.", "2."}]
        self.assertEqual(options, [
            "1. Analizar una frase",
            "2. Ver la simplificacion y conversion a CNF",
            "0. Salir",
        ])
        self.assertNotIn("3.", output)

    def test_exit_uses_option_zero(self) -> None:
        status, output = self.menu(["salir", "0"])
        self.assertEqual(status, 0)
        self.assertIn("Opcion no valida.", output)
        self.assertEqual(output.count("Hasta luego."), 1)

    def test_multiple_phrases_can_be_analyzed_without_restarting(self) -> None:
        status, output = self.menu(["1", "she cooks", "1", "she likes cake", "0"])
        self.assertEqual(status, 0)
        self.assertIn("Resultado: SÍ", output)
        self.assertIn("Resultado: NO", output)
        self.assertEqual(output.count("Tiempo CYK:"), 2)

    def test_analysis_explains_all_steps_and_returns_to_menu(self) -> None:
        status, output = self.menu(["1", "she eats a cake", "2", "0"])
        self.assertEqual(status, 0)
        for number in range(1, 6):
            self.assertIn(f"PASO {number}.", output)
        self.assertIn("NP -> Det N", output)
        self.assertIn("Resultado: SÍ", output)
        self.assertIn("Arbol sintactico:", output)
        self.assertEqual(output.count("=== PROYECTO 2 - ANALIZADOR CYK ==="), 3)

    def test_empty_input_does_not_access_a_nonexistent_cell(self) -> None:
        status, output = self.menu(["1", "", "0"])
        self.assertEqual(status, 0)
        self.assertIn("Entrada vacia:", output)
        self.assertIn("Resultado: NO", output)

    def test_direct_command_can_show_steps_and_cuts(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            status = run(["she cooks", "--show-steps", "--show-table"])
        self.assertEqual(status, 0)
        for expected in ("PASO 1.", "Corte despues de la palabra", "Resultado: SÍ", "Tabla CYK:"):
            self.assertIn(expected, output.getvalue())

    def test_simplification_option_shows_all_stages(self) -> None:
        source = PROJECT_ROOT / "grammars" / "arithmetic.cfg"
        status, output = self.menu(["2", "0"], ["--menu", "--grammar", str(source)])
        self.assertEqual(status, 0)
        for expected in (
            "1. Gramatica original:",
            "2. Sin producciones epsilon",
            "3. Sin producciones unitarias:",
            "4. Sin simbolos inutiles:",
            "5. Conversion final",
            "Producciones: 8 originales;",
        ):
            self.assertIn(expected, output)

    def test_consultation_automatically_reads_edited_rules(self) -> None:
        with TemporaryDirectory() as folder:
            source = Path(folder) / "custom.cfg"
            source.write_text("S -> she", encoding="utf-8")
            answers = iter(("1", "she eats", "0"))

            def answer(prompt: str) -> str:
                choice = next(answers)
                if choice == "1":
                    source.write_text("S -> NP VP\nNP -> she\nVP -> eats", encoding="utf-8")
                return choice

            output = io.StringIO()
            with patch("builtins.input", side_effect=answer), redirect_stdout(output):
                status = run(["--menu", "--grammar", str(source)])
        self.assertEqual(status, 0)
        self.assertIn("Resultado: SÍ", output.getvalue())

    def test_invalid_edits_return_to_menu_without_using_old_rules(self) -> None:
        with TemporaryDirectory() as folder:
            source = Path(folder) / "custom.cfg"
            source.write_text("S -> a", encoding="utf-8")
            answers = iter(("1", "0"))

            def answer(prompt: str) -> str:
                choice = next(answers)
                if choice == "1":
                    source.write_text("regla sin flecha", encoding="utf-8")
                return choice

            output = io.StringIO()
            with patch("builtins.input", side_effect=answer), redirect_stdout(output):
                status = run(["--menu", "--grammar", str(source)])
        self.assertEqual(status, 0)
        self.assertIn("Error de gramatica:", output.getvalue())
        self.assertNotIn("Resultado:", output.getvalue())

    def test_invalid_options_return_to_menu(self) -> None:
        status, output = self.menu(["99", "9", "0"])
        self.assertEqual(status, 0)
        self.assertEqual(output.count("Opcion no valida."), 2)

    def test_eof_and_keyboard_interrupt_exit_cleanly(self) -> None:
        for interruption in (EOFError(), KeyboardInterrupt()):
            with self.subTest(interruption=type(interruption).__name__):
                status, output = self.menu([interruption])
                self.assertEqual(status, 0)
                self.assertIn("Menu cerrado.", output)

    def test_menu_rejects_conflicting_direct_options(self) -> None:
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            run(["--menu", "she cooks"])
        self.assertEqual(error.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
