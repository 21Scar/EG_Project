# 3. Especificação Semântica

Esta secção identifica as propriedades da *StudyLang* que não podem ser determinadas apenas pela sintaxe e especifica-as através de uma gramática de atributos (AG). A AG é avaliada pelo verificador `check_studylang.py`, que percorre a árvore devolvida pelo `Lark` e calcula os atributos descritos abaixo; cada função do verificador corresponde a um grupo de produções (ver 3.6).

## 3.1. Propriedades Semânticas

| # | Propriedade | Onde é violada nos exemplos |
|---|---|---|
| P1 | Uma UC só pode ser declarada uma vez (identificada pelo nome) | Ex. 3, linha 4 |
| P2 | No máximo uma declaração `RESOURCE TIME` | Ex. 4, linha 1 |
| P3 | `CREDITS` depende do nível: obrigatório em cada UC de `UNIVERSITY`; proibido em `SECONDARY`, tanto na declaração da UC como em `u.CREDITS` | Ex. 4, linha 2; Ex. 3, linhas 3 e 20 |
| P4 | Uma UC referida em `STUDY "nome"` ou na lista de um `FOR EACH` tem de estar declarada; `STUDY id` exige que `id` seja o iterador de um `FOR EACH` | Ex. 3, linha 10 |
| P5 | Um nome usado numa expressão ou atribuído tem de estar declarado e visível (âmbito estático por bloco); a atribuição só é válida sobre uma variável | Ex. 3, linhas 11 e 17 |
| P6 | Não é permitido redeclarar um nome no mesmo bloco (o *shadowing* em blocos interiores é permitido) | Ex. 3, linha 14 |
| P7 | Só um iterador tem atributos: `id.CREDITS` / `id.DIFFICULTY` exigem que `id` seja iterador de UC | Ex. 3, linha 22 |
| P8 | Tipos: as expressões são inteiras; um iterador não pode ser usado como número; as comparações são entre inteiros; as horas são inteiras | (sem exemplo dedicado) |
| P9 | Divisão por zero constante é proibida | Ex. 3, linha 23 |
| P10 | As horas de um `STUDY` têm de ser positivas (quando constantes) | Ex. 4, linha 5 |
| P11 | As horas garantidas pelo plano não podem exceder `RESOURCE TIME` (se existir exatamente um `RESOURCE`) | Ex. 3, linha 8 (12 > 5) |

Resultado de `python check_studylang.py` sobre os exemplos da secção 1.4:

```text
=== Ex1 - universitário (válido) ===
OK: sintaxe e semântica válidas
=== Ex2 - secundário (válido) ===
OK: sintaxe e semântica válidas
=== Ex3 - secundário (10 erros semânticos) ===
  linha 3: UC "Matematica": CREDITS não existe no nível SECONDARY
  linha 4: UC "Matematica" repetida
  linha 8: horas garantidas (12) excedem RESOURCE TIME (5)
  linha 10: UC "Fisica" não declarada
  linha 11: 'total' não é uma variável declarada
  linha 14: redeclaração de 'x' no mesmo bloco
  linha 17: 'y' não declarado
  linha 20: CREDITS não existe no nível SECONDARY
  linha 22: 'x' não é iterador de UC (não tem DIFFICULTY)
  linha 23: divisão por zero
=== Ex4 - universitário (erros de nível) ===
  linha 1: mais do que um RESOURCE
  linha 2: UC "Redes": CREDITS obrigatório no nível UNIVERSITY
  linha 5: horas têm de ser positivas
=== Ex5 - erro sintático (falta LEVEL) ===
ERRO SINTÁTICO (linha 2, col 1): token inesperado
```

## 3.2. Modelo de Ambiente

**Tipos dos nomes** guardados no ambiente: `uc` (UC declarada), `var` (variável inteira) e `iter` (iterador de `FOR EACH`, que referencia uma UC). Os nomes de UCs (as *strings*) e os nomes de variáveis/iteradores (os `ID`) vivem em **espaços de nomes separados**: escreve-se `uc:"Nome"` para os primeiros e `id:nome` para os segundos.

**Ambiente `env`:** o nível do estudante (`level ∈ {uni, sec}`) e uma pilha de âmbitos, cada um um conjunto de pares *(chave, tipo)*. Operações:

* `enter(env)` cria um novo âmbito vazio no topo da pilha (herdando os visíveis);
* `add(env, k, t)` acrescenta *(k, t)* ao âmbito do topo;
* `lookup(env, k)` procura *k* do topo para a base e devolve o tipo, ou `⊥` se não existir;
* `inCurrent(env, k)` é verdadeiro se *k* existe no âmbito do topo.

**Valores de expressões:** cada expressão tem os atributos `type ∈ {int, err}`, `const` (booleano: valor conhecido estaticamente) e `val` (inteiro, só significativo se `const`).

## 3.3. Atributos

| Símbolo | Herdados (↓) | Sintetizados (↑) |
|---|---|---|
| `start` | – | `errors` |
| `decl` (`uc_decl`, `resource_decl`, `var_decl`) | `env_in` | `env_out`, `errors`, `nres`, `limit` |
| `plan`, `block`, `stmt`, `if_stmt`, `else_part`, `foreach_stmt` | `env_in` | `env_out` (só `stmt`), `errors`, `minHours` |
| `expr`, `cond` e subexpressões | `env` | `type`, `const`, `val`, `errors` |
| `string_list` | `env` | `errors`, `count` |

`level` é herdado da raiz e propagado sem alteração (está dentro de `env`). `minHours` é um **limite inferior** das horas que o plano aloca com certeza: só conta alocações de valor constante, pelo que a verificação P11 nunca produz falsos positivos (se reporta excesso, o excesso existe).

## 3.4. Regras Semânticas

Notação: `A.x` é o atributo `x` do símbolo `A`; `++` concatena listas de erros; `[]` é a lista vazia.

### 3.4.1. Programa e declarações

```
start → STUDENT ID LEVEL level decl* plan
    env_0        = emptyEnv(level.kind)               // level.kind = uni | sec
    decl_i.env_in = decl_{i-1}.env_out                 // encadeamento da esquerda para a direita
    plan.env_in  = decl_n.env_out
    nres         = Σ decl_i.nres      limit = limit do último RESOURCE
    start.errors = ⋃ decl_i.errors ++ plan.errors
        ++ (if nres > 1 then [erro "mais do que um RESOURCE"])                          // P2
        ++ (if nres == 1 and plan.minHours > limit then [erro "horas garantidas excedem RESOURCE TIME"])  // P11

uc_decl → UC STRING { credits? difficulty }
    uc_decl.errors =
          (if lookup(env_in, uc:STRING) ≠ ⊥ then [erro "UC repetida"])                 // P1
       ++ (if level == uni and credits ausente  then [erro "CREDITS obrigatório"])     // P3
       ++ (if level == sec and credits presente then [erro "CREDITS não existe"])      // P3
    uc_decl.env_out = add(env_in, uc:STRING, uc)

resource_decl → RESOURCE TIME INT HOURS
    resource_decl.env_out = env_in
    resource_decl.nres = 1       resource_decl.limit = INT.val

var_decl → VAR ID = expr
    expr.env = var_decl.env_in
    var_decl.errors = expr.errors
        ++ (if inCurrent(env_in, id:ID) then [erro "redeclaração"])                   // P6
        ++ (if expr.type ≠ int and expr.errors == [] then [erro "tipo"])              // P8
    var_decl.env_out = add(env_in, id:ID, var)
```

### 3.4.2. Blocos e instruções

```
plan → PLAN block
    block.env_in = plan.env_in
    plan.errors  = block.errors       plan.minHours = block.minHours

block → { stmt* }
    stmt_1.env_in = enter(block.env_in)               // novo âmbito; o env_out do último stmt é descartado
    stmt_i.env_in = stmt_{i-1}.env_out
    block.errors   = ⋃ stmt_i.errors
    block.minHours = Σ stmt_i.minHours

stmt → var_decl
    stmt.env_out = var_decl.env_out       stmt.minHours = 0      // a declaração fica visível nas instruções seguintes
stmt → assign_stmt | study_stmt | if_stmt | foreach_stmt
    stmt.env_out = stmt.env_in            // estas instruções não declaram nomes no bloco

assign_stmt → ID = expr
    expr.env = env_in
    assign_stmt.errors = expr.errors
        ++ (if lookup(env_in, id:ID) ≠ var then [erro "não é uma variável declarada"])  // P5
        ++ (if expr.type ≠ int and expr.errors == [] then [erro "tipo"])                // P8
    assign_stmt.minHours = 0

study_stmt → STUDY STRING FOR expr HOURS
    expr.env = env_in
    study_stmt.errors = expr.errors
        ++ (if expr.type ≠ int and expr.errors == [] then [erro "horas têm de ser inteiras"])       // P8
        ++ (if expr.const and expr.val ≤ 0 then [erro "horas têm de ser positivas"])                // P10
        ++ (if lookup(env_in, uc:STRING) ≠ uc then [erro "UC não declarada"])                       // P4
    study_stmt.minHours = (expr.val if expr.const and expr.val > 0 else 0)

study_stmt → STUDY ID FOR expr HOURS
    (igual, mas a verificação P4 é: lookup(env_in, id:ID) ≠ iter → erro "não é iterador de UC")
```

### 3.4.3. Controlo de fluxo

```
if_stmt → IF ( cond ) block else_part?
    cond.env = env_in      block.env_in = env_in      else_part.env_in = env_in
    if_stmt.errors   = cond.errors ++ block.errors ++ else_part.errors
    if_stmt.minHours = min(block.minHours, else_part.minHours)   // sem ELSE: else_part.minHours = 0

else_part → ELSE if_stmt | ELSE block
    else_part.errors / minHours = os do filho

foreach_stmt → FOR EACH ID IN [ string_list ] block
    string_list.env = env_in
    block.env_in    = add(enter(env_in), id:ID, iter)           // o iterador só existe no corpo do ciclo
    foreach_stmt.errors   = string_list.errors ++ block.errors
    foreach_stmt.minHours = string_list.count * block.minHours

string_list → STRING (, STRING)*
    string_list.count  = número de STRING
    string_list.errors = ⋃ (if lookup(env, uc:STRING_i) ≠ uc then [erro "UC não declarada"])    // P4
```

> Dentro de um ciclo, as expressões que usam `u.CREDITS` ou `u.DIFFICULTY` têm `const = false` (o valor depende da UC em cada iteração) e contribuem com 0 para `minHours`. O limite continua a ser um limite inferior válido. Uma extensão possível é avaliar o corpo uma vez por UC da lista, com o iterador ligado aos atributos concretos.

### 3.4.4. Expressões e condições

```
expr → INT
    type = int     const = true      val = INT.val

expr → ID                                                              // factor "var"
    const = false
    type  = int if lookup(env, id:ID) == var else err
    errors = (if lookup == ⊥ then [erro "não declarado"]               // P5
              else if lookup ≠ var then [erro "não é numérico"])       // P8

expr → ID . attr_name                                                  // factor "attr"
    const = false
    errors = (if lookup(env, id:ID) ≠ iter then [erro "não é iterador de UC"]                   // P7
              else if attr_name == CREDITS and level == sec then [erro "CREDITS não existe"])   // P3
    type = int if errors == [] else err

expr → - expr1
    type, const = os de expr1      val = -expr1.val

expr → expr1 (+ | - | *) expr2
    type   = int if expr1.type == int and expr2.type == int else err
    const  = expr1.const and expr2.const
    val    = expr1.val (op) expr2.val                  // só se const
    errors = expr1.errors ++ expr2.errors

expr → expr1 / expr2
    (igual às anteriores, com const = expr1.const and expr2.const and expr2.val ≠ 0
     e, em errors, + (if expr2.const and expr2.val == 0 then [erro "divisão por zero"]))       // P9

cond → expr1 REL_OP expr2                              // "compare"
    cond.errors = expr1.errors ++ expr2.errors
        ++ (if expr1.type ≠ int or expr2.type ≠ int then [erro "comparação exige inteiros"])  // P8
cond → cond1 OR cond2 | cond1 AND cond2 | NOT cond1
    cond.errors = concatenação dos errors dos filhos
```

## 3.5. Dependências e Ordem de Avaliação

* **Herdados:** `env_in` (e `env` nas expressões) fluem de cima para baixo e da esquerda para a direita: o `env_out` de uma declaração ou instrução é o `env_in` da seguinte, e o do `foreach_stmt` é construído a partir do do pai.
* **Sintetizados:** `type`, `const`, `val`, `errors`, `minHours`, `count`, `nres`, `limit` e `env_out` fluem das folhas para a raiz.
* **L-atribuída:** os atributos herdados de um símbolo dependem apenas do pai e dos irmãos à sua esquerda; os sintetizados, só dos filhos. O grafo de dependências é acíclico, e todos os atributos podem ser avaliados numa única passagem em profundidade, da esquerda para a direita, que é o que o verificador faz.

### Exemplo de avaliação (Ex. 3, linhas 8 e 10)

1. `start` cria `env_0` com `level = sec`. A primeira `uc_decl` ("Matematica", com `CREDITS`) gera o erro P3 (`CREDITS` no secundário), mas acrescenta `uc:"Matematica"` ao ambiente; a segunda gera P1 (UC repetida).
2. `plan.env_in = decl_n.env_out`; `block` cria um âmbito novo com `enter`.
3. `STUDY "Matematica" FOR 10 HOURS`: `lookup(env_in, uc:"Matematica") == uc` (sem erro); `expr.const = true`, `expr.val = 10` ⇒ `minHours = 10`.
4. `STUDY "Fisica" FOR 2 HOURS`: `lookup(env_in, uc:"Fisica") == ⊥` ⇒ erro P4; `minHours = 2`.
5. `block.minHours = 10 + 2 = 12`; em `start`, `nres == 1` e `12 > limit = 5` ⇒ erro P11 ("horas garantidas (12) excedem RESOURCE TIME (5)").

## 3.6. Correspondência com o Código

| Parte da AG | Função em `check_studylang.py` |
|---|---|
| `start`, declarações globais, P1/P2/P3/P11 | `check()` |
| `var_decl` | `var_decl()` |
| `block`, `stmt` | `block()`, `stmt()` |
| `if_stmt`, `else_part` | `if_stmt()` |
| `foreach_stmt`, `string_list` | `foreach()` |
| horas de um `STUDY` (P8, P10) | `check_hours()` |
| `expr` (tipos, `const`, `val`, P5, P7, P9) | `expr()` |
| `cond` | `cond()` |
| ambiente | classe `Env` |

O verificador não usa uma ferramenta de AG (como o `LarkAG`): as regras são avaliadas por funções recursivas que devolvem os atributos sintetizados e recebem o ambiente como argumento. Isto corresponde diretamente à AG acima, por ser L-atribuída.

## 3.7. Qualidade da Linguagem e da Gramática (rascunho)

| Propriedade | Avaliação |
|---|---|
| **Adequação ao domínio** | As construções (`UC`, `RESOURCE`, `PLAN`, `STUDY`, `FOR EACH`, `LEVEL`) correspondem diretamente a conceitos do planeamento de estudo; não é uma linguagem imperativa genérica. |
| **Legibilidade** | Palavras-chave em inglês próximas da linguagem natural (`STUDY "X" FOR 8 HOURS`); a estrutura em blocos e a identação são claras. |
| **Ausência de ambiguidade** | Gramática LALR(1) sem conflitos; sem *dangling else*; precedência e associatividade codificadas na própria gramática. |
| **Separação sintaxe/semântica** | Uma só gramática para os dois níveis; as regras que dependem do nível (`CREDITS`) estão na AG, que conhece o `level`. |
| **Minimalidade** | Sem produções inúteis; um só mecanismo de repetição (`FOR EACH`) e um de ramificação (`IF`), suficientes para o domínio. |
| **Verificabilidade** | Erros semânticos localizados (linha e mensagem) e testados em cinco exemplos, incluindo erros sintáticos. |
| **Limitações assumidas** | `minHours` é só um limite inferior (valores que dependem de `u.CREDITS` ou `u.DIFFICULTY` não contam); só existem inteiros; não há limite diário de horas nem pré-requisitos entre UCs; `STUDY` por nome só aceita *strings* literais; as condições não aceitam parênteses de agrupamento. |