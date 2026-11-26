# EG_Project — StudyLang

Projeto de Engenharia Gramatical 2026/2027.

A **StudyLang** é uma linguagem para escrever **planos de estudo**. O aluno declara as suas UCs e o tempo disponível e escreve como distribui as horas. O projeto tem duas partes:

- **Parte I: a linguagem.** Gramática, regras de validação (gramática de atributos) e qualidade.
- **Parte II: a ferramenta.** Cada plano é convertido em **grafos** (fluxo de controlo, fluxo de dados), que são percorridos para **validar** o plano (horas reais, código inútil, instruções impossíveis) e para o **transformar** (otimizar, planificar, exportar).

## Mapa do projeto

```text
EG_Project/
│
├── studylang.py           ← A FERRAMENTA: é o único ficheiro que se corre (python studylang.py --help)
├── COMO_TESTAR.md         ← guia passo a passo para testar e rever o projeto
├── requirements.txt       ← dependências (pip install -r requirements.txt)
│
├── parte1/                ← CÓDIGO DA PARTE I: a linguagem
│   ├── gramatica.lark          sintaxe da StudyLang
│   ├── verificador.py          parser + gramática de atributos (regras P1–P11)
│   └── metricas_gramatica.py   métricas de qualidade da gramática
│
├── parte2/                ← CÓDIGO DA PARTE II: grafos, validação e transformações
│   ├── representacoes_intermedias.py   constrói os grafos de cada plano (CFG, DFG, PDG)
│   ├── analise_estatica.py             valida o plano percorrendo os grafos
│   ├── transformacoes.py               otimizar, planificar e exportar planos
│   └── visualizacao.py                 desenha os grafos (ficheiros DOT + página HTML)
│
├── exemplos/              ← planos de exemplo (.study) usados nas duas partes
├── tests/                 ← testes automáticos (python -m unittest discover -s tests)
│
├── docs/                  ← O RELATÓRIO, por secções
│   ├── parte1/   1_desenho_da_linguagem · 2_lexico_e_sintaxe · 3_semantica_gramatica_de_atributos · 4_qualidade
│   └── parte2/   5_grafos_e_analise_estatica · 6_transformacoes · 7_ferramenta
│
└── resultados/            ← FICHEIROS GERADOS (não se editam à mão)
    ├── grafos/            todos os grafos + index.html para os ver no browser
    └── relatorios/        uma página HTML por exemplo, com análise, transformações e grafos
```

## Onde está cada tarefa do enunciado

| Tarefa | Documento | Código |
|---|---|---|
| **Parte I.1** Desenho da linguagem | [docs/parte1/1_desenho_da_linguagem.md](docs/parte1/1_desenho_da_linguagem.md) | [exemplos/](exemplos) |
| **Parte I.2** Léxico e sintaxe | [docs/parte1/2_lexico_e_sintaxe.md](docs/parte1/2_lexico_e_sintaxe.md) | [parte1/gramatica.lark](parte1/gramatica.lark) |
| **Parte I.3** Semântica (gramática de atributos) | [docs/parte1/3_semantica_gramatica_de_atributos.md](docs/parte1/3_semantica_gramatica_de_atributos.md) | [parte1/verificador.py](parte1/verificador.py) |
| **Parte I.4** Qualidade | [docs/parte1/4_qualidade.md](docs/parte1/4_qualidade.md) | [parte1/metricas_gramatica.py](parte1/metricas_gramatica.py) |
| **Parte II.1** Representações intermédias (grafos) | [docs/parte2/5_grafos_e_analise_estatica.md](docs/parte2/5_grafos_e_analise_estatica.md) | [parte2/representacoes_intermedias.py](parte2/representacoes_intermedias.py) |
| **Parte II.2** Análise estática (validação) | [docs/parte2/5_grafos_e_analise_estatica.md](docs/parte2/5_grafos_e_analise_estatica.md) (5.4–5.7) | [parte2/analise_estatica.py](parte2/analise_estatica.py) |
| **Parte II.3** Transformações | [docs/parte2/6_transformacoes.md](docs/parte2/6_transformacoes.md) | [parte2/transformacoes.py](parte2/transformacoes.py) |
| **Parte II.4** Ferramenta integrada | [docs/parte2/7_ferramenta.md](docs/parte2/7_ferramenta.md) | [studylang.py](studylang.py) |

## Início rápido

```bash
pip install -r requirements.txt
python studylang.py exemplos                                  # Parte I: verificador sobre os exemplos
python studylang.py analisar exemplos/ex2_secundario.study    # Parte II: validação com os grafos
python studylang.py otimizar exemplos/ex7_analise.study       # Parte II: transformação
python studylang.py relatorio exemplos/ex7_analise.study      # página HTML com tudo
python -m unittest discover -s tests                          # testes
```

O guia completo para instalar, testar e rever o projeto está em [COMO_TESTAR.md](COMO_TESTAR.md).

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
| Semântica não sintática | 11 propriedades verificadas pela gramática de atributos (secção 3) |

## 2. Especificação lexical e sintática: decisões principais

- **Uma só gramática para os dois níveis.** `CREDITS` é opcional na sintaxe. A obrigação (universitário) ou a proibição (secundário) é verificada na semântica, que conhece o nível. Assim, não precisamos de duas gramáticas.
- **Sem *dangling else*.** Os corpos de `IF`/`ELSE` são sempre blocos com chavetas, e o `ELSE IF` é `ELSE` seguido de um `if_stmt`.
- **Precedência na gramática.** `* /` têm precedência sobre `+ -`, ambos associativos à esquerda. Nas condições, `NOT` > `AND` > `OR`.
- **Atributos só através de iterador.** `u.CREDITS` e `u.DIFFICULTY` só são válidos quando `u` é o iterador de um `FOR EACH`.
- **LALR(1) sem conflitos.** O Lark constrói a tabela sem conflitos, por isso a gramática não é ambígua.
- **Lexer `basic`.** Com o lexer contextual (o *default*), uma palavra reservada seria aceite como nome (`VAR STUDY = 1`). Com o `basic`, as palavras reservadas são de facto reservadas.
- **Comentários** de linha `//` e espaços em branco são ignorados.

## 3. Especificação semântica (gramática de atributos)

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

A gramática é **L-atribuída**: os herdados dependem só do pai e dos irmãos à esquerda. Por isso, todos os atributos são avaliados numa única passagem em profundidade, da esquerda para a direita. O `parte1/verificador.py` implementa essa passagem com funções recursivas, uma por grupo de produções. Não usámos o `LarkAG`. A correspondência entre regras e funções está na secção 3.6 da fase 3.

## 4. Como testar

Requer Python 3, Lark e NetworkX (`pip install -r requirements.txt`).

```bash
python studylang.py exemplos
```

Exemplos incluídos e resultado esperado:

| Exemplo | Resultado |
|---|---|
| Ex1: universitário | válido |
| Ex2: secundário (âmbitos e *shadowing*) | válido para a AG (a análise da Parte II mostra que excede as horas) |
| Ex3: secundário | 10 erros semânticos detetados (P1, P3, P4, P5, P6, P7, P9, P11) |
| Ex4: universitário | 3 erros detetados (falta `CREDITS`, segundo `RESOURCE` na linha 4, 0 horas) |
| Ex5: falta `LEVEL` | erro sintático |
| Ex6: `VAR STUDY = 1` | erro sintático (palavra reservada usada como nome) |

## 5. Qualidade da linguagem e da gramática

A avaliação completa está na [fase 4](docs/parte1/4_qualidade.md), e as métricas são calculadas com `python studylang.py metricas`. Em resumo:

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
- **Não ambiguidade:** LALR(1) sem conflitos e sem *dangling else*.
- **Precedência:** codificada nos níveis da gramática.
- **Sem símbolos inúteis.**
- **Tamanho:** 40 terminais, 28 não-terminais e 57 produções; 25 não-terminais escritos, expandidos internamente pelo Lark.
- **Produções unitárias:** 15, quase todas para agrupar instruções ou para a cadeia de precedência.
- **Recursividade:** à esquerda nos operadores binários, o que lhes dá associatividade à esquerda.

**Gramática de atributos**
- **Atributos:** 13 (4 herdados e 9 sintetizados) e 20 condições de contexto.
- **Avaliação:** L-atribuída, numa só passagem, com erros acumulados e reportados na linha que os causa.

## 6. Parte II: representações, análise, transformações e ferramenta

Toda a Parte II é usada através de `studylang.py` (ver a [fase 7](docs/parte2/7_ferramenta.md)):

```bash
python studylang.py verificar  FICHEIRO               # sintaxe + gramática de atributos (Parte I)
python studylang.py analisar   FICHEIRO [--md|--json]  # análise estática e diagnósticos
python studylang.py grafos     FICHEIRO [-o PASTA]     # AST, CFG, DFG, PDG
python studylang.py otimizar   FICHEIRO [-o SAIDA]     # transformação que preserva o plano
python studylang.py planificar FICHEIRO [--agregar]    # plano desenrolado
python studylang.py exportar   FICHEIRO [--formato md|csv|json]
python studylang.py relatorio  FICHEIRO [-o PASTA]     # página HTML com tudo
```

- **Representações intermédias ([fase 5](docs/parte2/5_grafos_e_analise_estatica.md)):** CFG por instrução e por blocos básicos, DFG (*reaching definitions*), PDG e *slicing*. `python studylang.py grafos-todos` gera em `resultados/grafos/` os 25 grafos dos exemplos, mais os da gramática e da AG (NB07). O ficheiro `resultados/grafos/index.html` mostra-os no browser.
- **Análise estática (fase 5):** as horas do plano são calculadas com a AG (`minHours`), com intervalos (interpretação abstrata) e com avaliação exata. Isto mostra que o Ex2 aloca 21 horas com 20 disponíveis. Os diagnósticos detetam também divisões por zero em tempo de execução, condições constantes, código inalcançável, definições mortas, instruções sem efeito e UCs sem estudo.
- **Transformações ([fase 6](docs/parte2/6_transformacoes.md)):**
  - otimização (propagação e dobragem de constantes, eliminação de ramos e de código morto);
  - planificação (avaliação parcial);
  - exportação para Markdown, CSV ou JSON.

  A correção é verificada pela igualdade do significado, isto é, da sequência de sessões.
- **Testes:** `python -m unittest discover -s tests` corre 16 testes. Incluem propriedades verificadas em 150 programas válidos gerados aleatoriamente: *pretty-printer* inverso do parser, transformações que preservam o significado e análises sólidas.

## 7. Limitações conhecidas e melhorias possíveis

Estas limitações foram identificadas na Parte I e são analisadas com mais
detalhe na secção 4.4 de [docs/parte1/4_qualidade.md](docs/parte1/4_qualidade.md). As que
estão resolvidas foram tratadas na Parte II.

- **`minHours` é apenas um limite inferior.** *Resolvido na Parte II:* a
  análise estática calcula as horas exatas e assinala o excesso (diagnóstico
  `HORAS`). A planificação torna a P11 da AG exata.
- **Divisão por zero parcial.** A AG só a deteta com divisores constantes. *Na
  Parte II:* a avaliação exata deteta também as que só acontecem em tempo de
  execução (`DIV_ZERO`).
- **Apenas números inteiros.** A linguagem não tem números decimais, durações
  tipadas, datas ou calendários.
- **Sem dimensão temporal.** Não existem dias, semanas, limites diários ou
  pré-requisitos entre UCs.
- **Expressividade sintática limitada.** `STUDY` por nome aceita apenas
  *strings* literais e as condições não aceitam parênteses de agrupamento.
- **Mensagens de erro sintático.** *Resolvido na Parte II:* a ferramenta
  indica a posição e os tokens esperados.
- **Limitações da análise estática:** ver a secção 5.7 da
  [fase 5](docs/parte2/5_grafos_e_analise_estatica.md). Os intervalos não são relacionais,
  e a avaliação exata pressupõe programas fechados.
