# 7. Ferramenta e Integração

Esta secção corresponde à tarefa 4 da Parte II. Os componentes das Partes I e II estão integrados numa só ferramenta de linha de comandos, `studylang.py`. A ferramenta processa ficheiros `.study`, corre as análises, aplica as transformações e mostra os resultados em texto, Markdown, JSON, grafos ou numa página HTML.

## 7.1. Arquitetura

```text
 ficheiro .study
       │
       ▼
┌──────────────────────────────────────┐   Parte I
│ parte1/gramatica.lark                │   gramática LALR(1), lexer basic
│ parte1/verificador.py                │   parser + gramática de atributos (P1–P11)
└──────────────────┬───────────────────┘
                   │ árvore validada
                   ▼
┌──────────────────────────────────────┐   Parte II
│ parte2/representacoes_intermedias.py │   resolução de nomes, CFG, blocos básicos,
│                                      │   reaching definitions, DFG, PDG, fatias
├──────────────────────────────────────┤
│ parte2/analise_estatica.py           │   intervalos, avaliação exata, diagnósticos
├──────────────────────────────────────┤
│ parte2/transformacoes.py             │   pretty-printer, otimização, planificação,
│                                      │   exportação, significado (meaning)
├──────────────────────────────────────┤
│ parte2/visualizacao.py               │   DOT, visualizador HTML (viz.js),
│                                      │   grafos da gramática e da AG (NB07)
└──────────────────┬───────────────────┘
                   ▼
┌──────────────────────────────────────┐
│ studylang.py (CLI)                   │   verificar · analisar · grafos · otimizar ·
│                                      │   planificar · exportar · relatorio ·
│                                      │   exemplos · metricas · grafos-todos
└──────────────────────────────────────┘
```

**Cada componente só depende dos que estão acima dele.** O verificador da Parte I não foi alterado na sua lógica: as camadas da Parte II usam a árvore e os erros que ele produz. A integração apoia-se em três decisões:

* **Uma classe `representacoes_intermedias.Program`** guarda tudo o que se sabe sobre um programa: a árvore, os erros da AG, as UCs, o limite de horas, a resolução de nomes e o CFG. As análises e as transformações recebem um `Program` em vez de texto, o que evita voltar a fazer o parse e permite analisar árvores já transformadas.
* **A resolução de nomes segue o atributo `env` da AG.** Usa o mesmo âmbito estático por bloco, mas de forma explícita (cada uso aponta para a sua declaração), e é a base do DFG e das transformações.
* **As transformações reutilizam as análises.** A otimização usa os intervalos (`analise_estatica.Interp`) e as fatias do PDG (`representacoes_intermedias.slices`). A planificação e a exportação usam a avaliação exata. A correção é verificada com a mesma função `meaning`.

## 7.2. Instalação e uso

```bash
pip install -r requirements.txt          # lark, networkx
python studylang.py --help
```

| Comando | O que faz |
|---|---|
| `verificar FICH` | parse e gramática de atributos (Parte I); código de saída 1 se houver erros |
| `analisar FICH [--md \| --json]` | métricas do CFG, dependências, horas (AG / intervalos / exata) e diagnósticos |
| `grafos FICH [-o PASTA]` | AST anotada, CFG, CFG de blocos, DFG e PDG em DOT, mais `index.html` |
| `otimizar FICH [-o SAIDA]` | programa otimizado; o registo e a verificação de equivalência vão para stderr |
| `planificar FICH [--agregar] [-o SAIDA]` | plano desenrolado; volta a verificar o resultado com a AG |
| `exportar FICH [--formato md\|csv\|json]` | tabela do plano efetivo |
| `relatorio FICH [-o PASTA]` | página HTML com o programa, os diagnósticos, as horas, as transformações e os grafos |

Outros scripts:

```bash
python studylang.py exemplos                     # exemplos da Parte I
python studylang.py metricas                            # métricas da gramática (NB07)
python studylang.py grafos-todos                              # todos os grafos (gramática, AG, exemplos) em resultados/grafos/
python -m unittest discover -s tests -v       # testes (secção 6.6)
```

Os exemplos estão em `exemplos/*.study` e são partilhados pelo verificador da Parte I e pela ferramenta. Os relatórios HTML dos três exemplos válidos já estão gerados em `resultados/relatorios/`.

## 7.3. Demonstração

**1. Um plano "válido" para a Parte I, mas que excede as horas (Ex2).**

```text
$ python studylang.py verificar exemplos/ex2_secundario.study
exemplos/ex2_secundario.study: OK, sintaxe e semântica válidas

$ python studylang.py analisar exemplos/ex2_secundario.study
exemplos/ex2_secundario.study: Joao (SECONDARY), 3 UC(s), RESOURCE TIME = 20
  CFG: 7 blocos básicos, V(G) = 3, 3 caminhos, aninhamento 2, termina em ≤ 22 execuções
  Dependências: 9 de fluxo, 7 anti, 4 de saída
  Horas: AG ≥ 0 | intervalos [12, 27] | exatas 21  ->  excede de certeza (21 > 20)
  Por UC: Matematica A 9 h, Fisica 8 h, Portugues 4 h
  Diagnósticos (3):
  ✖ erro  l.10  [HORAS] o plano aloca 21 h e só há 20 h em RESOURCE TIME (a AG só garante ≥ 0 h e não deteta o excesso)
  ⚠ aviso l.11  [SEM_EFEITO] não influencia nenhuma hora de estudo: `VAR extra = 1`
  ⚠ aviso l.21  [DEF_MORTA] o valor de `extra@11` definido aqui nunca é lido: `extra = extra + 1`
```

**2. Otimizar e planificar (Ex7).** `otimizar` reduz o plano de 11 para 3 instruções e confirma que é o mesmo plano. `planificar --agregar` dá `STUDY "Algebra" FOR 11 HOURS` e `STUDY "Historia" FOR 3 HOURS`.

**3. Erros sintáticos mais claros.** A Parte I indicava só "token inesperado" (limitação da secção 4.4). A ferramenta mostra agora o que era esperado e onde:

```text
$ python studylang.py verificar exemplos/ex5_erro_sintatico.study
exemplos/ex5_erro_sintatico.study: erro sintático na linha 2, coluna 1: encontrado 'UC'; esperado: LEVEL
    UC "Redes" { CREDITS 3 DIFFICULTY 3 }
    ^
```

**4. Relatório HTML.** `python studylang.py relatorio exemplos/ex7_analise.study` gera uma página com todos os resultados e os grafos desenhados no browser, sem precisar de instalar o Graphviz. É a forma mais prática de fazer a demonstração na apresentação.

## 7.4. Alterações à Parte I

O enunciado pede que se expliquem as alterações à Parte I:

* **Reorganização do repositório.** O código passou a estar em duas pastas, `parte1/` e `parte2/`, a documentação em `docs/parte1/` e `docs/parte2/`, e os ficheiros gerados em `resultados/`. Alguns ficheiros mudaram de nome para dizerem melhor o que contêm: `check_studylang.py` → `parte1/verificador.py`, `studylang.lark` → `parte1/gramatica.lark`, `metricas.py` → `parte1/metricas_gramatica.py`. A lógica do verificador não mudou.
* **Exemplos em ficheiros.** Os exemplos passaram das *strings* do verificador para `exemplos/*.study`, e o verificador lê-os daí. O resultado de `python studylang.py exemplos` é o mesmo que o antigo `python check_studylang.py`.
* **Mensagens de erro sintático.** Indicam agora os tokens esperados e a posição (melhoria proposta na secção 4.4).
* **Gramática e AG sem alterações.** As novas verificações (P11 exata, divisão por zero em tempo de execução, horas ≤ 0 calculadas) foram acrescentadas como **análise estática**, em `analise_estatica.diagnostics`, e não como regras da AG. Assim, a AG continua L-atribuída e de uma passagem, e as verificações mais caras ficam numa camada própria.
* **Ex2.** A análise mostrou que o Ex2, apresentado na Parte I como válido, aloca 21 horas com 20 disponíveis. O exemplo foi mantido sem alterações porque mostra bem a diferença entre a verificação da AG e a análise estática.
