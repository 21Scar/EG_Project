## ex7_analise

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

Erros semânticos (check_studylang): nenhum

### Grafo de fluxo de controlo (CFG)

- Instruções no CFG: 14; blocos básicos: 8 (+ENTRY, EXIT)
- Arestas entre blocos: 11; arestas de retorno (ciclos): B7→B2
- Complexidade ciclomática V(G) = E − N + 2 = 11 − 10 + 2 = 3 (= decisões + 1 = 2 + 1)
- Caminhos ENTRY→EXIT com cada ciclo percorrido 0 ou 1 vezes: 3 (o caminho que salta o ciclo é impossível na prática: as listas do FOR EACH nunca são vazias)
- Profundidade máxima de aninhamento: 2
- Instruções estruturalmente inalcançáveis: nenhuma
- Terminação: o único ciclo é FOR EACH sobre uma lista literal finita, por isso o programa termina sempre; no máximo 18 execuções de instruções do plano.

| Bloco | Instruções |
|---|---|
| B1 | l.3 `UC "Algebra" { CREDITS 6 DIFFICULTY 5 }`<br>l.4 `UC "Historia" { CREDITS 3 DIFFICULTY 1 }`<br>l.6 `RESOURCE TIME 25 HOURS`<br>l.7 `VAR base = 2`<br>l.8 `VAR bonus = 10`<br>l.11 `VAR total = 0`<br>l.12 `bonus = 1` |
| B2 | l.13 `FOR EACH u IN ["Algebra", "Historia"]` |
| B3 | l.14 `VAR h = base * u.DIFFICULTY` |
| B4 | l.15 `IF ( base > 10 )` |
| B5 | l.16 `STUDY u FOR 50 HOURS` |
| B6 | l.18 `STUDY u FOR h + bonus HOURS` |
| B7 | l.20 `total = total + h` |
| B8 | l.22 `VAR resto = 25 - total` |

### Definições e usos; reaching definitions (DFG)

Ponto fixo atingido em 3 iterações.

| Nó | Linha | Instrução | Def | Use | Definições que chegam aos usos |
|---|---|---|---|---|---|
| S5 | 7 | `VAR base = 2` | base |  |  |
| S6 | 8 | `VAR bonus = 10` | bonus |  |  |
| S7 | 11 | `VAR total = 0` | total |  |  |
| S8 | 12 | `bonus = 1` | bonus |  |  |
| S9 | 13 | `FOR EACH u IN ["Algebra", "Historia"]` | u |  |  |
| S10 | 14 | `VAR h = base * u.DIFFICULTY` | h | base, u | base←S5, u←S9 |
| S11 | 15 | `IF ( base > 10 )` |  | base | base←S5 |
| S12 | 16 | `STUDY u FOR 50 HOURS` |  | u | u←S9 |
| S13 | 18 | `STUDY u FOR h + bonus HOURS` |  | bonus, h, u | bonus←S8, h←S10, u←S9 |
| S14 | 20 | `total = total + h` | total | h, total | h←S10, total←S14, total←S7 |
| S15 | 22 | `VAR resto = 25 - total` | resto | total | total←S14, total←S7 |

- Dependências verdadeiras (fluxo): 12
- Antidependências (lê antes de ser reescrita): 5 — S10→S9 (u), S12→S9 (u), S13→S10 (h), S13→S9 (u), S14→S10 (h)
- Dependências de saída (duas escritas da mesma variável): 5 — S10→S10 (h, entre iterações), S14→S14 (total, entre iterações), S6→S8 (bonus), S7→S14 (total), S9→S9 (u, entre iterações)
- Se ignorássemos os âmbitos (variáveis só pelo nome): 12 dependências, 0 falsas

### PDG e slicing

Fatia para trás (backward slice) de cada STUDY, seguindo dependências de dados e de controlo:

| Critério | Instruções na fatia (linhas) |
|---|---|
| l.16 `STUDY u FOR 50 HOURS` | 7, 13, 15, 16 |
| l.18 `STUDY u FOR h + bonus HOURS` | 7, 12, 13, 14, 15, 18 |

- Definições nunca lidas: `VAR bonus = 10` (l.8), `VAR resto = 25 - total` (l.22)
- Instruções fora de todas as fatias (não influenciam nenhuma hora de estudo): `VAR bonus = 10` (l.8), `VAR total = 0` (l.11), `total = total + h` (l.20), `VAR resto = 25 - total` (l.22)

### Análise estática das horas (P11)

RESOURCE TIME = 25 horas.

| Análise | Horas do plano | Veredicto |
|---|---|---|
| AG atual (`minHours`, só constantes) | ≥ 0 | não deteta excesso |
| Intervalos, sem avaliar condições | [6, 100] | pode exceder (alarme possível) |
| Intervalos, com condições (abstract interpretation) | [6, 22] | cumpre de certeza |
| Avaliação exata (ciclos desenrolados por UC) | 14 | cumpre de certeza |

Plano efetivo (avaliação exata): Algebra: 11 h, Historia: 3 h

| Condição | Intervalos (T = sempre verdadeira, F = sempre falsa, ? = depende) | Valores observados na avaliação exata |
|---|---|---|
| l.15 `IF ( base > 10 )` | F | F |

- Ramos impossíveis provados pela análise de intervalos: S11→S12; instruções inalcançáveis: `STUDY u FOR 50 HOURS` (l.16)
- Ramos nunca executados com estes dados (avaliação exata): l.15 ramo V

### Diagnósticos

| Nível | Linha | Código | Mensagem |
|---|---|---|---|
| aviso | 8 | DEF_MORTA | o valor de `bonus` definido aqui nunca é lido: `VAR bonus = 10` |
| aviso | 11 | SEM_EFEITO | não influencia nenhuma hora de estudo: `VAR total = 0` |
| aviso | 15 | COND_CONST | condição sempre falsa: `IF ( base > 10 )` |
| aviso | 16 | INALCANCAVEL | instrução inalcançável: `STUDY u FOR 50 HOURS` |
| aviso | 20 | SEM_EFEITO | não influencia nenhuma hora de estudo: `total = total + h` |
| aviso | 22 | DEF_MORTA | o valor de `resto` definido aqui nunca é lido: `VAR resto = 25 - total` |
