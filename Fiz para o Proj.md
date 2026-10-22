### 2. Exemplos e verificação

- **Ex1, universitário (válido):** `FOR EACH`, `IF / ELSE IF / ELSE`, `AND/OR/NOT`, `u.CREDITS` e `u.DIFFICULTY`.
- **Ex2, secundário (válido):** UCs só com `DIFFICULTY`, variável global, local ao `PLAN` e local ao ciclo, e _shadowing_ de `extra` num bloco interior.
- **Ex3, secundário (10 erros semânticos):** o antigo exemplo da Ana, adaptado e com erros novos de nível. Foram detetados os 10: `CREDITS` no secundário (declaração e `u.CREDITS`), UC repetida, excesso de horas, UC não declarada, variável não declarada, redeclaração, variável fora de âmbito, `x.DIFFICULTY` com `x` não-UC e divisão por zero.
- **Ex4, universitário:** falta `CREDITS`, dois `RESOURCE` e horas = 0. Os três erros foram detetados.
- **Ex5:** um programa sem `LEVEL` é rejeitado já pelo parser, o que mostra a separação entre erros sintáticos e semânticos.
Estes exemplos testaram a gramática se estiver bem escrita e se estiver mal escrita ou com erros, era importante verificarmos se conseguimos ter as limitações que falei no ficheiro (tipo não conseguir criar um plano de mais de 24 horas por dia  por exemplo)