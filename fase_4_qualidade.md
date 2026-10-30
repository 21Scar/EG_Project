# 4. Qualidade da Linguagem e da Gramática

## 4.1. Qualidade da Linguagem

A linguagem foi avaliada segundo os fatores internos de qualidade do NB7.

**Expressividade.** As construções correspondem a conceitos do domínio (`UC`, `STUDY … FOR … HOURS`, `RESOURCE TIME`, `LEVEL`), o que permite ao estudante escrever o plano de forma próxima da forma como pensa nele. Por outro lado, só existem números inteiros e não há noção de dias.

**Documentação.** Só existem comentários de linha (`//`), sem comentários de bloco nem anotações estruturadas. É um ponto fraco.

**Unicidade.** Há uma só forma de repetir (`FOR EACH`) e uma só forma de decidir (`IF / ELSE IF / ELSE`), o que facilita a aprendizagem e a leitura. A exceção é o `STUDY`, que aceita a UC pelo nome ou pelo iterador.

**Consistência.** As palavras-chave estão todas em maiúsculas e os blocos usam sempre chavetas. A principal inconsistência é que as UCs são referidas por strings e as variáveis por identificadores.

**Extensibilidade.** O utilizador não pode criar tipos ou construções novas: qualquer extensão obriga a alterar a gramática.

**Escalabilidade.** Em planos com muitas UCs, é preciso repetir os nomes das UCs em cada `FOR EACH`, porque não há forma de iterar sobre todas as UCs declaradas.

**Fiabilidade.** O verificador deteta 11 tipos de erro semântico (P1 a P11), como UCs não declaradas, variáveis usadas fora do seu âmbito ou horas que excedem o `RESOURCE TIME`. No entanto, alguns erros escapam (ver 4.4).

**Modularidade.** Não existem funções, módulos nem imports. Para o domínio, isto é aceitável, porque um plano de estudo é normalmente pequeno (um semestre com poucas UCs).

## 4.2. Qualidade da Gramática

As métricas foram calculadas com o script `metricas.py`, baseado no código do NB7.

| Métrica | Valor |
|---|---|
| Terminais | 40 |
| Não-terminais | 28 (25 escritos + 3 auxiliares gerados pelo Lark) |
| Produções | 57 |
| Produções unitárias | 15 |
| Não-terminais recursivos diretos | 9 |
| Comprimento médio / máximo das produções | 2,47 / 8 |
| Produções por não-terminal (média / máximo) | 2,04 / 5 |
| Grau médio de entrada / saída | 1,6 / 1,6 |
| Parser LALR (estados / entradas da tabela) | 117 / 650 |

**Produções unitárias.** Das 15, 8 servem para agrupar os tipos de declaração e de instrução, 5 para definir a cadeia de precedência dos operadores (`cond → or_cond → and_cond → not_cond` e `expr → term → factor`) e 2 são auxiliares geradas pelo Lark. Como representam conceitos com significado, ajudam a compreensão da gramática. Além disso, o `?` do Lark evita que apareçam como nós na árvore sintática, que fica mais simples de processar.

**Recursividade.** Dos 9 não-terminais recursivos, 4 são operadores binários com recursividade à esquerda, o que lhes dá associatividade à esquerda. Os operadores prefixos (`NOT`, `-`) usam recursividade à direita. Os restantes 3 são as regras auxiliares que o Lark gera para as listas (`*`).

**Tamanho e dependências.** As produções são curtas e cada não-terminal depende em média de menos de 2 outros, o que facilita a manutenção da gramática: alterar uma regra afeta poucas outras.

**Notação.** A gramática usa EBNF (`*` e `?`) para listas e partes opcionais e recursividade ao estilo BNF para os operadores. A mistura não é inconsistente, porque segue um critério: EBNF onde só interessa a sequência dos elementos, e recursividade onde interessa a estrutura das operações na árvore (cada operação gera um nó próprio, como `add` ou `mul`, com a associatividade correta).

**Métricas lexicográficas.** Os nomes dos não-terminais derivam dos conceitos que representam (por exemplo `study_stmt` e `foreach_stmt`). Das 21 palavras-chave, 12 são do domínio do estudo e 9 de programação, o que torna os programas próximos da linguagem natural (por exemplo `STUDY "X" FOR 8 HOURS`). Há 6 terminais flexíveis e 34 fixos. A linguagem só suporta comentários de linha, o que limita a documentação dos planos.

## 4.3. Qualidade da Gramática de Atributos

| Métrica | Valor |
|---|---|
| Atributos (herdados / sintetizados) | 11 (2 / 9) |
| Condições de contexto | 20 |
| Atributos atómicos / estruturados | 7 / 4 |

**Complexidade dos atributos.** A maioria dos atributos é atómica (números ou booleanos). Os estruturados são o ambiente (`env`), que é uma pilha de âmbitos, e a lista de mensagens de erro (`errors`). O ambiente é o atributo mais complexo, mas concentra num só sítio toda a informação sobre os nomes declarados (UCs, variáveis e iteradores) e os âmbitos onde são visíveis.

**Esquema de avaliação.** A gramática é L-atribuída: os atributos herdados dependem só do pai e dos irmãos à esquerda, por isso todos os atributos podem ser calculados numa só passagem pela árvore, da esquerda para a direita.

**Esquema de restrições.** As 20 condições de contexto não interrompem a análise: cada erro é acrescentado à lista `errors`. Isto permite ao utilizador ver todos os erros de uma só vez.

**Clareza dos nomes.** A maioria dos nomes vem dos conceitos que representam (`errors`, `minHours`, `limit`). Alguns são abreviaturas, como `env` (ambiente) e `nres` (número de declarações `RESOURCE`).

## 4.4. Limitações e Melhorias Propostas

**Variáveis não contam para as horas.** O verificador não deteta que `VAR h = 10` seguido de `STUDY "Matematica" FOR h HOURS` excede `RESOURCE TIME 5 HOURS`.

Isto acontece porque uma variável tem sempre `const = false`, ou seja, o verificador não sabe o valor da variável. Por isso, o `STUDY` conta 0 horas para o `minHours`.

É uma escolha conservadora: o verificador só conta as horas que tem a certeza que são alocadas, para nunca dar falsos positivos (erros que não existem).

**Melhoria:** guardar no ambiente (`env`) o valor das variáveis declaradas com um valor constante (propagação de constantes).

**Condições sem agrupamento.** A linguagem não permite parênteses à volta de condições, por exemplo `(A OR B) AND C`. O programa dá erro sintático, porque o parser, ao ver `(`, espera uma expressão aritmética e não uma comparação.

É possível escrever o mesmo usando a precedência `AND` > `OR`: `A AND C OR B AND C`. No entanto, a condição fica mais longa e menos legível, e `C` tem de ser repetido.

**Melhoria:** permitir parênteses nas condições.

**Mensagens de erro sintático pouco informativas.** No caso acima, o erro diz apenas “token inesperado”, sem indicar o que era esperado naquele ponto.

**Melhoria:** mostrar na mensagem os tokens que seriam aceites naquele ponto, informação que o Lark já fornece.

**Resumo das limitações.**

| Limitação | Melhoria proposta |
|---|---|
| Variáveis não contam para as horas | Guardar no ambiente o valor das variáveis constantes (propagação de constantes) |
| Condições sem agrupamento | Permitir parênteses nas condições |
| Mensagens de erro sintático pouco informativas | Mostrar os tokens que seriam aceites naquele ponto |
| Horas que dependem de `u.CREDITS` ou `u.DIFFICULTY` não contam para o limite | Avaliar o corpo do `FOR EACH` uma vez por UC da lista |
| Só existem números inteiros | Acrescentar números decimais (por exemplo `1.5 HOURS`) |
| Não há limite diário de horas (por exemplo, 24 h por dia) | Acrescentar a noção de dias ao plano e uma condição de contexto para o limite |
| É preciso repetir os nomes das UCs em cada `FOR EACH` | Permitir iterar sobre todas as UCs declaradas |
| O erro de `RESOURCE` duplicado aparece na linha 1 | Indicar a linha do segundo `RESOURCE` |

## 4.5. Síntese

Em resumo, a StudyLang é adequada ao domínio do planeamento de estudo: as suas construções (`UC`, `STUDY … FOR … HOURS`, `RESOURCE TIME`, `LEVEL`) correspondem diretamente aos conceitos do estudante, e a linguagem tem uma só forma de repetir e de decidir, o que a torna fácil de aprender.

A gramática é pequena (57 produções), sem ambiguidade (o parser LALR(1) é construído sem conflitos) e com poucas dependências entre símbolos, o que facilita a sua manutenção. A gramática de atributos é L-atribuída e avalia-se numa só passagem, reportando todos os erros de uma vez.

Os principais pontos fracos são a falta de documentação, a necessidade de repetir os nomes das UCs em planos grandes e algumas verificações que deixam escapar erros, como as horas atribuídas através de variáveis. As melhorias propostas na secção 4.4 seriam um bom ponto de partida para a Parte II do projeto.