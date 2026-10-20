# Universidad del Valle de Guatemala

**Facultad de Ingeniería**

**Teoría de la Computación**

## Proyecto 2: Simplificación de gramáticas y análisis sintáctico con CYK

| Integrante | Carné |
|---|---|
| Juan Francisco Orozco Mijangos | 24647 |
| Antony David Melquisedec Saz Saz | 24710 |

## Descripción del proyecto

En este proyecto implementamos el algoritmo CYK en Python para comprobar si
una frase sencilla en inglés pertenece al lenguaje de una gramática libre de
contexto. Antes de analizar la frase, simplificamos la gramática eliminando
producciones epsilon, producciones unitarias y símbolos inútiles. Después la
convertimos a Forma Normal de Chomsky, que es la estructura que necesita CYK
para trabajar.

La idea es construir la solución a partir de partes pequeñas de la frase y
combinarlas mediante programación dinámica. El programa muestra si la entrada
es aceptada, cuánto tarda la validación y un árbol sintáctico que permite ver
cómo se obtuvo el resultado. Con esto relacionamos los conceptos de gramáticas
y lenguajes formales del curso con una implementación que podemos probar paso
a paso. También incluimos una gramática aritmética para comprobar que la
conversión funciona con reglas que todavía no están en CNF.

La validación es sintáctica: una frase puede ser aceptada aunque su significado
no tenga sentido, siempre que cumpla las reglas de la gramática.

No requiere librerías externas. Solo se necesita Python 3.10 o posterior.

## Uso rápido

Desde la carpeta del proyecto:

```bash
python3 main.py
```

Se abre un menu que permite repetir las consultas sin reiniciar el programa:

| Opcion | Accion |
|---|---|
| 1 | Mostrar la preparacion de la gramatica, los tokens, las celdas CYK y el resultado con tiempo y arbol |
| 2 | Mostrar las etapas de simplificacion y la CNF final |
| 0 | Salir |

La opcion 1 acepta una entrada vacia para comprobar si la gramatica genera
epsilon. Antes de cada consulta se vuelve a leer el archivo, por lo que se
pueden editar sus reglas sin reiniciar el programa. Si una regla es invalida,
se muestra el error y se vuelve al menu.

Despues de cada consulta se vuelve al menu. Para terminar, seleccione
**0. Salir**. La explicacion de los pasos se imprime fuera de la medicion
del algoritmo, por lo que el tiempo CYK no incluye esa salida en pantalla.

Tambien puede ejecutar una consulta directamente:

```bash
python3 main.py "She eats a cake with a fork."
```

Para mostrar los pasos tambien en una consulta directa:

```bash
python3 main.py "she eats a cake" --show-steps --show-table
```

La salida incluye:

- `SÍ` o `NO` según el resultado del reconocimiento;
- tiempo exclusivo de ejecución del algoritmo CYK en milisegundos y nanosegundos;
- árbol sintáctico gráfico y en notación parentizada cuando la frase es válida.

Para ver la tabla dinámica:

```bash
python3 main.py "The cat drinks the beer" --show-table
```

Para mostrar o guardar la gramática CNF:

```bash
python3 main.py "she eats a cake" --show-cnf
python3 main.py "she eats a cake" --save-cnf grammars/english_generated_cnf.cfg
```

Para usar otra gramática, por ejemplo la aritmética proporcionada:

```bash
python3 main.py "id + id * id" --grammar grammars/arithmetic.cfg
```

Para abrir el menu con una gramatica determinada:

```bash
python3 main.py --menu --grammar grammars/arithmetic.cfg
```

En ese menu, la opcion 2 permite demostrar la simplificacion y conversion de
reglas aritmeticas que todavia no estan en CNF.

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

`S -> ∅` representa un símbolo sin producciones, útil para guardar una gramática
que genera el lenguaje vacío. Es distinto de `S -> ε`, que acepta la cadena
vacía. Para usar un marcador como terminal literal se escribe entre comillas,
por ejemplo, `S -> 'e'`.

## Pruebas

```bash
python3 -m unittest discover -s tests -v
```

Las 42 pruebas incluyen las 30 comprobaciones del algoritmo y 12 del menu.
Verifican la simplificación, la conversión a CNF, las frases en inglés, el
árbol reconstruido, casos límite, errores de archivos, lectura de reglas
editadas, salida numerica y consultas consecutivas. También comparan el
reconocimiento aritmético con una derivación independiente de la CFG original
y con la CNF de referencia para las 3,906 cadenas posibles de hasta cinco
tokens, incluida la vacía.

En Windows puede usarse `python` en lugar de `python3`, según la instalación.

## Documentación

El [informe del proyecto](documentacion.pdf) incluye el diseño de la aplicación,
la explicación de los algoritmos, las pruebas realizadas y la discusión.
El informe registra las 30 pruebas de la version original; esta version agrega
12 pruebas de la interfaz y el menu explicado en este README.

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
tests/test_regressions.py       Casos límite y comparación independiente de lenguajes
tests/test_console.py           Pruebas del menu de consola
documentacion.pdf              Informe del proyecto
```
