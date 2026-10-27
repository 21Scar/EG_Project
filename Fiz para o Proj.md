### 2. Exemplos e verificação

- **Ex1, universitário (válido):** `FOR EACH`, `IF / ELSE IF / ELSE`, `AND/OR/NOT`, `u.CREDITS` e `u.DIFFICULTY`.
- **Ex2, secundário (válido):** UCs só com `DIFFICULTY`, variável global, local ao `PLAN` e local ao ciclo, e _shadowing_ de `extra` num bloco interior.
- **Ex3, secundário (10 erros semânticos):** o antigo exemplo da Ana, adaptado e com erros novos de nível. Foram detetados os 10: `CREDITS` no secundário (declaração e `u.CREDITS`), UC repetida, excesso de horas, UC não declarada, variável não declarada, redeclaração, variável fora de âmbito, `x.DIFFICULTY` com `x` não-UC e divisão por zero.
- **Ex4, universitário:** falta `CREDITS`, dois `RESOURCE` e horas = 0. Os três erros foram detetados.
- **Ex5:** um programa sem `LEVEL` é rejeitado já pelo parser, o que mostra a separação entre erros sintáticos e semânticos.
Estes exemplos testaram a gramática se estiver bem escrita e se estiver mal escrita ou com erros, era importante verificarmos se conseguimos ter as limitações que falei no ficheiro (tipo não conseguir criar um plano de mais de 24 horas por dia  por exemplo)


---
O que atualizei 27/10/2026 Leonor

- fase_1_desenho_da_linguagem.md: acrescentei o conceito de nível (LEVEL) e uma tabela com os requisitos mínimos do enunciado e como a linguagem os cumpre. Os cinco exemplos do verificador substituem os três antigos, com os comentários de erro intactos.
- fase_2_especifica_o_lexical_e_sint_tica.md: o léxico e a EBNF seguem a gramática atual (LEVEL, CREDITS opcional, ELSE opcional, REL_OP). As decisões de desenho ficam justificadas, incluindo porquê um só CREDITS opcional e porquê o lexer="basic". A secção 2.4 tem o .lark completo.
- fase_3_especificacao_semantica.md: reescrevi as regras a partir do check_studylang.py. A tabela passou a 11 propriedades (P1 a P11) com o exemplo e a linha onde cada uma é violada. A secção 3.6 liga cada parte da AG à função do código que a implementa. A secção 3.7 é um rascunho da qualidade (tarefa 4 do enunciado).

Pontos a decidir em grupo:

- LarkAG: o verificador não usa o LarkAG das aulas, avalia a AG com funções recursivas. Escrevi isso no documento (3.6) em vez de o esconder. Se o professor exigir o formato do NB06, a tradução é direta, porque a AG é L-atribuída. Convém perguntar-lhe antes de investir tempo.
- Limitações: o README fala de um limite de 24 horas por dia, mas o código não o verifica, por isso não o pus como propriedade. Está listado como limitação na 3.7. Se quiserem a regra, é uma verificação nova no check_studylang.py (e uma linha na tabela P).
- Mensagem do Ex4: o erro “mais do que um RESOURCE” aparece na linha 1 em vez de na linha do segundo RESOURCE. Não afeta nada, mas é a única mensagem com a linha pouco precisa.