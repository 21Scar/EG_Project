# 2. Especificação Lexical e Sintática

Nesta secção, apresentamos a especificação formal da *StudyLang*. O processo de reconhecimento da linguagem está dividido em duas partes: a definição lexical (identificação dos símbolos básicos ou *tokens*) e a especificação sintática (definição das regras de formação de frases válidas através de uma Gramática Independente de Contexto).

## 2.1. Especificação Lexical

A análise lexical é responsável por converter a sequência de caracteres do código-fonte numa sequência de *tokens*. A *StudyLang* é insensível a espaços em branco (espaços, tabulações e quebras de linha), que funcionam apenas como separadores. **Os comentários de linha (iniciados por `//` e terminados no fim da linha) são descartados pelo analisador lexical**, tal como os espaços em branco.

Os *tokens* da linguagem dividem-se nas seguintes categorias:

* **Palavras Reservadas (Keywords):** Termos que fazem parte da estrutura da linguagem e não podem ser usados como nomes de variáveis.
  * `STUDENT`, `UC`, `CREDITS`, `DIFFICULTY`, `RESOURCE`, `TIME`, `HOURS`, `PLAN`, `STUDY`, `FOR`, `VAR`, `EACH`, `IN`, `IF`, `ELSE`, `AND`, `OR`, `NOT`
  * Em caso de conflito com a expressão regular de `ID`, a palavra reservada tem prioridade. As palavras reservadas são sensíveis a maiúsculas/minúsculas (`study` é um `ID`, `STUDY` é uma palavra reservada).
* **Identificadores (ID):** Usados para nomear variáveis e iteradores. Iniciam-se com uma letra, seguida de letras, números ou *underscores*.
  * Expressão Regular: `[a-zA-Z][a-zA-Z0-9_]*`
* **Literais de Texto (STRING):** Qualquer sequência de caracteres (exceto aspas duplas) delimitada por aspas duplas. Usado primariamente para os nomes das UCs.
  * Expressão Regular: `"[^"]*"`
* **Literais Numéricos (NUMBER):** Sequência de dígitos que representa números inteiros não negativos (os valores negativos obtêm-se com o operador unário `-`).
  * Expressão Regular: `[0-9]+`
* **Comentários (ignorados):**
  * Expressão Regular: `//[^\n]*`
* **Operadores e Pontuação:** Símbolos utilizados para matemática, lógica e estruturação de blocos.
  * Aritméticos: `+`, `-`, `*`, `/`
  * Relacionais: `>`, `<`, `>=`, `<=`, `==`, `!=`
  * Atribuição: `=`
  * Acesso a atributo: `.`
  * Estruturais: `{`, `}`, `(`, `)`, `[`, `]`, `,`
  * Os operadores de dois carateres (`>=`, `<=`, `==`, `!=`) são reconhecidos pelo princípio do maior prefixo (*longest match*).

## 2.2. Especificação Sintática (Gramática Independente de Contexto)

A sintaxe da linguagem é definida por uma Gramática Independente de Contexto (CFG). Abaixo, apresentamos a especificação da gramática utilizando a notação EBNF (*Extended Backus-Naur Form*). Os terminais entre aspas são palavras reservadas ou símbolos; `<ID>`, `<STRING>` e `<NUMBER>` são os *tokens* definidos na secção 2.1.

A estrutura hierárquica garante a correta precedência das operações: nas expressões aritméticas, a multiplicação e divisão têm precedência sobre a adição e subtração; nas condições, `NOT` tem precedência sobre `AND`, que tem precedência sobre `OR`.

```ebnf
<Program>       ::= "STUDENT" <ID> <Declaration>* <Plan>

<Declaration>   ::= <UC_Decl>
                  | <Resource_Decl>
                  | <Var_Decl>

<UC_Decl>       ::= "UC" <STRING> "{" "CREDITS" <NUMBER> "DIFFICULTY" <NUMBER> "}"

<Resource_Decl> ::= "RESOURCE" "TIME" <NUMBER> "HOURS"

<Var_Decl>      ::= "VAR" <ID> "=" <Expression>

<Plan>          ::= "PLAN" <Block>

<Block>         ::= "{" <Statement>* "}"

<Statement>     ::= <Var_Decl>              /* declaracao local ao bloco */
                  | <Assign_Stmt>
                  | <Study_Stmt>
                  | <If_Stmt>
                  | <ForEach_Stmt>

<Assign_Stmt>   ::= <ID> "=" <Expression>

<Study_Stmt>    ::= "STUDY" ( <STRING> | <ID> ) "FOR" <Expression> "HOURS"

<If_Stmt>       ::= "IF" "(" <Condition> ")" <Block>
                    ( "ELSE" ( <If_Stmt> | <Block> ) )?

<ForEach_Stmt>  ::= "FOR" "EACH" <ID> "IN" "[" <StringList> "]" <Block>

<StringList>    ::= <STRING> ( "," <STRING> )*

/* Condicoes: NOT > AND > OR */
<Condition>     ::= <AndCond> ( "OR" <AndCond> )*

<AndCond>       ::= <NotCond> ( "AND" <NotCond> )*

<NotCond>       ::= "NOT" <NotCond>
                  | <Expression> <RelOp> <Expression>

<RelOp>         ::= ">" | "<" | ">=" | "<=" | "==" | "!="

/* Hierarquia de expressoes matematicas */
<Expression>    ::= <Term> ( ( "+" | "-" ) <Term> )*

<Term>          ::= <Factor> ( ( "*" | "/" ) <Factor> )*

<Factor>        ::= "-" <Factor>
                  | <NUMBER>
                  | <ID>
                  | <ID> "." <Attr>         /* ex.: u.CREDITS */
                  | "(" <Expression> ")"

<Attr>          ::= "CREDITS" | "DIFFICULTY"
```

A gramática estabelece que um programa inicia-se com a identificação do estudante, seguida por um bloco opcional de declarações (recursos, UCs e variáveis globais) e termina obrigatoriamente com o bloco `PLAN`, que contém a lógica de alocação de horas e controlo de fluxo. Dentro de qualquer bloco podem ser declaradas variáveis locais, o que introduz a noção de âmbito aninhado (ver secção 3).

## 2.3. Decisões de Desenho e Propriedades da Gramática

* **Atributos de UC com acesso por iterador.** Na versão anterior, `CREDITS` e `DIFFICULTY` apareciam como *Factor* isolados, o que tornava o seu significado dependente do contexto (de que UC?). Agora só podem ser usados na forma `<ID> "." <Attr>`, onde `<ID>` é o iterador de um `FOR EACH`. Isto torna o programa mais legível e permite verificar o uso correto por semântica estática.
* **Sem ambiguidade do *dangling else*.** Os corpos do `IF` e do `ELSE` são sempre blocos delimitados por chavetas, e o `ELSE IF` é obtido pela produção `"ELSE" <If_Stmt>`, pelo que cada `ELSE` se associa sem ambiguidade ao `IF` mais próximo.
* **Associatividade.** Os operadores binários `+ - * /` são associativos à esquerda, o que resulta diretamente da forma iterativa `( op <Term> )*`.
* **Condições sem parênteses de agrupamento.** Não se permite `(<Condition>)` para evitar o conflito com `"(" <Expression> ")"` (ambos começam por `(`). O agrupamento é feito com a precedência `NOT > AND > OR` e com expressões entre parênteses dentro das comparações.
* **Determinismo (LL).** A gramática é adequada para análise descendente com lookahead reduzido: as alternativas de `<Statement>` começam em tokens distintos (`VAR`, `ID`, `STUDY`, `IF`, `FOR`); as alternativas de `<Declaration>` começam em `UC`, `RESOURCE`, `VAR`; e as duas alternativas de `<Factor>` iniciadas por `<ID>` são resolvidas olhando para o token seguinte (`.` ou não), o que corresponde a uma fatorização à esquerda: `<ID> ( "." <Attr> )?`.
* **Separação entre sintaxe e semântica.** A gramática aceita programas como o Exemplo 3 (secção 1.4): as violações (UC não declarada, excesso de horas, variável fora de âmbito, etc.) não são detetáveis apenas pela sintaxe e são tratadas na especificação semântica (secção 3).
