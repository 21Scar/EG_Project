# 2. Especificação Lexical e Sintática

Nesta secção apresentamos a especificação formal da *StudyLang*. O reconhecimento da linguagem está dividido em duas partes: a definição lexical (identificação dos símbolos básicos ou *tokens*) e a especificação sintática (regras de formação de programas válidos através de uma Gramática Independente de Contexto). A especificação foi implementada em `Lark` (secção 2.4), e é essa implementação que o verificador `check_studylang.py` usa.

## 2.1. Especificação Lexical

A análise lexical converte a sequência de caracteres do código-fonte numa sequência de *tokens*. A *StudyLang* é insensível a espaços em branco (espaços, tabulações e quebras de linha), que funcionam apenas como separadores. Os **comentários de linha**, iniciados por `//` e terminados no fim da linha, são descartados pelo analisador lexical, tal como os espaços em branco.

Os *tokens* dividem-se nas seguintes categorias:

* **Palavras reservadas:** termos que fazem parte da estrutura da linguagem e não podem ser usados como nomes de variáveis. São sensíveis a maiúsculas/minúsculas (`study` é um `ID`; `STUDY` é palavra reservada).
  * `STUDENT`, `LEVEL`, `UNIVERSITY`, `SECONDARY`, `UC`, `CREDITS`, `DIFFICULTY`, `RESOURCE`, `TIME`, `HOURS`, `PLAN`, `STUDY`, `FOR`, `VAR`, `EACH`, `IN`, `IF`, `ELSE`, `AND`, `OR`, `NOT`
  * Uma palavra reservada tem prioridade sobre `ID`; um identificador que apenas *começa* por uma palavra reservada (por exemplo `HOURSx`) continua a ser um `ID`.
* **Identificadores (`ID`):** nomeiam o estudante, variáveis e iteradores. Iniciam-se com uma letra, seguida de letras, dígitos ou *underscores*.
  * Expressão regular: `[a-zA-Z][a-zA-Z0-9_]*`
* **Literais de texto (`STRING`):** sequência de caracteres (exceto aspas duplas) delimitada por aspas duplas; usados para os nomes das UCs.
  * Expressão regular: `"[^"]*"`
* **Literais numéricos (`INT`):** inteiros não negativos (os negativos obtêm-se com o operador unário `-`).
  * Expressão regular: `[0-9]+`
* **Operadores relacionais (`REL_OP`):** `>=`, `<=`, `==`, `!=`, `>`, `<`.
* **Outros operadores e pontuação:** aritméticos `+`, `-`, `*`, `/`; atribuição `=`; acesso a atributo `.`; estruturais `{`, `}`, `(`, `)`, `[`, `]`, `,`.
* **Comentários (ignorados):** `//[^\n]*`

## 2.2. Especificação Sintática (Gramática Independente de Contexto)

A sintaxe é definida por uma CFG, apresentada em notação EBNF. Os terminais entre aspas são palavras reservadas ou símbolos; `<ID>`, `<STRING>`, `<INT>` e `<REL_OP>` são os *tokens* da secção 2.1.

```ebnf
<Program>       ::= "STUDENT" <ID> "LEVEL" <Level> <Declaration>* <Plan>

<Level>         ::= "UNIVERSITY" | "SECONDARY"

<Declaration>   ::= <UC_Decl>
                  | <Resource_Decl>
                  | <Var_Decl>

<UC_Decl>       ::= "UC" <STRING> "{" <Credits>? <Difficulty> "}"
<Credits>       ::= "CREDITS" <INT>
<Difficulty>    ::= "DIFFICULTY" <INT>

<Resource_Decl> ::= "RESOURCE" "TIME" <INT> "HOURS"

<Var_Decl>      ::= "VAR" <ID> "=" <Expression>

<Plan>          ::= "PLAN" <Block>

<Block>         ::= "{" <Statement>* "}"

<Statement>     ::= <Var_Decl>              /* declaração local ao bloco */
                  | <Assign_Stmt>
                  | <Study_Stmt>
                  | <If_Stmt>
                  | <ForEach_Stmt>

<Assign_Stmt>   ::= <ID> "=" <Expression>

<Study_Stmt>    ::= "STUDY" ( <STRING> | <ID> ) "FOR" <Expression> "HOURS"

<If_Stmt>       ::= "IF" "(" <Condition> ")" <Block> <Else_Part>?
<Else_Part>     ::= "ELSE" ( <If_Stmt> | <Block> )

<ForEach_Stmt>  ::= "FOR" "EACH" <ID> "IN" "[" <StringList> "]" <Block>
<StringList>    ::= <STRING> ( "," <STRING> )*

/* Condições: NOT > AND > OR */
<Condition>     ::= <AndCond> ( "OR" <AndCond> )*
<AndCond>       ::= <NotCond> ( "AND" <NotCond> )*
<NotCond>       ::= "NOT" <NotCond>
                  | <Expression> <REL_OP> <Expression>

/* Expressões: * e / têm precedência sobre + e - */
<Expression>    ::= <Term> ( ( "+" | "-" ) <Term> )*
<Term>          ::= <Factor> ( ( "*" | "/" ) <Factor> )*
<Factor>        ::= "-" <Factor>
                  | <INT>
                  | <ID>
                  | <ID> "." <Attr>         /* ex.: u.CREDITS */
                  | "(" <Expression> ")"
<Attr>          ::= "CREDITS" | "DIFFICULTY"
```

Um programa inicia-se com a identificação do estudante e do nível, seguida de um bloco de declarações (UCs, recursos e variáveis globais) e termina com o bloco `PLAN`, que contém a lógica de alocação de horas e o controlo de fluxo. Dentro de qualquer bloco podem ser declaradas variáveis locais, o que introduz âmbitos aninhados (secção 3).

## 2.3. Decisões de Desenho e Propriedades da Gramática

* **`CREDITS` sintaticamente opcional.** A produção `<UC_Decl>` aceita uma UC com ou sem `CREDITS`. Se a gramática impusesse `CREDITS` (ou o proibisse), precisaria de duas gramáticas, uma por nível. Optou-se por uma só gramática e por verificar a obrigatoriedade (`UNIVERSITY`) ou proibição (`SECONDARY`) na especificação semântica, que conhece o nível. É um exemplo de propriedade que não depende só da sintaxe.
* **Atributos de UC acedidos por iterador.** `CREDITS` e `DIFFICULTY` só aparecem como atributo na forma `<ID> "." <Attr>`, onde `<ID>` deve ser o iterador de um `FOR EACH`. Isto evita ambiguidades sobre "de que UC" é o atributo; a verificação de que `<ID>` é um iterador é semântica.
* **Sem *dangling else*.** Os corpos de `IF` e `ELSE` são sempre blocos delimitados por chavetas, e o `ELSE IF` obtém-se com a produção `"ELSE" <If_Stmt>`, pelo que cada `ELSE` se associa sem ambiguidade ao `IF` mais próximo.
* **Precedência e associatividade.** A forma `( op <Term> )*` dá associatividade à esquerda a `+ - * /`, com `* /` mais fortes que `+ -`. Nas condições, `NOT` > `AND` > `OR`. O operando de `NOT` é uma comparação (ou outro `NOT`); não há condições entre parênteses, o que evita o conflito com `"(" <Expression> ")"`. Assim, `NOT u.DIFFICULTY > 2` significa `NOT (u.DIFFICULTY > 2)`.
* **Gramática LALR(1) e sem ambiguidade.** A implementação em `Lark` usa o analisador LALR(1); o gerador constrói a tabela de análise sem conflitos, o que garante que a gramática não é ambígua.
* **Léxico `basic`.** O analisador lexical usado é o `basic` do `Lark` (e não o contextual, que é o *default*). Com o contextual, uma palavra reservada seria aceite como `ID` onde só um `ID` é esperado (por exemplo, `VAR STUDY = 1`), contrariando a regra de que as palavras reservadas não podem ser nomes.
* **Separação entre sintaxe e semântica.** Programas como o Exemplo 3 e o Exemplo 4 (secção 1.4) são aceites pela gramática; as violações são tratadas na secção 3. O Exemplo 5 (sem `LEVEL`) é rejeitado pelo analisador sintático.

## 2.4. Gramática em Lark (implementação)

Ficheiro `studylang.lark`. Convenções: terminais em maiúsculas, não-terminais em minúsculas; `?regra` faz *inlining* de regras de passagem; `-> nome` dá nome a uma alternativa, o que facilita o processamento semântico sobre a árvore. A gramática é carregada com `Lark(..., parser="lalr", lexer="basic")`.

```lark
// =====================================================================
// StudyLang - gramática Lark (LALR(1), lexer basic)
// Versão com nível de estudante (UNIVERSITY | SECONDARY)
// =====================================================================

// ---------- Programa ----------
start: "STUDENT" ID "LEVEL" level decl* plan

level: "UNIVERSITY" -> university
     | "SECONDARY"  -> secondary

// ---------- Declarações globais ----------
?decl: uc_decl
     | resource_decl
     | var_decl

// CREDITS é sintaticamente opcional; a obrigatoriedade (universitário)
// ou proibição (secundário) é verificada na gramática de atributos.
uc_decl: "UC" STRING "{" credits? difficulty "}"
credits: CREDITS INT
difficulty: DIFFICULTY INT

resource_decl: "RESOURCE" "TIME" INT "HOURS"

var_decl: "VAR" ID "=" expr

// ---------- Plano e instruções ----------
plan: "PLAN" block
block: "{" stmt* "}"

?stmt: var_decl
     | assign_stmt
     | study_stmt
     | if_stmt
     | foreach_stmt

assign_stmt: ID "=" expr

study_stmt: "STUDY" (STRING | ID) "FOR" expr "HOURS"

// O "dangling else" não existe: os corpos são sempre blocos com chavetas
if_stmt: "IF" "(" cond ")" block else_part?
else_part: "ELSE" (if_stmt | block)

foreach_stmt: "FOR" "EACH" ID "IN" "[" string_list "]" block
string_list: STRING ("," STRING)*

// ---------- Condições: NOT > AND > OR ----------
?cond: or_cond
?or_cond: and_cond
        | or_cond "OR" and_cond   -> or_
?and_cond: not_cond
         | and_cond "AND" not_cond -> and_
?not_cond: "NOT" not_cond          -> not_
         | expr REL_OP expr        -> compare

// ---------- Expressões: * / > + -  (associativas à esquerda) ----------
?expr: term
     | expr "+" term  -> add
     | expr "-" term  -> sub
?term: factor
     | term "*" factor -> mul
     | term "/" factor -> div
?factor: "-" factor       -> neg
       | INT              -> num
       | ID               -> var
       | ID "." attr_name -> attr
       | "(" expr ")"

attr_name: CREDITS | DIFFICULTY

// ---------- Léxico ----------
// Palavras reservadas (literais entre aspas nas regras) têm prioridade
// sobre ID e são sensíveis a maiúsculas/minúsculas. Isto só é verdade com
// Lark(..., lexer="basic"); com o lexer contextual (por omissão) seriam
// aceites como ID (ex.: VAR STUDY = 1).
CREDITS: "CREDITS"
DIFFICULTY: "DIFFICULTY"

REL_OP: ">=" | "<=" | "==" | "!=" | ">" | "<"

ID: /[a-zA-Z][a-zA-Z0-9_]*/
STRING: /"[^"]*"/
INT: /[0-9]+/

COMMENT: /\/\/[^\n]*/
%import common.WS
%ignore WS
%ignore COMMENT
```