## ex1_universitario

```study
STUDENT Leonor LEVEL UNIVERSITY

UC "Sistemas Distribuidos" { CREDITS 6 DIFFICULTY 4 }
UC "Engenharia Gramatical" { CREDITS 6 DIFFICULTY 5 }
UC "Redes"                 { CREDITS 3 DIFFICULTY 2 }

RESOURCE TIME 30 HOURS
VAR max_session = 4

PLAN {
    FOR EACH u IN [ "Sistemas Distribuidos", "Engenharia Gramatical", "Redes" ] {
        VAR h = u.CREDITS * 2
        IF ( u.DIFFICULTY > 3 AND h <= max_session * 3 ) {
            STUDY u FOR h HOURS
        } ELSE IF ( u.CREDITS < 4 OR NOT u.DIFFICULTY > 2 ) {
            STUDY u FOR 2 HOURS
        } ELSE {
            STUDY u FOR max_session HOURS
        }
    }
    STUDY "Redes" FOR 3 HOURS
}
```

Erros semânticos (check_studylang): nenhum

### Grafo de fluxo de controlo (CFG)

- Instruções no CFG: 13; blocos básicos: 9 (+ENTRY, EXIT)
- Arestas entre blocos: 13; arestas de retorno (ciclos): B5→B2, B7→B2, B8→B2
- Complexidade ciclomática V(G) = E − N + 2 = 13 − 11 + 2 = 4 (= decisões + 1 = 3 + 1)
- Caminhos ENTRY→EXIT com cada ciclo percorrido 0 ou 1 vezes: 4 (o caminho que salta o ciclo é impossível na prática: as listas do FOR EACH nunca são vazias)
- Profundidade máxima de aninhamento: 3
- Instruções estruturalmente inalcançáveis: nenhuma
- Terminação: o único ciclo é FOR EACH sobre uma lista literal finita, por isso o programa termina sempre; no máximo 24 execuções de instruções do plano.

| Bloco | Instruções |
|---|---|
| B1 | l.3 `UC "Sistemas Distribuidos" { CREDITS 6 DIFFICULTY 4 }`<br>l.4 `UC "Engenharia Gramatical" { CREDITS 6 DIFFICULTY 5 }`<br>l.5 `UC "Redes" { CREDITS 3 DIFFICULTY 2 }`<br>l.7 `RESOURCE TIME 30 HOURS`<br>l.8 `VAR max_session = 4` |
| B2 | l.11 `FOR EACH u IN ["Sistemas Distribuidos", "Engenharia Gramatical", "Redes"]` |
| B3 | l.12 `VAR h = u.CREDITS * 2` |
| B4 | l.13 `IF ( u.DIFFICULTY > 3 AND h <= max_session * 3 )` |
| B5 | l.14 `STUDY u FOR h HOURS` |
| B6 | l.15 `IF ( u.CREDITS < 4 OR NOT u.DIFFICULTY > 2 )` |
| B7 | l.16 `STUDY u FOR 2 HOURS` |
| B8 | l.18 `STUDY u FOR max_session HOURS` |
| B9 | l.21 `STUDY "Redes" FOR 3 HOURS` |

### Definições e usos; reaching definitions (DFG)

Ponto fixo atingido em 3 iterações.

| Nó | Linha | Instrução | Def | Use | Definições que chegam aos usos |
|---|---|---|---|---|---|
| S6 | 8 | `VAR max_session = 4` | max_session |  |  |
| S7 | 11 | `FOR EACH u IN ["Sistemas Distribuidos", "Engenharia Gramatical", "Redes"]` | u |  |  |
| S8 | 12 | `VAR h = u.CREDITS * 2` | h | u | u←S7 |
| S9 | 13 | `IF ( u.DIFFICULTY > 3 AND h <= max_session * 3 )` |  | h, max_session, u | h←S8, max_session←S6, u←S7 |
| S10 | 14 | `STUDY u FOR h HOURS` |  | h, u | h←S8, u←S7 |
| S11 | 15 | `IF ( u.CREDITS < 4 OR NOT u.DIFFICULTY > 2 )` |  | u | u←S7 |
| S12 | 16 | `STUDY u FOR 2 HOURS` |  | u | u←S7 |
| S13 | 18 | `STUDY u FOR max_session HOURS` |  | max_session, u | max_session←S6, u←S7 |
| S14 | 21 | `STUDY "Redes" FOR 3 HOURS` |  |  |  |

- Dependências verdadeiras (fluxo): 10
- Antidependências (lê antes de ser reescrita): 8 — S10→S7 (u), S10→S8 (h), S11→S7 (u), S12→S7 (u), S13→S7 (u), S8→S7 (u), S9→S7 (u), S9→S8 (h)
- Dependências de saída (duas escritas da mesma variável): 2 — S7→S7 (u, entre iterações), S8→S8 (h, entre iterações)
- Se ignorássemos os âmbitos (variáveis só pelo nome): 10 dependências, 0 falsas

### PDG e slicing

Fatia para trás (backward slice) de cada STUDY, seguindo dependências de dados e de controlo:

| Critério | Instruções na fatia (linhas) |
|---|---|
| l.14 `STUDY u FOR h HOURS` | 8, 11, 12, 13, 14 |
| l.16 `STUDY u FOR 2 HOURS` | 8, 11, 12, 13, 15, 16 |
| l.18 `STUDY u FOR max_session HOURS` | 8, 11, 12, 13, 15, 18 |
| l.21 `STUDY "Redes" FOR 3 HOURS` | 21 |

- Definições nunca lidas: nenhuma
- Instruções fora de todas as fatias (não influenciam nenhuma hora de estudo): nenhuma

### Análise estática das horas (P11)

RESOURCE TIME = 30 horas.

| Análise | Horas do plano | Veredicto |
|---|---|---|
| AG atual (`minHours`, só constantes) | ≥ 3 | não deteta excesso |
| Intervalos, sem avaliar condições | [9, 39] | pode exceder (alarme possível) |
| Intervalos, com condições (abstract interpretation) | [9, 39] | pode exceder (alarme possível) |
| Avaliação exata (ciclos desenrolados por UC) | 29 | cumpre de certeza |

Plano efetivo (avaliação exata): Sistemas Distribuidos: 12 h, Engenharia Gramatical: 12 h, Redes: 5 h

| Condição | Intervalos (T = sempre verdadeira, F = sempre falsa, ? = depende) | Valores observados na avaliação exata |
|---|---|---|
| l.13 `IF ( u.DIFFICULTY > 3 AND h <= max_session * 3 )` | ? | F/T |
| l.15 `IF ( u.CREDITS < 4 OR NOT u.DIFFICULTY > 2 )` | ? | T |

- Ramos impossíveis provados pela análise de intervalos: nenhum; instruções inalcançáveis: nenhuma
- Ramos nunca executados com estes dados (avaliação exata): l.15 ramo F

### Diagnósticos

| Nível | Linha | Código | Mensagem |
|---|---|---|---|
| info | 10 | HORAS | os intervalos admitem até 39 h, mas a avaliação exata dá 29 h ≤ 30: o limite é cumprido |
| info | 15 | RAMO_NAO_EXEC | o ramo F de `IF ( u.CREDITS < 4 OR NOT u.DIFFICULTY > 2 )` nunca é executado com as UCs deste plano |
