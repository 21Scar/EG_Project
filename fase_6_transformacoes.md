# 6. Transformações

Esta secção corresponde à tarefa 3 da Parte II. Todas as transformações estão em `transformacoes.py` e são aplicadas à árvore validada da Parte I:

| Transformação | Comando | Tipo | Resultado |
|---|---|---|---|
| *Pretty-printer* | (usada pelas outras) | árvore → código | código *StudyLang* normalizado |
| Otimização | `studylang.py otimizar` | reescrita *StudyLang* → *StudyLang* | o mesmo plano, sem código inútil |
| Planificação | `studylang.py planificar [--agregar]` | avaliação parcial *StudyLang* → *StudyLang* | um plano só com `STUDY "UC" FOR n HOURS` |
| Exportação | `studylang.py exportar --formato md\|csv\|json` | tradução para outra representação | tabela do plano efetivo |

## 6.1. Significado de um plano e critério de correção

Para dizer se uma transformação "preserva o significado", é preciso definir esse significado. Na *StudyLang*, o comportamento observável de um plano são as sessões de estudo que ele produz. Por isso, o **significado de um programa** é a **sequência de sessões `(UC, horas)`** pela ordem em que são executadas. É calculado pela avaliação exata (secção 5.4) e está em `transformacoes.meaning`.

Para o Ex1, por exemplo:

```text
[("Sistemas Distribuidos", 12), ("Engenharia Gramatical", 12), ("Redes", 2), ("Redes", 3)]
```

Uma transformação é **correta** se o programa resultante:

1. for aceite pelo parser e pela gramática de atributos da Parte I;
2. tiver o **mesmo significado** que o original. Na planificação agregada, que junta as sessões de cada UC, o critério é mais fraco: as **mesmas horas por UC**.

## 6.2. *Pretty-printer*

`pretty(tree)` converte uma árvore no texto *StudyLang* correspondente. É a base das outras transformações, que reescrevem a árvore e só no fim a convertem em texto. Os parênteses só aparecem onde são necessários para que o texto volte a dar **exatamente a mesma árvore**:

* à esquerda, quando o operando tem menor precedência;
* à direita, quando tem precedência menor ou igual, porque os operadores são associativos à esquerda.

Propriedade testada: `parse(pretty(t)) == t` para os exemplos e para todos os programas aleatórios. Os comentários perdem-se, porque o Lark não os guarda na árvore.

## 6.3. Otimização

`optimize(source)` aplica dois passos alternadamente, até que nenhum deles altere o programa. Esse ponto fixo é atingido em 2 rondas nos três exemplos.

**Passo 1: propagação e dobragem de constantes, e eliminação de ramos.** Corre a interpretação abstrata com intervalos (secção 5.4) e regista o intervalo de cada expressão e o valor (T/F/?) de cada condição, juntando todas as vezes que são avaliadas.

* Uma expressão cujo intervalo é um único valor `[c, c]` é substituída pelo literal `c`. Isto cobre tanto a propagação de constantes (`bonus` → `1`) como a dobragem (`max_session * 3` → `12`).
* Numa condição composta, uma parte sempre verdadeira ou sempre falsa é simplificada: `c AND T` dá `c`, e `c OR F` dá `c`.
* Um `IF` cuja condição é sempre verdadeira ou sempre falsa é substituído pelo ramo que executa. Sem `ELSE` e com condição sempre falsa, o `IF` desaparece.

**Passo 2: eliminação de código sem efeito.** Usa as fatias do PDG (secção 5.3.4). Remove declarações, atribuições, `IF` e `FOR EACH` que não pertencem à fatia de nenhum `STUDY`. Um `IF` ou `FOR EACH` fora das fatias não contém nenhum `STUDY` nem nada de que um `STUDY` dependa, por isso pode ser removido por inteiro.

**Condições de segurança.** Os testes ajudaram a encontrar estas duas:

* **Âmbitos.** Colocar o conteúdo de um ramo no bloco exterior só é seguro se o ramo não declarar variáveis. Caso contrário, o nome passaria a ser visível fora do ramo e poderia colidir com outro (P6) ou mudar a que declaração se referem os usos seguintes. Quando o ramo declara variáveis, o `IF` fica, mas o ramo impossível é removido.
* **Declarações necessárias.** Um `VAR` cujo valor nunca é lido, por ser reescrito antes de qualquer uso, não pode ser removido se a variável continuar a ser usada ou atribuída: o nome tem de continuar declarado (P5). Este caso foi encontrado pelos testes com programas aleatórios, e a regra foi corrigida.

**Só usa os intervalos, não a avaliação exata.** Um ramo que nenhuma UC atual executa (`RAMO_NAO_EXEC`) **não** é removido, porque é só uma propriedade dos dados atuais. Com os intervalos, um ramo só é removido se for impossível para qualquer UC da lista.

**Resultados nos exemplos:**

| Exemplo | Alterações | Instruções no CFG (VAR globais + plano): antes → depois |
|---|---|---|
| Ex1 | `h <= max_session * 3` é sempre verdadeira e sai da condição; `max_session` → 4; `VAR max_session` removida | 9 → 8 |
| Ex2 | `base` → 2 e `extra` → 2 propagados; `VAR base`, as duas `VAR extra` e `extra = extra + 1` removidas | 9 → 5 |
| Ex7 | `base` → 2 e `bonus` → 1 propagados; `IF (base > 10)` substituído pelo ramo `ELSE`; 6 instruções sem efeito removidas | 11 → 3 |

O Ex7 otimizado fica assim:

```study
PLAN {
    FOR EACH u IN [ "Algebra", "Historia" ] {
        VAR h = 2 * u.DIFFICULTY
        STUDY u FOR h + 1 HOURS
    }
}
```

O registo de alterações indica as **linhas do ficheiro original**. Isto é possível porque os nós reescritos herdam a posição (`meta`) do nó de origem, e os passos seguintes trabalham sobre a árvore e não sobre texto reformatado:

```text
l.14: `base` → 2 (constante)
l.18: `bonus` → 1 (constante)
l.15: condição sempre falsa, o IF é substituído pelo ramo ELSE
l.7: removida instrução sem efeito no plano: `VAR base = 2`
...
```

## 6.4. Planificação (avaliação parcial)

`flatten(source)` avalia o programa e escreve-o de novo **sem variáveis, ciclos nem condições**: um `STUDY "UC" FOR n HOURS` por sessão, pela ordem de execução. Com `--agregar`, escreve uma sessão por UC. Mantém o estudante, o nível, as UCs e o `RESOURCE`.

Esta transformação tem uma consequência importante: **no plano planificado, a P11 da gramática de atributos da Parte I passa a ser exata**, porque todas as horas são constantes. O Ex2 planificado é rejeitado pelo próprio verificador da Parte I:

```text
$ python studylang.py planificar exemplos/ex2_secundario.study --agregar
...
PLAN {
    STUDY "Matematica A" FOR 9 HOURS
    STUDY "Fisica" FOR 8 HOURS
    STUDY "Portugues" FOR 4 HOURS
}
// plano planificado: 3 sessões; verificação da AG sobre o resultado: horas garantidas (21) excedem RESOURCE TIME (20)
```

## 6.5. Exportação

`export(source, fmt)` traduz o plano efetivo para Markdown, CSV ou JSON, para usar fora da linguagem (folha de cálculo, outra aplicação). Por UC, indica os créditos, a dificuldade, as sessões, as horas, a percentagem do `RESOURCE TIME` e as horas por crédito. Para o Ex1:

```text
uc;creditos;dificuldade;sessoes;horas;percentagem_do_recurso;horas_por_credito
Sistemas Distribuidos;6;4;1;12;40.0;2.0
Engenharia Gramatical;6;5;1;12;40.0;2.0
Redes;3;2;2;5;16.7;1.67
```

## 6.6. Evidência de correção

Os testes estão em `tests/test_studylang.py` e correm com `python -m unittest discover -s tests`. Há dois tipos.

**Testes sobre os exemplos.** Verificam os valores esperados das análises e das transformações. Por exemplo:

* o Ex7 otimizado não tem `IF` nem `total`;
* o Ex2 planificado é rejeitado pela P11;
* o registo de alterações usa as linhas do ficheiro original.

**Testes de propriedades sobre programas aleatórios.** Um gerador produz programas *StudyLang* válidos com semente fixa, para que os resultados sejam reprodutíveis: níveis, 1 a 4 UCs, variáveis globais e locais com *shadowing*, atribuições, `IF/ELSE` e condições compostas, `FOR EACH` aninhados e divisões. Dos 150 programas dos testes, 86 têm ciclos, 53 têm ciclos aninhados e 77 têm `IF`; em média têm 20 linhas. Para cada um verifica-se:

| Propriedade | O que garante |
|---|---|
| `parse(pretty(t)) == t` | o *pretty-printer* não altera a estrutura |
| otimizado é válido e `meaning(otimizado) == meaning(original)` | a otimização preserva o plano |
| `optimize(optimize(p)) == optimize(p)`, com registo vazio | a otimização atinge um ponto fixo |
| número de instruções não aumenta | a otimização nunca piora o programa |
| `meaning(flatten(p)) == meaning(p)`; horas por UC iguais na versão agregada | a planificação preserva o plano |
| `minHours ≤ horas exatas`, e horas exatas ∈ intervalos (com e sem condições) | as análises da secção 5 são sólidas |
| grafo de atributos L-atribuído e respeitado pela passagem única | a afirmação da secção 5.2.3 vale para outros programas além dos exemplos |

Além dos 150 programas dos testes, as mesmas propriedades foram verificadas em 1000 programas gerados com outras 5 sementes, sem falhas. A otimização alterou 999 deles e removeu 2703 instruções. Os testes encontraram dois erros durante o desenvolvimento, ambos corrigidos: o cálculo de caminhos em ciclos aninhados e a remoção de uma declaração ainda necessária.

Os testes dão evidência forte, mas não são uma prova: o gerador não produz todos os programas possíveis. Por exemplo, todas as horas são positivas, e só se divide por literais positivos.
