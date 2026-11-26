# Grafos e análise estática da StudyLang (gerado por parte2/visualizacao.py)

Ficheiro gerado automaticamente: não editar à mão. Os grafos estão em `resultados/grafos/*.dot` e podem ser vistos em `resultados/grafos/index.html`.

## 1. Grafo de dependências da gramática

- Não-terminais: 28; arestas distintas: 45
- Grau médio de entrada/saída: 1.61 / 1.61
- Maior grau de entrada (símbolos mais reutilizados): `expr` (6), `block` (4), `__start_star_0` (2), `var_decl` (2), `__block_star_1` (2)
- Recursividade direta (9): `__block_star_1`, `__start_star_0`, `__string_list_star_2`, `and_cond`, `expr`, `factor`, `not_cond`, `or_cond`, `term`
- Recursividade indireta (2 ciclos):
  - {`expr`, `factor`, `term`}
  - {`__block_star_1`, `block`, `else_part`, `foreach_stmt`, `if_stmt`, `stmt`}
- Símbolos inacessíveis a partir de `start`: nenhum
- Símbolos improdutivos: nenhum
- Profundidade do grafo condensado (níveis de SCCs a partir de `start`): 8

## 2. Grafos de dependências da gramática de atributos

- Produções com regras semânticas: 31
- Regras de avaliação (atributos definidos, contando por produção): 113
- Grafo global: 97 nós (ocorrências símbolo.atributo), 142 arestas
- Grau médio de entrada/saída: 1.46 / 1.46
- Maior grau de entrada (atributos com mais dependências): `expr.errors` (7), `study_stmt.errors` (7), `start.errors` (6), `cond.errors` (6), `expr.type` (5)
- Maior grau de saída (atributos mais usados): `ID.name` (7), `stmt.env_in` (6), `expr.env` (4), `block.errors` (4), `block.minHours` (4)
- Verificação L-atribuída (todas as produções): OK, nenhuma aresta viola a condição

### Grafo de dependências instanciado nas árvores dos exemplos

| Programa | Ocorrências | Atributos (nós) | Dependências (arestas) | Acíclico | Violações L-atribuída | Violações da ordem de uma passagem |
|---|---|---|---|---|---|---|
| Ex1 universitário | 98 | 264 | 314 | sim | 0 | 0 |
| Ex2 secundário | 80 | 233 | 279 | sim | 0 | 0 |
| Ex7 análise | 90 | 263 | 310 | sim | 0 | 0 |

Programa mínimo usado no grafo `ag_instancia_mini`:

```study
STUDENT Ana LEVEL SECONDARY
UC "Fisica" { DIFFICULTY 3 }
PLAN {
    VAR h = 2
    STUDY "Fisica" FOR h * 2 HOURS
}
```

O grafo instanciado do programa mínimo tem 20 ocorrências, 57 atributos e 66 dependências; é acíclico, logo existe uma ordem de avaliação (ordenação topológica), e a passagem única em profundidade respeita-a (0 violações).

# 3. Grafos dos programas (NB08)

## Ex1 universitário

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

Erros semânticos (verificador da Parte I): nenhum

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

## Ex2 secundário

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

Erros semânticos (verificador da Parte I): nenhum

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

## Ex7 análise

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

Erros semânticos (verificador da Parte I): nenhum

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
