# EG_Project — StudyLang

Projeto de Engenharia Gramatical 2026/2027.

- **Parte I (Engenharia de Linguagens e Gramáticas):** desenho da linguagem, gramática e gramática de atributos (fases 1–4).
- **Parte II (Representação, Análise e Integração):** representações intermédias, análise estática, transformações e a ferramenta `studylang.py` (fases 5–7).

## Início rápido

```bash
pip install -r requirements.txt
python studylang.py analisar exemplos/ex2_secundario.study
python studylang.py otimizar exemplos/ex7_analise.study
python studylang.py relatorio exemplos/ex7_analise.study      # página HTML com tudo
python -m unittest discover -s tests                          # testes
```

O guia passo a passo para instalar, testar e rever o projeto está em [COMO_TESTAR.md](COMO_TESTAR.md).

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
| [metricas.py](metricas.py) | Cálculo das métricas da gramática compilada pelo Lark, usadas na fase 4 |
| [exemplos/](exemplos) | Programas de exemplo (`.study`), partilhados pelas duas partes |
| **Parte II** | |
| [fase_5_grafos_e_dependencias.md](fase_5_grafos_e_dependencias.md) | Tarefas 1 e 2: grafos de dependências (gramática e AG), CFG, DFG, PDG, análise estática e diagnósticos |
| [fase_6_transformacoes.md](fase_6_transformacoes.md) | Tarefa 3: otimização, planificação, exportação e evidência de correção |
| [fase_7_ferramenta.md](fase_7_ferramenta.md) | Tarefa 4: arquitetura, instalação, uso e demonstração da ferramenta |
| [ir.py](ir.py) | Representações intermédias: resolução de nomes, CFG, blocos básicos, DFG, PDG, fatias |
| [analise.py](analise.py) | Análise estática: intervalos, avaliação exata, diagnósticos |
| [transformacoes.py](transformacoes.py) | Pretty-printer, otimização, planificação e exportação |
| [grafos.py](grafos.py) | Visualização: gera todos os grafos em `grafos/` e o relatório `grafos/analise.md` |
| [studylang.py](studylang.py) | Ferramenta de linha de comandos que integra tudo |
| [tests/](tests) | Testes unitários e de propriedades (programas aleatórios) |
| [relatorios/](relatorios) | Relatórios HTML já gerados para os exemplos válidos |

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

Requer Python 3, Lark e NetworkX (`pip install -r requirements.txt`).

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

A avaliação completa está na [fase 4](fase_4_qualidade.md), e as métricas são calculadas com `python metricas.py`. Em resumo:

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

## 7. Parte II: representações, análise, transformações e ferramenta

Toda a Parte II é usada através de `studylang.py` (ver a [fase 7](fase_7_ferramenta.md)):

```bash
python studylang.py verificar  FICHEIRO               # sintaxe + gramática de atributos (Parte I)
python studylang.py analisar   FICHEIRO [--md|--json]  # análise estática e diagnósticos
python studylang.py grafos     FICHEIRO [-o PASTA]     # AST, CFG, DFG, PDG
python studylang.py otimizar   FICHEIRO [-o SAIDA]     # transformação que preserva o plano
python studylang.py planificar FICHEIRO [--agregar]    # plano desenrolado
python studylang.py exportar   FICHEIRO [--formato md|csv|json]
python studylang.py relatorio  FICHEIRO [-o PASTA]     # página HTML com tudo
```

- **Representações intermédias ([fase 5](fase_5_grafos_e_dependencias.md)):** CFG por instrução e por blocos básicos, DFG (*reaching definitions*), PDG e *slicing*. `python grafos.py` gera em `grafos/` os 25 grafos dos exemplos, mais os da gramática e da AG (NB07). O ficheiro `grafos/index.html` mostra-os no browser.
- **Análise estática (fase 5):** as horas do plano são calculadas com a AG (`minHours`), com intervalos (interpretação abstrata) e com avaliação exata. Isto mostra que o Ex2 aloca 21 horas com 20 disponíveis. Os diagnósticos detetam também divisões por zero em tempo de execução, condições constantes, código inalcançável, definições mortas, instruções sem efeito e UCs sem estudo.
- **Transformações ([fase 6](fase_6_transformacoes.md)):**
  - otimização (propagação e dobragem de constantes, eliminação de ramos e de código morto);
  - planificação (avaliação parcial);
  - exportação para Markdown, CSV ou JSON.

  A correção é verificada pela igualdade do significado, isto é, da sequência de sessões.
- **Testes:** `python -m unittest discover -s tests` corre 16 testes. Incluem propriedades verificadas em 150 programas válidos gerados aleatoriamente: *pretty-printer* inverso do parser, transformações que preservam o significado e análises sólidas.

## 8. Limitações conhecidas e melhorias possíveis

Estas limitações foram identificadas na Parte I e são analisadas com mais
detalhe na secção 4.4 de [fase_4_qualidade.md](fase_4_qualidade.md). As que
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
  [fase 5](fase_5_grafos_e_dependencias.md). Os intervalos não são relacionais,
  e a avaliação exata pressupõe programas fechados.
