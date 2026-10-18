# Antony Saz 24710
# Juan orozco


# Proyecto 2 - Algoritmo CYK

Aplicación en Python que simplifica una gramática libre de contexto (CFG), la
convierte a Forma Normal de Chomsky (CNF) y usa programación dinámica para
determinar si una cadena pertenece al lenguaje. Si la cadena es aceptada,
también reconstruye su árbol sintáctico.

No requiere librerías externas. Solo se necesita Python 3.10 o posterior.

## Uso rápido

Desde la carpeta del proyecto:

```powershell
python main.py "She eats a cake with a fork."
```

La salida incluye:

- `SÍ` o `NO` según el resultado del reconocimiento;
- tiempo exclusivo de ejecución del algoritmo CYK en milisegundos y nanosegundos;
- árbol sintáctico gráfico y en notación parentizada cuando la frase es válida.

Para ver la tabla dinámica:

```powershell
python main.py "The cat drinks the beer" --show-table
```

Para mostrar o guardar la gramática CNF:

```powershell
python main.py "she eats a cake" --show-cnf
python main.py "she eats a cake" --save-cnf grammars/english_generated_cnf.cfg
```

Para usar otra gramática, por ejemplo la aritmética proporcionada:

```powershell
python main.py "id + id * id" --grammar grammars/arithmetic.cfg
```

Si no se escribe la frase como argumento, el programa la solicita de forma
interactiva:

```powershell
python main.py
```

## Formato de las gramáticas

Cada línea contiene un no terminal, `->` (o `→`) y una o más alternativas
separadas por `|`. Los símbolos se separan con espacios. Se aceptan `e`, `ε`,
`epsilon`, `eps` o `λ` para representar la cadena vacía.

```text
S -> NP VP
NP -> Det N | she
Det -> a | the
```

El primer no terminal es el símbolo inicial. También puede indicarse otro con
`--start SIMBOLO`. Los comentarios empiezan con `#`.

## Pruebas

```powershell
python -m unittest discover -s tests -v
```

Las pruebas verifican la simplificación, la conversión a CNF, las frases en
inglés, el árbol reconstruido y la gramática aritmética de referencia.

## Estructura

```text
main.py                         Interfaz de línea de comandos
cyk/grammar.py                  Modelo y lector de CFG
cyk/cnf.py                      Simplificación y conversión a CNF
cyk/parser.py                   CYK, backpointers y árbol sintáctico
grammars/english.cfg            Gramática del enunciado
grammars/arithmetic.cfg         Ejemplo original sin CNF
grammars/arithmetic_cnf_reference.cfg  CNF entregada como referencia
tests/test_project.py           Pruebas automatizadas
INFORME.md                      Documentación del diseño y discusión
```

La documentación solicitada para la entrega está en [INFORME.md](INFORME.md).
