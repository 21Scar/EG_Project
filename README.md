# EG_Project — StudyLang

Projeto de Engenharia Gramatical 2026/2027, Parte I: Engenharia de Linguagens e Gramáticas.

## 1. A linguagem

A **StudyLang** é uma DSL para **planear e validar planos de estudo**. O estudante declara o seu nível de ensino, as UCs/disciplinas (com dificuldade e, no universitário, créditos ECTS) e o tempo disponível. Depois escreve um `PLAN` que distribui horas de estudo pelas UCs. A linguagem verifica se o plano respeita as regras do domínio: UCs declaradas, horas disponíveis, créditos de acordo com o nível, etc.

```study
STUDENT Leonor LEVEL UNIVERSITY

UC "Engenharia Gramatical" { CREDITS 6 DIFFICULTY 5 }
UC "Redes"                 { CREDITS 3 DIFFICULTY 2 }

RESOURCE TIME 30 HOURS
VAR max_session = 4

PLAN {
    FOR EACH u IN [ "Engenharia Gramatical", "Redes" ] {
        VAR h = u.CREDITS * 2
        IF ( u.DIFFICULTY > 3 AND h <= max_session * 3 ) {
            STUDY u FOR h HOURS
        } ELSE {
            STUDY u FOR 2 HOURS
        }
    }
}
```

**Utilizadores:** estudantes do ensino universitário (`UNIVERSITY`) e secundário (`SECONDARY`).

**Conceitos principais:** estudante e nível (`STUDENT`, `LEVEL`), unidades curriculares (`UC`), recursos (`RESOURCE TIME`), plano (`PLAN`, `STUDY`), variáveis (`VAR`) e controlo de fluxo (`IF / ELSE IF / ELSE`, `FOR EACH`, `AND / OR / NOT`).

### Requisitos mínimos do enunciado

| Requisito | Na StudyLang |
|---|---|
| Variáveis e declarações | `VAR`, `UC`, `RESOURCE`, atribuição `x = expr` |
| Âmbitos | âmbito estático por bloco, *shadowing* permitido, sem redeclaração no mesmo bloco; o iterador do `FOR EACH` é local ao ciclo |
| Expressões e estado | aritmética inteira (`+ - * /`, `-` unário, parênteses), `u.CREDITS` / `u.DIFFICULTY`, atribuição |
| Construções aninhadas | blocos `{ }` dentro de `PLAN`, `IF` e `FOR EACH` |
| Ramificação e repetição | `IF / ELSE IF / ELSE` e `FOR EACH` |
| Semântica não sintática | 11 propriedades verificadas pela gramática de atributos (secção 4) |

## 2. Estrutura do repositório

| Ficheiro | Conteúdo |
|---|---|
| [fase_1_desenho_da_linguagem.md](fase_1_desenho_da_linguagem.md) | Tarefa 1: domínio, propósito, conceitos e exemplos de programas |
| [fase_2_especifica_o_lexical_e_sint_tica.md](fase_2_especifica_o_lexical_e_sint_tica.md) | Tarefa 2: léxico, gramática em EBNF e decisões de desenho |
| [fase_3_especificacao_semantica.md](fase_3_especificacao_semantica.md) | Tarefa 3: propriedades semânticas e gramática de atributos |
| [fase_4_qualidade.md](fase_4_qualidade.md) | Tarefa 4: qualidade da linguagem, da gramática e da gramática de atributos |
| [studylang.lark](studylang.lark) | Gramática implementada em Lark (LALR(1)) |
| [check_studylang.py](check_studylang.py) | Parser e avaliador da gramática de atributos, com os exemplos de teste |
| [metricas.py](metricas.py) | Cálculo das métricas da gramática usadas na fase 4 |

## 3. Especificação lexical e sintática: decisões principais

- **Uma só gramática para os dois níveis.** `CREDITS` é opcional na sintaxe. A obrigação (universitário) ou a proibição (secundário) é verificada na semântica, que conhece o nível. Assim, não precisamos de duas gramáticas.
- **Sem *dangling else*.** Os corpos de `IF`/`ELSE` são sempre blocos com chavetas, e o `ELSE IF` é `ELSE` seguido de um `if_stmt`.
- **Precedência na gramática.** `* /` têm precedência sobre `+ -`, ambos associativos à esquerda. Nas condições, `NOT` > `AND` > `OR`.
- **Atributos só através de iterador.** `u.CREDITS` e `u.DIFFICULTY` só são válidos quando `u` é o iterador de um `FOR EACH`.
- **LALR(1) sem conflitos.** O Lark constrói a tabela sem conflitos, por isso a gramática não é ambígua.
- **Lexer `basic`.** Com o lexer contextual (o *default*), uma palavra reservada seria aceite como nome (`VAR STUDY = 1`). Com o `basic`, as palavras reservadas são de facto reservadas.
- **Comentários** de linha `//` e espaços em branco são ignorados.

## 4. Especificação semântica (gramática de atributos)

Propriedades verificadas:

| # | Propriedade |
|---|---|
| P1 | Uma UC só pode ser declarada uma vez |
| P2 | No máximo um `RESOURCE TIME` |
| P3 | `CREDITS` obrigatório em `UNIVERSITY` e proibido em `SECONDARY` (na declaração e em `u.CREDITS`) |
| P4 | As UCs usadas em `STUDY` e em `FOR EACH` têm de estar declaradas |
| P5 | As variáveis usadas têm de estar declaradas e visíveis |
| P6 | Não se pode redeclarar um nome no mesmo bloco |
| P7 | Só um iterador de UC tem atributos (`x.DIFFICULTY` com `x` variável é erro) |
| P8 | Tipos: expressões, comparações e horas são inteiras |
| P9 | Divisão por zero constante |
| P10 | As horas de um `STUDY` têm de ser positivas |
| P11 | As horas garantidas pelo plano não podem exceder o `RESOURCE TIME` |

**Atributos:**
- **herdados:** `env`, com o nível do estudante e uma pilha de âmbitos, e `nres_in` / `limit_in`, o número de `RESOURCE` já vistos e o limite de horas;
- **sintetizados:** `errors`, `type`, `const`, `val`, `minHours`, `count`, `nres_out`, `limit_out` e `env_out`.

`minHours` é um limite inferior das horas que o plano aloca com certeza: só conta valores constantes, por isso a verificação P11 nunca dá falsos positivos.

A gramática é **L-atribuída**: os herdados dependem só do pai e dos irmãos à esquerda. Por isso, todos os atributos são avaliados numa única passagem em profundidade, da esquerda para a direita. O `check_studylang.py` implementa essa passagem com funções recursivas, uma por grupo de produções. Não usámos o `LarkAG`. A correspondência entre regras e funções está na secção 3.6 da fase 3.

## 5. Como testar

Requer Python 3 e Lark (`pip install lark`).

```bash
python check_studylang.py
```

Exemplos incluídos e resultado esperado:

| Exemplo | Resultado |
|---|---|
| Ex1: universitário | válido |
| Ex2: secundário (âmbitos e *shadowing*) | válido |
| Ex3: secundário | 10 erros semânticos detetados (P1, P3, P4, P5, P6, P7, P9, P11) |
| Ex4: universitário | 3 erros detetados (falta `CREDITS`, segundo `RESOURCE` na linha 4, 0 horas) |
| Ex5: falta `LEVEL` | erro sintático |
| Ex6: `VAR STUDY = 1` | erro sintático (palavra reservada usada como nome) |

## 6. Qualidade da linguagem e da gramática

A avaliação completa está na [fase 4](fase_4_qualidade.md). As métricas são calculadas com `python metricas.py`. Em resumo:

**Linguagem**
- **Pontos fortes:**
  - *expressividade:* as construções correspondem a conceitos do domínio;
  - *unicidade:* há uma só forma de repetir e uma só de decidir;
  - *consistência:* palavras-chave em maiúsculas e blocos sempre com chavetas;
  - *fiabilidade:* 11 tipos de erro semântico detetados.
- **Pontos fracos:**
  - *documentação:* só há comentários `//`;
  - *extensibilidade e modularidade:* não há funções nem módulos;
  - *escalabilidade:* os nomes das UCs são repetidos em cada `FOR EACH`.

**Gramática**
- **Tamanho:** 40 terminais, 28 não-terminais e 57 produções.
- **Parser:** LALR(1) sem conflitos, com 117 estados.
- **Produções unitárias:** 15, quase todas para agrupar instruções ou para a cadeia de precedência.
- **Recursividade:** à esquerda nos operadores binários, o que lhes dá associatividade à esquerda.

**Gramática de atributos**
- **Atributos:** 13 (4 herdados e 9 sintetizados) e 20 condições de contexto.
- **Avaliação:** L-atribuída, numa só passagem. Os erros são acumulados e mostrados todos de uma vez.

**Limitações assumidas:**
- **Não há limite diário de horas** (por exemplo, impedir mais de 24 horas num dia), porque a linguagem não tem a noção de dia. Seria uma extensão possível: um bloco `DAY` e uma nova propriedade semântica.
- só existem inteiros;
- `minHours` ignora horas que dependem de `u.CREDITS` ou `u.DIFFICULTY`;
- não há pré-requisitos entre UCs;
- as condições não aceitam parênteses de agrupamento;
- `STUDY` por nome só aceita *strings* literais.
