# 3. Especificação Semântica (rascunho)

Esta secção identifica as propriedades da *StudyLang* que não podem ser determinadas apenas pela sintaxe e especifica as principais através de uma gramática de atributos.

## 3.1. Propriedades Semânticas

| # | Propriedade | Exemplo de violação (Ex. 3) | Atributos envolvidos |
|---|---|---|---|
| P1 | Uma UC só pode ser declarada uma vez (pelo nome) | Erro 1 | `env` herdado, `errors` sintetizado |
| P2 | No máximo uma declaração `RESOURCE TIME` | – | `nres` sintetizado |
| P3 | Uma UC estudada (`STUDY "nome"`) ou listada num `FOR EACH` tem de estar declarada | Erro 3 | `env` herdado |
| P4 | Uma variável só pode ser usada/atribuída se estiver declarada e visível (âmbito estático por bloco) | Erros 4 e 6 | `env` herdado |
| P5 | Não se pode redeclarar um nome no mesmo bloco (shadowing só em blocos internos) | Erro 5 | `env` com níveis de âmbito |
| P6 | `id.CREDITS` / `id.DIFFICULTY` só são válidos se `id` for iterador de uma UC | Erro 7 | `env` (tipo de cada nome) |
| P7 | Tipos: expressões são `int`, condições são `bool`; uma UC não pode ser usada como número | – | `type` sintetizado |
| P8 | Divisão por zero constante é proibida | Erro 8 | `const`, `val` sintetizados |
| P9 | As horas garantidamente alocadas não podem exceder `RESOURCE TIME` | Erro 2 | `minHours` sintetizado, `limit` |

## 3.2. Modelo de Valores e Ambiente

**Tipos dos nomes** (guardados no ambiente): `uc` (UC declarada por nome), `var` (variável inteira) e `iter` (iterador de `FOR EACH`, que referencia uma UC).

**Ambiente `env`:** pilha de âmbitos; cada âmbito é um conjunto de pares *(nome, tipo)*. Operações:

* `enterScope(env)` – cria um novo âmbito vazio no topo da pilha;
* `add(env, n, t)` – adiciona *(n, t)* ao âmbito do topo;
* `lookup(env, n)` – procura *n* do topo para a base e devolve o tipo, ou `⊥` se não existir;
* `inCurrentScope(env, n)` – verdadeiro se *n* existe no âmbito do topo.

Os nomes de UCs (`STRING`) e de variáveis/iteradores (`ID`) vivem em espaços de nomes separados; para a tabela, escreve-se `uc:"Nome"` para a primeira e `id` para a segunda.

**Valores:** `Expression` tem os atributos `type ∈ {int, err}`, `const` (booleano: valor conhecido estaticamente) e `val` (inteiro, só significativo se `const`).

**Erros:** cada símbolo tem um atributo sintetizado `errors` (lista de mensagens); a lista final do programa é `Program.errors`.

## 3.3. Gramática normalizada para a gramática de atributos

Para evitar o operador `*` (o que complica a definição de atributos), usamos uma forma BNF equivalente à da secção 2.2:

```
Program   → STUDENT ID Decls Plan
Decls     → Decl Decls | ε
Decl      → UC_Decl | Resource_Decl | Var_Decl
UC_Decl   → UC STRING { CREDITS NUMBER DIFFICULTY NUMBER }
Resource_Decl → RESOURCE TIME NUMBER HOURS
Var_Decl  → VAR ID = Expr
Plan      → PLAN Block
Block     → { Stmts }
Stmts     → Stmt Stmts | ε
Stmt      → Var_Decl | Assign | Study | If | ForEach
Assign    → ID = Expr
Study     → STUDY STRING FOR Expr HOURS
          | STUDY ID FOR Expr HOURS
If        → IF ( Cond ) Block ElsePart
ElsePart  → ELSE If | ELSE Block | ε
ForEach   → FOR EACH ID IN [ StrList ] Block
StrList   → STRING | STRING , StrList
Expr      → Expr + Term | Expr - Term | Term
Term      → Term * Factor | Term / Factor | Factor
Factor    → - Factor | NUMBER | ID | ID . Attr | ( Expr )
Cond      → Cond OR AndC | AndC
AndC      → AndC AND NotC | NotC
NotC      → NOT NotC | Expr RelOp Expr
```

## 3.4. Atributos

| Símbolo | Herdados (↓) | Sintetizados (↑) |
|---|---|---|
| `Decls`, `Decl` | `env_in` | `env_out`, `errors`, `nres`, `limit` |
| `Plan`, `Block`, `Stmts`, `Stmt`, `If`, `ElsePart`, `ForEach` | `env_in` | `env_out` (apenas `Stmts`/`Stmt`), `errors`, `minHours` |
| `Expr`, `Term`, `Factor`, `Cond`, `AndC`, `NotC` | `env` | `type`, `const`, `val`, `errors` |
| `StrList` | `env` | `errors`, `count` |
| `Program` | – | `errors` |

`minHours` é um limite inferior do número de horas que o plano aloca com certeza; só conta alocações cujo valor é constante. Deste modo, a verificação P9 nunca produz falsos positivos (se reporta excesso, o excesso existe).

## 3.5. Regras Semânticas

Notação: `A.x` é o atributo `x` do símbolo `A`; `++` concatena listas; `[]` é a lista vazia; `msg(...)` é uma mensagem de erro.

### 3.5.1. Programa e declarações

```
Program → STUDENT ID Decls Plan
    Decls.env_in  = emptyEnv()                  // um unico ambito global
    Plan.env_in   = Decls.env_out
    Program.errors = Decls.errors ++ Plan.errors
                     ++ (if Decls.nres > 1 then [msg("mais do que um RESOURCE")] else [])
                     ++ (if Decls.nres == 1 and Plan.minHours > Decls.limit
                         then [msg("horas excedem RESOURCE TIME")] else [])      // P2, P9

Decls → Decl Decls1
    Decl.env_in   = Decls.env_in
    Decls1.env_in = Decl.env_out
    Decls.env_out = Decls1.env_out
    Decls.errors  = Decl.errors ++ Decls1.errors
    Decls.nres    = Decl.nres + Decls1.nres
    Decls.limit   = Decl.limit + Decls1.limit   // so e relevante quando nres == 1

Decls → ε
    Decls.env_out = Decls.env_in
    Decls.errors  = []   Decls.nres = 0   Decls.limit = 0

Decl → UC_Decl | Resource_Decl | Var_Decl        // regra de copia
    (os atributos de Decl sao os do filho; o filho recebe Decl.env_in)

UC_Decl → UC STRING { CREDITS NUMBER1 DIFFICULTY NUMBER2 }
    UC_Decl.errors  = if lookup(env_in, uc:STRING.lexeme) ≠ ⊥
                      then [msg("UC repetida")] else []                           // P1
    UC_Decl.env_out = add(env_in, uc:STRING.lexeme, uc)
    UC_Decl.nres = 0   UC_Decl.limit = 0

Resource_Decl → RESOURCE TIME NUMBER HOURS
    Resource_Decl.env_out = Resource_Decl.env_in
    Resource_Decl.errors  = []
    Resource_Decl.nres    = 1
    Resource_Decl.limit   = NUMBER.val

Var_Decl → VAR ID = Expr
    Expr.env = Var_Decl.env_in
    Var_Decl.errors = Expr.errors
        ++ (if inCurrentScope(env_in, ID.lexeme) then [msg("redeclaracao")] else [])  // P5
        ++ (if Expr.type ≠ int then [msg("tipo")] else [])                            // P7
    Var_Decl.env_out = add(env_in, ID.lexeme, var)
    Var_Decl.nres = 0   Var_Decl.limit = 0
```

### 3.5.2. Blocos e instruções

```
Plan → PLAN Block
    Block.env_in = Plan.env_in
    Plan.errors = Block.errors      Plan.minHours = Block.minHours

Block → { Stmts }
    Stmts.env_in = enterScope(Block.env_in)       // novo ambito; env_out de Stmts e descartado
    Block.errors = Stmts.errors     Block.minHours = Stmts.minHours

Stmts → Stmt Stmts1
    Stmt.env_in   = Stmts.env_in
    Stmts1.env_in = Stmt.env_out                  // a declaracao em Stmt fica visivel a seguir
    Stmts.errors   = Stmt.errors ++ Stmts1.errors
    Stmts.minHours = Stmt.minHours + Stmts1.minHours

Stmts → ε
    Stmts.errors = []    Stmts.minHours = 0

Stmt → Var_Decl
    Var_Decl.env_in = Stmt.env_in    Stmt.env_out = Var_Decl.env_out
    Stmt.errors = Var_Decl.errors    Stmt.minHours = 0

Stmt → Assign | Study | If | ForEach        // as restantes alternativas
    X.env_in = Stmt.env_in           Stmt.env_out = Stmt.env_in         // nao declaram nomes
    Stmt.errors = X.errors           Stmt.minHours = X.minHours

Assign → ID = Expr
    Expr.env = Assign.env_in
    Assign.errors = Expr.errors
        ++ (if lookup(env_in, ID.lexeme) ≠ var then [msg("variavel nao declarada")] else [])  // P4
        ++ (if Expr.type ≠ int then [msg("tipo")] else [])                                    // P7
    Assign.minHours = 0

Study → STUDY STRING FOR Expr HOURS
    Expr.env = Study.env_in
    Study.errors = Expr.errors
        ++ (if lookup(env_in, uc:STRING.lexeme) ≠ uc then [msg("UC nao declarada")] else [])  // P3
        ++ (if Expr.type ≠ int then [msg("tipo")] else [])
    Study.minHours = if Expr.const then Expr.val else 0

Study → STUDY ID FOR Expr HOURS
    Expr.env = Study.env_in
    Study.errors = Expr.errors
        ++ (if lookup(env_in, ID.lexeme) ≠ iter then [msg("ID nao e iterador de UC")] else [])  // P4/P6
        ++ (if Expr.type ≠ int then [msg("tipo")] else [])
    Study.minHours = if Expr.const then Expr.val else 0
```

### 3.5.3. Controlo de fluxo

```
If → IF ( Cond ) Block ElsePart
    Cond.env = If.env_in
    Block.env_in = If.env_in        ElsePart.env_in = If.env_in
    If.errors = Cond.errors ++ Block.errors ++ ElsePart.errors
    If.minHours = min(Block.minHours, ElsePart.minHours)     // ramo mais pobre (garantido)

ElsePart → ELSE If       // ElsePart.errors e minHours = os de If, If.env_in = ElsePart.env_in
ElsePart → ELSE Block    // idem com Block
ElsePart → ε
    ElsePart.errors = []     ElsePart.minHours = 0           // sem ELSE, nenhuma hora garantida

ForEach → FOR EACH ID IN [ StrList ] Block
    StrList.env = ForEach.env_in
    Block.env_in = add(enterScope(ForEach.env_in), ID.lexeme, iter)   // iterador local ao ciclo
    ForEach.errors = StrList.errors ++ Block.errors
    ForEach.minHours = StrList.count * Block.minHours

StrList → STRING
    StrList.count = 1
    StrList.errors = (if lookup(env, uc:STRING.lexeme) ≠ uc then [msg("UC nao declarada")] else [])  // P3
StrList → STRING , StrList1
    StrList1.env = StrList.env
    StrList.count = 1 + StrList1.count
    StrList.errors = StrList1.errors
        ++ (if lookup(env, uc:STRING.lexeme) ≠ uc then [msg("UC nao declarada")] else [])
```

> Nota: como o `Block` de um `ForEach` não sabe qual a UC concreta em cada iteração, as expressões que usam `u.CREDITS` ou `u.DIFFICULTY` têm `const = false` e contribuem com 0 para `minHours` (ver 3.5.4). O limite continua a ser um limite inferior válido. Uma extensão possível é avaliar o corpo uma vez por UC da lista, com o iterador ligado aos atributos concretos.

### 3.5.4. Expressões e condições

```
Expr → Expr1 + Term | Expr1 - Term
    Expr1.env = Expr.env     Term.env = Expr.env
    Expr.type  = if Expr1.type == int and Term.type == int then int else err
    Expr.const = Expr1.const and Term.const
    Expr.val   = Expr1.val (+|-) Term.val            // so significativo se const
    Expr.errors = Expr1.errors ++ Term.errors
Expr → Term                                           // regra de copia

Term → Term1 * Factor
    (analogo a + e -)
Term → Term1 / Factor
    Term.type  = if Term1.type == int and Factor.type == int then int else err
    Term.const = Term1.const and Factor.const and Factor.val ≠ 0
    Term.val   = Term1.val / Factor.val                // divisao inteira
    Term.errors = Term1.errors ++ Factor.errors
        ++ (if Factor.const and Factor.val == 0 then [msg("divisao por zero")] else [])       // P8
Term → Factor                                          // regra de copia

Factor → NUMBER
    Factor.type = int    Factor.const = true    Factor.val = NUMBER.val    Factor.errors = []

Factor → ID
    Factor.const = false
    Factor.type  = if lookup(env, ID.lexeme) == var then int else err
    Factor.errors = (if lookup(env, ID.lexeme) == ⊥ then [msg("nao declarado")]             // P4
                     else if lookup(env, ID.lexeme) ≠ var then [msg("nao e numerico")] else [])  // P7

Factor → ID . Attr
    Factor.const = false
    Factor.type  = if lookup(env, ID.lexeme) == iter then int else err
    Factor.errors = (if lookup(env, ID.lexeme) ≠ iter then [msg("so iteradores tem atributos")] else [])  // P6

Factor → - Factor1
    Factor.type = Factor1.type    Factor.const = Factor1.const    Factor.val = -Factor1.val
Factor → ( Expr )                                      // regra de copia

NotC → Expr1 RelOp Expr2
    NotC.type = bool
    NotC.errors = Expr1.errors ++ Expr2.errors
        ++ (if Expr1.type ≠ int or Expr2.type ≠ int then [msg("tipo")] else [])
NotC → NOT NotC1                                       // propagar errors; type = bool
AndC, Cond                                             // concatenar errors dos filhos; type = bool
```

## 3.6. Dependências e Avaliação

* **Atributos herdados:** `env_in` (e `env` nas expressões) fluem de cima para baixo e da esquerda para a direita (o `env_out` de uma declaração é o `env_in` da seguinte): é uma dependência *L-atribuída*.
* **Atributos sintetizados:** `type`, `const`, `val`, `errors`, `minHours`, `count`, `nres`, `limit` e `env_out` fluem das folhas para a raiz.
* **Ordem de avaliação:** como todas as dependências respeitam o sentido da árvore (herdados só dependem do pai e dos irmãos à esquerda; sintetizados dependem dos filhos), a gramática é **L-atribuída**, o que permite avaliar todos os atributos numa única passagem em profundidade (da esquerda para a direita), podendo ser integrada diretamente num analisador descendente. O grafo de dependências é acíclico.

### Exemplo de avaliação (Exemplo 3, `STUDY "Fisica" FOR 2 HOURS`)

1. `Decls.env_out` contém `uc:"Matematica"` (a segunda declaração gera erro P1 mas não altera o ambiente).
2. `Plan.env_in = Decls.env_out`; `Block.env_in` idêntico; `Stmts.env_in = enterScope(...)`.
3. `Study.env_in` contém apenas `uc:"Matematica"`; `lookup(env_in, uc:"Fisica") = ⊥` ⇒ `Study.errors = [ "UC nao declarada" ]`.
4. `Expr.const = true`, `Expr.val = 2` ⇒ `Study.minHours = 2`, que se soma aos 10 do primeiro `STUDY`; em `Program`, `12 > 5` ⇒ erro P9.

## 3.7. Qualidade da Linguagem e da Gramática (rascunho)

| Propriedade | Avaliação |
|---|---|
| **Adequação ao domínio** | As construções (`UC`, `RESOURCE`, `PLAN`, `STUDY`, `FOR EACH`) correspondem diretamente aos conceitos do estudante; não é uma linguagem imperativa genérica. |
| **Legibilidade / expressividade** | Palavras-chave em inglês próximas da linguagem natural (`STUDY "X" FOR 8 HOURS`). Limite: só inteiros, só UCs listadas por nome. |
| **Ausência de ambiguidade** | Sem *dangling else* (blocos com chavetas); precedência e associatividade codificadas na própria gramática. |
| **Determinismo / analisabilidade** | Adequada a análise LL com 1 token de lookahead (com a fatorização `ID ("." Attr)?`). |
| **Minimalidade** | Sem produções inúteis ou inalcançáveis; `<Declaration>*` vs `<Statement>*` mantêm-se separados porque `RESOURCE` e `UC` só fazem sentido no âmbito global. |
| **Modularidade da gramática** | Expressões, condições, declarações e instruções ficam em grupos independentes, reutilizáveis. |
| **Limitações assumidas** | `minHours` é só um limite inferior; não existe verificação de pré-requisitos entre UCs nem tipos além de `int`/`bool`/`uc`. |
