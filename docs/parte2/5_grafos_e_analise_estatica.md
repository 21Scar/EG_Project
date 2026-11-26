# 5. Grafos de Dependências e de Fluxo

Esta secção analisa as dependências da *StudyLang* a dois níveis:

* **na especificação** (NB07): dependências entre os símbolos da gramática e entre os atributos da gramática de atributos;
* **nos programas** (NB08): representações intermédias orientadas para a análise (AST anotada, CFG, DFG e PDG) e análises estáticas sobre elas.

Esta secção corresponde às tarefas 1 (representações intermédias) e 2 (análise estática) da Parte II. As representações estão implementadas em `parte2/representacoes_intermedias.py`, as análises em `parte2/analise_estatica.py` e a visualização em `parte2/visualizacao.py`. Os três módulos reutilizam o parser e o verificador de `parte1/verificador.py`. A integração destes componentes na ferramenta `studylang.py` está descrita na [secção 7](7_ferramenta.md).

Todos os grafos e números desta secção são gerados pelo script `parte2/visualizacao.py`:

```bash
pip install -r requirements.txt
python studylang.py grafos-todos
```

O script escreve, na pasta `resultados/grafos/`, um ficheiro `.dot` por grafo, o relatório completo `analise.md` e o visualizador `index.html`. O visualizador desenha todos os grafos no browser e permite descarregá-los em SVG, sem instalar nada. Se o Graphviz estiver instalado (`dot` no PATH), o script gera também os ficheiros `.svg` e `.png`. Como no NB08, os grafos são construídos com `networkx` a partir da árvore devolvida pelo `Lark`.

Programas analisados: os exemplos válidos Ex1 (universitário) e Ex2 (secundário) da secção 1.4 e um exemplo novo, **Ex7**, escrito para pôr em evidência as análises do NB08:

```study
STUDENT Marta LEVEL UNIVERSITY

UC "Algebra"  { CREDITS 6 DIFFICULTY 5 }
UC "Historia" { CREDITS 3 DIFFICULTY 1 }

RESOURCE TIME 25 HOURS
VAR base = 2
VAR bonus = 10                        // nunca lida: redefinida antes de qualquer uso

PLAN {
    VAR total = 0
    bonus = 1                         // dependência de saída com a linha 8
    FOR EACH u IN [ "Algebra", "Historia" ] {
        VAR h = base * u.DIFFICULTY
        IF ( base > 10 ) {            // sempre falsa: base é a constante 2
            STUDY u FOR 50 HOURS      // inalcançável
        } ELSE {
            STUDY u FOR h + bonus HOURS
        }
        total = total + h             // dependência transportada pelo ciclo
    }
    VAR resto = 25 - total            // nunca lida
}
```

O Ex7 é aceite pelo verificador sem erros: nenhuma das situações assinaladas nos comentários é detetada pela gramática de atributos. Só as análises desta secção as encontram.

---

## 5.1. Grafo de dependências da gramática

**Grafo:** `gramatica_dependencias`. Há uma aresta `A → B` quando `B` aparece no lado direito de uma produção de `A`. O grafo é construído sobre a gramática compilada pelo Lark, a mesma que `parte1/metricas_gramatica.py` usa: 28 não-terminais, incluindo 3 regras auxiliares geradas para os `*`.

| Propriedade | Valor |
|---|---|
| Não-terminais / arestas distintas | 28 / 45 |
| Grau médio de entrada = saída | 1,61 |
| Mais reutilizados (grau de entrada) | `expr` (6), `block` (4) |
| Recursividade direta | 9 não-terminais: `expr`, `term`, `factor`, `or_cond`, `and_cond`, `not_cond` e as 3 listas auxiliares |
| Recursividade indireta (ciclos) | {`expr`, `term`, `factor`} e {`stmt`, `block`, `if_stmt`, `else_part`, `foreach_stmt`, `__block_star`} |
| Símbolos inacessíveis / improdutivos | nenhum / nenhum |
| Profundidade (níveis de componentes fortemente ligadas) | 8 |

**Interpretação.**

* As duas componentes fortemente ligadas correspondem às duas formas de aninhamento da linguagem. A primeira é a das **expressões**: `factor → "(" expr ")"` fecha o ciclo `expr → term → factor → expr`. A segunda é a das **instruções**: um bloco contém instruções, e um `IF` ou um `FOR EACH` contém blocos. É este ciclo que permite as *construções compostas e aninhadas* pedidas pelo enunciado.
* As condições (`or_cond`, `and_cond`, `not_cond`) só têm recursividade direta e **não formam um ciclo com `cond`**: nenhuma regra volta a gerar uma condição completa entre parênteses. O grafo confirma, assim, a limitação da secção 4.4 (condições sem agrupamento). Permitir `"(" cond ")"` acrescentaria uma aresta `not_cond → cond` e um terceiro ciclo.
* Não há símbolos inúteis: todos são acessíveis a partir de `start` e todos geram pelo menos uma frase terminal. Os dois testes foram feitos sobre o grafo, por percurso e por ponto fixo.
* `expr` é o símbolo com mais dependentes: é usado por declarações, atribuições, `STUDY` e comparações. Alterar a sintaxe das expressões tem por isso o maior impacto na gramática.

## 5.2. Grafos de dependências da gramática de atributos

As regras semânticas da secção 3.4 foram escritas em `parte2/visualizacao.py` como uma função por produção. Cada função regista as arestas `X.a → Y.b`, que significam que `Y.b` é calculado a partir de `X.a`. Ao todo são 31 produções, contando as produções de cópia `decl → …` e `stmt → …`, e 113 regras de avaliação.

### 5.2.1. Grafos locais das produções

**Grafos:** `ag_local_start`, `ag_local_block`, `ag_local_foreach`, `ag_local_if`, `ag_local_var_decl`, `ag_local_study` e `ag_local_div`. Os herdados estão a verde, os sintetizados a laranja e os léxicos a cinzento.

* **`block → { stmt* }`:** é uma cadeia `block.env_in → stmt₁.env_in`, `stmt₁.env_out → stmt₂.env_in`, …, enquanto `errors` e `minHours` sobem de cada `stmt` para o `block`. É a forma gráfica do encadeamento da esquerda para a direita, que torna uma declaração visível nas instruções seguintes.
* **`foreach_stmt`:** o `block.env_in` depende de `foreach_stmt.env_in` e de `ID.name`. O iterador é acrescentado ao ambiente **só** do corpo, e é por isso que o grafo mostra que o iterador é local ao ciclo. `minHours` depende de `string_list.count` e de `block.minHours`, ou seja, do produto.
* **`start`:** contém as três cadeias herdadas que atravessam as declarações (`env`, `nres` e `limit`). O `start.errors` depende de `plan.minHours` e do `limit_out` da última declaração: é aqui que se juntam a informação descendente (o limite de horas) e a ascendente (as horas do plano), na verificação P11.
* **`expr → expr / expr`:** é a única produção em que `const` depende de `val` (`expr₂.val → expr.const`). Isto acontece porque uma divisão por zero deixa de ser constante.

### 5.2.2. Grafo global e métricas de dependência

**Grafo:** `ag_global`. É a união dos grafos locais com nós `símbolo.atributo`, a forma usada no NB07 para as métricas de dependência de atributos, que a secção 4.3 ainda não incluía:

| Métrica (NB07) | Valor |
|---|---|
| Nós (ocorrências símbolo.atributo) | 97 |
| Arestas (dependências distintas) | 142 |
| Grau médio de entrada = saída | 1,46 |
| Maior grau de entrada | `expr.errors` (7), `study_stmt.errors` (7), `start.errors` (6), `cond.errors` (6) |
| Maior grau de saída | `ID.name` (7), `stmt.env_in` (6), `expr.env`, `block.errors`, `block.minHours` (4) |

Os atributos com mais dependências são as listas `errors`: cada condição de contexto acrescenta-lhes uma aresta, o que mostra o custo do esquema de restrições "acumular todos os erros". Os atributos mais usados são o nome dos identificadores e o ambiente, o que confirma que o `env` é o atributo central da AG (secção 4.3). O grau médio baixo (1,46) indica que cada regra depende, em média, de pouco mais de um atributo, o que favorece a manutenção.

### 5.2.3. A AG é L-atribuída e não circular: verificação automática

A secção 3.5 afirmava que a AG é L-atribuída. O script **verifica-o aresta a aresta** em todas as produções, testando duas condições:

1. um herdado de `Xⱼ` só depende de herdados do pai ou de atributos dos irmãos `X₁ … Xⱼ₋₁`;
2. um sintetizado do pai só depende de atributos do próprio pai ou dos filhos.

Resultado: **nenhuma aresta viola as condições**.

Para os programas concretos, o script instancia as regras na árvore de cada exemplo e obtém o grafo de dependências da árvore. Sobre esse grafo verifica que é **acíclico**, porque existe uma ordenação topológica, que é uma ordem de avaliação. Verifica também que a **passagem única em profundidade** do verificador respeita todas as arestas. Nessa passagem, os herdados são calculados ao entrar num nó e os sintetizados ao sair.

| Programa | Ocorrências | Atributos | Dependências | Acíclico | Violações L-atribuída | Violações da passagem única |
|---|---|---|---|---|---|---|
| Ex1 | 98 | 264 | 314 | sim | 0 | 0 |
| Ex2 | 80 | 233 | 279 | sim | 0 | 0 |
| Ex7 | 90 | 263 | 310 | sim | 0 | 0 |

O grafo `ag_instancia_mini` mostra esta instanciação para um programa de seis linhas, já que nos exemplos completos o grafo é demasiado grande para se ler. Nele vê-se o ambiente a descer pela árvore e `errors`/`minHours` a subir.

## 5.3. Representações intermédias dos programas

### 5.3.1. AST anotada

**Grafos:** `ex1_ast`, `ex2_ast` e `ex7_ast`. São a árvore do Lark com os atributos que o verificador calcula: `type` e `val` nas expressões e `minHours` nas instruções. Os valores foram capturados durante a execução de `verificador.check()`, por isso a figura mostra exatamente o que a implementação calcula. Por exemplo, no Ex1 `minHours` vale 0 no corpo do ciclo, porque `h` depende de `u.CREDITS` e não é constante, e vale 3 no plano.

### 5.3.2. Grafo de fluxo de controlo (CFG)

**Grafos:** `exN_cfg` (um nó por instrução) e `exN_cfg_blocos` (blocos básicos, construídos pela junção de instruções consecutivas, como no NB08). Os `IF` são losangos, os cabeçalhos de `FOR EACH` são hexágonos e a aresta de retorno do ciclo está a vermelho.

| Métrica | Ex1 | Ex2 | Ex7 |
|---|---|---|---|
| Instruções / blocos básicos | 13 / 9 | 13 / 7 | 14 / 8 |
| Arestas entre blocos | 13 | 10 | 11 |
| Arestas de retorno (ciclos) | 3 (para B2) | 2 (para B2) | 1 (para B2) |
| Complexidade ciclomática V(G) = E − N + 2 | 4 | 3 | 3 |
| Caminhos ENTRY→EXIT (cada ciclo 0 ou 1 vezes) | 4 | 3 | 3 |
| Profundidade de aninhamento | 3 | 2 | 2 |
| Máximo de execuções de instruções | 24 | 22 | 18 |

Em todos os casos, `V(G)` é igual ao número de decisões + 1, como esperado num programa estruturado. O número de arestas de retorno é o número de ramos que terminam o corpo do ciclo, mas o *loop header* é sempre um só.

**Propriedades da linguagem que os CFGs tornam visíveis:**

* **CFGs sempre estruturados e redutíveis.** Não há `goto`, `break` nem `return`, por isso cada construção tem uma única entrada e uma única saída. Consequência: **não há código estruturalmente inalcançável** (0 nos três exemplos). Uma instrução só pode ser inalcançável por razões semânticas, quando uma condição é sempre falsa (ver 5.4).
* **Terminação garantida e decidível.** O único ciclo é o `FOR EACH`, sobre uma lista literal finita que o corpo não pode alterar. Todos os programas terminam, e o número máximo de execuções de cada instrução é o produto dos tamanhos das listas dos ciclos que a envolvem (última linha da tabela). Ao contrário do que o NB08 refere para linguagens gerais, a terminação nunca precisa de ser aproximada.
* **Um dos caminhos do CFG é impossível.** O CFG tem o caminho que salta o ciclo (a aresta `fim` sem passar pelo corpo), mas a gramática exige pelo menos uma UC na lista (`string_list: STRING ("," STRING)*`). Este caminho nunca é executado: é um exemplo de como o CFG sobre-aproxima a execução.

### 5.3.3. Definições, usos e grafo de fluxo de dados (DFG)

**Grafos:** `exN_dfg`. Uma aresta `d → u` significa que a definição em `d` chega ao uso em `u`. As arestas são calculadas por **reaching definitions** sobre o CFG, iterando até ao ponto fixo (3 iterações nos três exemplos). As definições são `VAR`, as atribuições e o cabeçalho do `FOR EACH`, que define o iterador em cada volta.

As tabelas completas de definições e usos estão em `resultados/grafos/analise.md`. Os resultados mais relevantes são estes:

| | Ex1 | Ex2 | Ex7 |
|---|---|---|---|
| Dependências verdadeiras (fluxo) | 10 | 9 | 12 |
| Antidependências | 8 | 7 | 5 |
| Dependências de saída | 2 | 4 | 5 |
| Definições nunca lidas | 0 | 1 | 2 |
| Dependências falsas se os âmbitos forem ignorados | 0 | **1** | 0 |

* **Os âmbitos são indispensáveis à análise de fluxo de dados.** No Ex2 há duas variáveis `extra`: a do `PLAN` (linha 11) e a do bloco do `IF` (linha 15), que a sombreia. Se as variáveis fossem identificadas só pelo nome, a análise criaria a dependência falsa `VAR extra = 2` (l.15) → `extra = extra + 1` (l.21), mas a variável interior já não existe na linha 21. O script resolve primeiro cada nome para a sua declaração, segundo o âmbito estático por bloco da secção 3.2, e só depois constrói o DFG. É a mesma informação que o atributo `env` transporta na AG, e mostra que a análise semântica (Parte I) é a base da análise de fluxo (Parte II).
* **Dependências transportadas pelo ciclo.** Em `total = total + h` (Ex7), o uso de `total` recebe duas definições: `VAR total = 0`, na primeira volta, e a própria instrução, nas seguintes. As dependências de saída "entre iterações" (`h`, `u` e `total`) são reescritas da mesma variável em voltas sucessivas.
* **Antidependências.** Por exemplo, `STUDY u FOR h HOURS` lê `h` antes de `VAR h = …` o reescrever na volta seguinte. São estas dependências que impedem, por exemplo, que se reordenem instruções do corpo do ciclo.
* **Nunca há usos sem definição.** `VAR` exige sempre um valor inicial e a P5 obriga a que cada nome esteja declarado e visível, por isso todos os usos têm pelo menos uma definição que lhes chega. É uma garantia que o desenho da linguagem dá ao fluxo de dados.

### 5.3.4. Grafo de dependências do programa (PDG) e *slicing*

**Grafos:** `exN_pdg`. Juntam as dependências de **controlo** (a tracejado, com o ramo `V`, `F` ou `próximo`) às de **dados** (a azul). Como a linguagem é estruturada, uma instrução depende do controlo do `IF` ou `FOR EACH` mais próximo que a contém.

O critério de *slicing* natural no domínio são as instruções `STUDY`, porque são o comportamento observável do plano. Para cada `STUDY` calcula-se a **fatia para trás**, isto é, todos os nós de que depende por dados ou por controlo. No Ex1:

| Critério | Linhas na fatia |
|---|---|
| l.14 `STUDY u FOR h HOURS` | 8, 11, 12, 13, 14 |
| l.16 `STUDY u FOR 2 HOURS` | 8, 11, 12, 13, 15, 16 |
| l.18 `STUDY u FOR max_session HOURS` | 8, 11, 12, 13, 15, 18 |
| l.21 `STUDY "Redes" FOR 3 HOURS` | 21 |

A linha 8 (`VAR max_session = 4`) está na fatia de `STUDY u FOR 2 HOURS` embora este não use `max_session`. Isto acontece porque o `STUDY` só executa se a condição da linha 13, que usa `max_session`, for falsa. É uma dependência que só a componente de controlo do PDG revela, tal como no exemplo de *slicing* do NB08.

**Código morto do ponto de vista do plano.** As instruções que não pertencem a nenhuma fatia não influenciam nenhuma hora de estudo. No PDG aparecem a cinzento:

* **Ex2:** `VAR extra = 1` (l.11) e `extra = extra + 1` (l.21). A segunda nunca é lida e a primeira só é lida pela segunda: é o mesmo caso de código morto em cadeia do NB08.
* **Ex7:** `VAR bonus = 10` (redefinida antes de ser lida), `VAR total = 0`, `total = total + h` e `VAR resto = 25 - total`. `total` é calculado em todas as voltas, mas o seu valor nunca chega a um `STUDY`.

## 5.4. Análise estática das horas (P11)

A propriedade mais importante do domínio é a P11: as horas do plano não podem exceder o `RESOURCE TIME`. A AG verifica-a com `minHours`, que só conta valores constantes. O script compara essa verificação com três análises sobre as mesmas representações, que vão da mais grosseira à mais precisa:

1. **Intervalos sem condições:** interpretação abstrata com o domínio de intervalos do NB08 (`[l, u]`, com junção `⊔` nos pontos de encontro). O iterador vale todas as UCs da lista, e `u.DIFFICULTY` é o intervalo entre a menor e a maior dificuldade da lista. Os dois ramos de cada `IF` são sempre considerados possíveis.
2. **Intervalos com condições:** como a anterior, mas as condições também são avaliadas sobre intervalos (sempre verdadeira, sempre falsa ou depende). Os ramos impossíveis são descartados.
3. **Avaliação exata:** o corpo de cada `FOR EACH` é avaliado uma vez por UC da lista, com o iterador ligado aos atributos concretos.

| Programa | RESOURCE | AG (`minHours`) | Intervalos sem condições | Intervalos com condições | Exata | Veredicto exato |
|---|---|---|---|---|---|---|
| Ex1 | 30 | ≥ 3 | [9, 39] | [9, 39] | **29** | cumpre |
| Ex2 | 20 | ≥ 0 | [12, 27] | [12, 27] | **21** | **excede** |
| Ex7 | 25 | ≥ 0 | [6, 100] | [6, 22] | **14** | cumpre |

**Interpretação, nos termos do NB08:**

* **`minHours` é uma sub-aproximação.** Nunca dá falsos positivos, mas deixa passar erros. O Ex2, apresentado na secção 1.4 como válido, **aloca 21 horas com apenas 20 disponíveis**: Matemática A 9 h, Física 8 h e Português 4 h. A AG não o deteta porque todas as horas dependem de `u.DIFFICULTY`.
* **Os intervalos são uma sobre-aproximação.** Nunca deixam passar um excesso, mas dão falsos alarmes. No Ex1, o intervalo [9, 39] ultrapassa 30, mas o plano real tem 29 horas. A imprecisão vem de a análise não relacionar `u.CREDITS` com `u.DIFFICULTY` da mesma UC: combina os créditos de uma UC com a dificuldade de outra.
* **Avaliar as condições torna a análise mais precisa.** No Ex7, a condição `base > 10` é sempre falsa, porque `base` vale [2, 2]. Ao descartar o ramo `STUDY u FOR 50 HOURS`, o intervalo passa de [6, 100] (falso alarme) para [6, 22], o que **prova** que o plano cumpre o limite. O ramo é marcado como inalcançável nos grafos `ex7_cfg` e `ex7_cfg_blocos`: é a simplificação de controlo por propagação de constantes do NB08.
* **Aqui a análise exata é possível.** Nas linguagens gerais é indecidível, mas na *StudyLang* não há entrada de dados (todos os valores são constantes do programa) e os ciclos são limitados por listas literais. Os programas são, portanto, fechados e terminam sempre, e a avaliação exata é ela própria uma análise estática. Pela mesma razão, o domínio de intervalos dispensa *widening*: cada ciclo é percorrido um número conhecido de vezes.

**Cobertura de ramos.** A avaliação exata indica também que ramos são executados com os dados do programa. No Ex1, o ramo `ELSE` da linha 18 (`STUDY u FOR max_session HOURS`) **nunca é executado**: as três UCs caem nos dois primeiros ramos. O código não é inalcançável em geral, já que outra UC poderia lá cair, mas é inútil para este plano.

## 5.5. Síntese e ligação à Parte II

* A gramática tem dois ciclos de recursividade, as expressões e as instruções, que suportam o aninhamento. A ausência de um terceiro ciclo nas condições explica a limitação dos parênteses.
* A AG tem 142 dependências entre 97 atributos. A propriedade L-atribuída e a não-circularidade, antes apenas afirmadas, são agora **verificadas automaticamente**, por produção e nas árvores dos exemplos.
* Os CFGs da *StudyLang* são estruturados, e os programas terminam sempre com um número de passos conhecido. Isto torna as análises de fluxo simples e, no caso das horas, permite que sejam exatas.
* A análise de fluxo depende da resolução de âmbitos feita na AG: sem ela, o DFG do Ex2 teria uma dependência falsa.
* As análises encontraram problemas que a AG não deteta: um excesso de horas no Ex2, código morto no Ex2 e no Ex7, um ramo inalcançável no Ex7 e um ramo nunca executado no Ex1.

**O que estas análises dão à ferramenta.** As análises resolvem limitações da secção 4.4 e foram integradas na ferramenta:

1. A P11 passa a ser verificada com a avaliação exata das horas. Isto elimina a limitação "variáveis não contam para as horas", e também as horas que dependem de `u.CREDITS` e `u.DIFFICULTY`. Ver o diagnóstico `HORAS` em `analise_estatica.diagnostics`.
2. A ferramenta gera avisos a partir do PDG (definições nunca lidas, instruções fora de todas as fatias) e do CFG com intervalos (condições constantes, instruções inalcançáveis).
3. O PDG e os intervalos são usados pelas transformações da [secção 6](6_transformacoes.md) para eliminar código morto e simplificar condições constantes.

## 5.6. Diagnósticos da análise estática

`analise_estatica.diagnostics(P)` junta os resultados numa lista de erros e avisos, cada um com a linha do ficheiro. É isto que o comando `studylang.py analisar` mostra ao utilizador:

| Código | Nível | Origem | Significado |
|---|---|---|---|
| `AG` | erro | gramática de atributos (Parte I) | as 11 propriedades P1–P11 |
| `HORAS` | erro | avaliação exata | o plano excede o `RESOURCE TIME`, embora a AG não o detete (Ex2) |
| `HORAS` | info | intervalos vs. exata | os intervalos dão um alarme, mas o valor exato cumpre o limite (Ex1) |
| `DIV_ZERO` | erro | avaliação exata | divisão por zero que só acontece em tempo de execução, por exemplo `10 / (u.DIFFICULTY - 2)` |
| `HORAS_POS` | erro | avaliação exata | um `STUDY` com horas ≤ 0 calculadas a partir de variáveis (a P10 só verifica constantes) |
| `COND_CONST` | aviso | intervalos | condição sempre verdadeira ou sempre falsa |
| `INALCANCAVEL` | aviso | CFG + intervalos | instrução que nenhuma execução alcança |
| `DEF_MORTA` | aviso | DFG | valor atribuído que nunca é lido |
| `SEM_EFEITO` | aviso | PDG (slicing) | instrução que não influencia nenhuma hora de estudo |
| `RAMO_NAO_EXEC` | info | avaliação exata | ramo que nenhuma UC do plano executa |
| `UC_SEM_ESTUDO` | aviso | avaliação exata | UC declarada sem horas no plano |

A análise de fluxo só é feita sobre programas sem erros semânticos. Num programa inválido, por exemplo com uma variável não declarada, o DFG e a avaliação não estão bem definidos, por isso a ferramenta mostra só os erros da AG.

## 5.7. Pressupostos e limitações da análise estática

* **Programas fechados.** A avaliação exata pressupõe que todos os dados estão no programa: as UCs, os seus atributos e as listas dos ciclos. É o caso da *StudyLang* atual. Se a linguagem passasse a ler dados externos, por exemplo um ficheiro de UCs, a avaliação exata deixaria de ser possível e a ferramenta teria de usar só os intervalos, que continuam sólidos.
* **Intervalos não relacionais.** O domínio de intervalos guarda cada valor isoladamente, por isso perde relações como "os créditos e a dificuldade são da mesma UC". Daí o falso alarme do Ex1, com o intervalo [9, 39] para 29 horas reais. Um domínio relacional, como octógonos, ou a avaliação do ciclo por UC resolveriam esta perda de precisão. A ferramenta usa a segunda opção.
* **Ramos não executados dependem dos dados.** Um `RAMO_NAO_EXEC` não significa código morto: deixa de ser verdade se se acrescentar uma UC à lista. Por isso é só informativo e a otimização não o remove. Só remove ramos que os intervalos provam impossíveis para qualquer UC da lista.
* **"Sem efeito" é relativo ao plano.** O comportamento observável considerado são as sessões `STUDY`. Uma variável calculada só para ser lida pelo utilizador, como `total` no Ex7, é marcada como sem efeito porque não muda nenhuma hora. Esta escolha é deliberada para o domínio.
* **Precisão do CFG.** O CFG inclui o caminho que salta o ciclo (lista vazia), que a gramática torna impossível. Algumas métricas, como o número de caminhos, contam-no.
* **Divisão inteira.** Como no verificador da Parte I, `/` é a divisão inteira (`//` do Python). Os intervalos seguem a mesma semântica, mas um divisor cujo intervalo contenha 0 torna o resultado desconhecido (⊤).

A solidez das análises é testada automaticamente (secção 6.6) com 150 programas aleatórios nos testes, e foi verificada também noutros 1000 programas gerados com outras sementes. Em todos, as horas exatas ficam dentro dos intervalos e o `minHours` da AG nunca as ultrapassa.
