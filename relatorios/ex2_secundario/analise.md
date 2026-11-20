## ex2_secundario

```study
STUDENT Joao LEVEL SECONDARY

UC "Matematica A" { DIFFICULTY 5 }
UC "Fisica"       { DIFFICULTY 4 }
UC "Portugues"    { DIFFICULTY 2 }

RESOURCE TIME 20 HOURS
VAR base = 2                          // variavel global

PLAN {
    VAR extra = 1                     // local ao PLAN
    FOR EACH u IN [ "Matematica A", "Fisica", "Portugues" ] {
        VAR h = base + u.DIFFICULTY   // local ao corpo do ciclo
        IF ( u.DIFFICULTY >= 4 ) {
            VAR extra = 2             // shadowing permitido num bloco interior
            STUDY u FOR h + extra HOURS
        } ELSE {
            STUDY u FOR h HOURS
        }
    }
    extra = extra + 1
}
```

Erros semânticos (check_studylang): nenhum

### Grafo de fluxo de controlo (CFG)

- Instruções no CFG: 13; blocos básicos: 7 (+ENTRY, EXIT)
- Arestas entre blocos: 10; arestas de retorno (ciclos): B5→B2, B6→B2
- Complexidade ciclomática V(G) = E − N + 2 = 10 − 9 + 2 = 3 (= decisões + 1 = 2 + 1)
- Caminhos ENTRY→EXIT com cada ciclo percorrido 0 ou 1 vezes: 3 (o caminho que salta o ciclo é impossível na prática: as listas do FOR EACH nunca são vazias)
- Profundidade máxima de aninhamento: 2
- Instruções estruturalmente inalcançáveis: nenhuma
- Terminação: o único ciclo é FOR EACH sobre uma lista literal finita, por isso o programa termina sempre; no máximo 22 execuções de instruções do plano.

| Bloco | Instruções |
|---|---|
| B1 | l.3 `UC "Matematica A" { DIFFICULTY 5 }`<br>l.4 `UC "Fisica" { DIFFICULTY 4 }`<br>l.5 `UC "Portugues" { DIFFICULTY 2 }`<br>l.7 `RESOURCE TIME 20 HOURS`<br>l.8 `VAR base = 2`<br>l.11 `VAR extra = 1` |
| B2 | l.12 `FOR EACH u IN ["Matematica A", "Fisica", "Portugues"]` |
| B3 | l.13 `VAR h = base + u.DIFFICULTY` |
| B4 | l.14 `IF ( u.DIFFICULTY >= 4 )` |
| B5 | l.15 `VAR extra = 2`<br>l.16 `STUDY u FOR h + extra HOURS` |
| B6 | l.18 `STUDY u FOR h HOURS` |
| B7 | l.21 `extra = extra + 1` |

### Definições e usos; reaching definitions (DFG)

Ponto fixo atingido em 3 iterações.

| Nó | Linha | Instrução | Def | Use | Definições que chegam aos usos |
|---|---|---|---|---|---|
| S6 | 8 | `VAR base = 2` | base |  |  |
| S7 | 11 | `VAR extra = 1` | extra@11 |  |  |
| S8 | 12 | `FOR EACH u IN ["Matematica A", "Fisica", "Portugues"]` | u |  |  |
| S9 | 13 | `VAR h = base + u.DIFFICULTY` | h | base, u | base←S6, u←S8 |
| S10 | 14 | `IF ( u.DIFFICULTY >= 4 )` |  | u | u←S8 |
| S11 | 15 | `VAR extra = 2` | extra@15 |  |  |
| S12 | 16 | `STUDY u FOR h + extra HOURS` |  | extra@15, h, u | extra@15←S11, h←S9, u←S8 |
| S13 | 18 | `STUDY u FOR h HOURS` |  | h, u | h←S9, u←S8 |
| S14 | 21 | `extra = extra + 1` | extra@11 | extra@11 | extra@11←S7 |

- Dependências verdadeiras (fluxo): 9
- Antidependências (lê antes de ser reescrita): 7 — S10→S8 (u), S12→S11 (extra@15), S12→S8 (u), S12→S9 (h), S13→S8 (u), S13→S9 (h), S9→S8 (u)
- Dependências de saída (duas escritas da mesma variável): 4 — S11→S11 (extra@15, entre iterações), S7→S14 (extra@11), S8→S8 (u, entre iterações), S9→S9 (h, entre iterações)
- Se ignorássemos os âmbitos (variáveis só pelo nome): 10 dependências, 1 falsas — S11→S14 (extra)

### PDG e slicing

Fatia para trás (backward slice) de cada STUDY, seguindo dependências de dados e de controlo:

| Critério | Instruções na fatia (linhas) |
|---|---|
| l.16 `STUDY u FOR h + extra HOURS` | 8, 12, 13, 14, 15, 16 |
| l.18 `STUDY u FOR h HOURS` | 8, 12, 13, 14, 18 |

- Definições nunca lidas: `extra = extra + 1` (l.21)
- Instruções fora de todas as fatias (não influenciam nenhuma hora de estudo): `VAR extra = 1` (l.11), `extra = extra + 1` (l.21)

### Análise estática das horas (P11)

RESOURCE TIME = 20 horas.

| Análise | Horas do plano | Veredicto |
|---|---|---|
| AG atual (`minHours`, só constantes) | ≥ 0 | não deteta excesso |
| Intervalos, sem avaliar condições | [12, 27] | pode exceder (alarme possível) |
| Intervalos, com condições (abstract interpretation) | [12, 27] | pode exceder (alarme possível) |
| Avaliação exata (ciclos desenrolados por UC) | 21 | excede de certeza (21 > 20) |

Plano efetivo (avaliação exata): Matematica A: 9 h, Fisica: 8 h, Portugues: 4 h

| Condição | Intervalos (T = sempre verdadeira, F = sempre falsa, ? = depende) | Valores observados na avaliação exata |
|---|---|---|
| l.14 `IF ( u.DIFFICULTY >= 4 )` | ? | F/T |

- Ramos impossíveis provados pela análise de intervalos: nenhum; instruções inalcançáveis: nenhuma
- Ramos nunca executados com estes dados (avaliação exata): nenhum

### Diagnósticos

| Nível | Linha | Código | Mensagem |
|---|---|---|---|
| erro | 10 | HORAS | o plano aloca 21 h e só há 20 h em RESOURCE TIME (a AG só garante ≥ 0 h e não deteta o excesso) |
| aviso | 11 | SEM_EFEITO | não influencia nenhuma hora de estudo: `VAR extra = 1` |
| aviso | 21 | DEF_MORTA | o valor de `extra@11` definido aqui nunca é lido: `extra = extra + 1` |
