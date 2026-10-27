# 1. Desenho da Linguagem

## 1.1. Domínio e Propósito da Linguagem

A linguagem desenvolvida neste projeto (denominada *StudyLang*) é uma Linguagem de Domínio Específico (DSL) desenhada para o planeamento, gestão e validação de planos de estudo.

O problema central que esta linguagem visa resolver é a dificuldade que muitos estudantes enfrentam na alocação eficiente do seu tempo disponível pelas diversas Unidades Curriculares (UCs) ou disciplinas. Frequentemente, os alunos precisam de equilibrar o peso académico (créditos ECTS, no ensino superior) e a dificuldade percecionada de cada matéria com um número limitado de horas de estudo. A *StudyLang* permite que o estudante declare o seu contexto (nível de ensino, UCs, tempo disponível) e escreva um plano de estudo, validando automaticamente se as restrições de tempo e as regras do seu nível de ensino são respeitadas.

## 1.2. Utilizadores e Contexto de Utilização

Os utilizadores alvo desta linguagem são estudantes, tanto do **ensino universitário** como do **ensino secundário**, que procurem uma forma estruturada e programática de organizar o seu calendário de estudo. O contexto de utilização pressupõe que o aluno conheça as UCs em que está inscrito, o grau de dificuldade percecionado de cada uma, e a sua disponibilidade temporal real para o estudo autónomo.

A distinção entre os dois níveis é parte do desenho da linguagem: no ensino universitário cada UC tem créditos ECTS (`CREDITS`), que influenciam o plano; no ensino secundário as disciplinas não têm créditos, pelo que a linguagem os proíbe. Cada programa declara o seu nível, e as regras semânticas adaptam-se a ele (secção 3).

## 1.3. Conceitos Principais e Abstrações

Para suportar o seu propósito, a linguagem baseia-se nas seguintes abstrações principais:

* **Estudante e nível (`STUDENT`, `LEVEL`):** todo o programa começa por identificar o estudante e o seu nível, `UNIVERSITY` ou `SECONDARY`. O nível determina que atributos das UCs são obrigatórios ou proibidos.
* **Unidades Curriculares (UC):** representam os blocos de conhecimento a estudar. Cada UC é identificada pelo seu nome (uma *string*) e tem o atributo `DIFFICULTY` (nível de exigência) e, no nível universitário, o atributo `CREDITS` (peso académico). Os atributos de uma UC são acedidos, dentro de um ciclo, através do iterador (por exemplo `u.CREDITS`).
* **Recursos (`RESOURCE`):** representam as restrições físicas do estudante, primariamente o tempo total disponível (`RESOURCE TIME n HOURS`).
* **Plano de Estudos (`PLAN` e `STUDY`):** o núcleo da linguagem, onde as horas de estudo são efetivamente alocadas às UCs declaradas.
* **Variáveis e âmbitos:** as variáveis (`VAR`) podem ser declaradas no âmbito global (antes do `PLAN`) ou localmente em qualquer bloco `{ ... }`. A linguagem adota **âmbito estático por bloco**: um nome é visível desde a sua declaração até ao fim do bloco onde foi declarado, incluindo blocos aninhados; blocos internos podem *sombrear* (*shadowing*) nomes de blocos exteriores, mas não é permitido redeclarar um nome no mesmo bloco. O iterador de um `FOR EACH` é local ao corpo do ciclo.
* **Controlo de fluxo:** `FOR EACH` (repetição sobre uma lista de UCs) e `IF ... ELSE IF ... ELSE` (ramificação), com condições compostas através de `AND`, `OR` e `NOT`, permitem gerar planos de estudo dinâmicos, adaptados às propriedades de cada UC (por exemplo, estudar mais horas se a dificuldade for elevada).
* **Validação:** programas sintaticamente corretos podem violar regras do domínio (UC não declarada, mais horas do que as disponíveis, créditos no ensino secundário, etc.). Essas regras não são verificáveis apenas pela sintaxe e são especificadas por uma gramática de atributos (secção 3).

### 1.3.1. Cobertura dos requisitos mínimos do enunciado

| Requisito do enunciado | Como é satisfeito na *StudyLang* |
|---|---|
| Variáveis e declarações | `VAR`, `UC`, `RESOURCE`; atribuição `x = expr` |
| Âmbitos e disciplina de âmbito definida | âmbito estático por bloco, com *shadowing* e proibição de redeclaração no mesmo bloco |
| Expressões e manipulação de valor/estado | expressões inteiras (`+ - * /`, parênteses, `-` unário), acesso a atributos `u.CREDITS`/`u.DIFFICULTY`, atribuição |
| Construções compostas e aninhadas | blocos dentro de `PLAN`, `IF` e `FOR EACH`, aninháveis arbitrariamente |
| Controlo de fluxo (ramificação e repetição) | `IF / ELSE IF / ELSE` e `FOR EACH` |
| Propriedades semânticas não decidíveis pela sintaxe | UC não declarada, variável fora de âmbito, `CREDITS` consoante o nível, limite de horas, tipos, divisão por zero (ver 3.1) |

## 1.4. Exemplos Representativos de Programas

Os cinco exemplos abaixo são os usados no verificador (`check_studylang.py`) e demonstram a sintaxe, a semântica e a separação entre erros sintáticos e semânticos.

### Exemplo 1: Programa universitário (válido)

Usa `FOR EACH` sobre três UCs, variável global e variável local ao ciclo, `IF / ELSE IF / ELSE`, condições com `AND`, `OR` e `NOT`, e os atributos `u.CREDITS` e `u.DIFFICULTY`.

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

### Exemplo 2: Programa secundário (válido)

As UCs só têm `DIFFICULTY`. Mostra uma variável global (`base`), uma local ao `PLAN` (`extra`), uma local ao corpo do ciclo (`h`) e o *shadowing* de `extra` num bloco interior.

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

### Exemplo 3: Programa secundário com 10 violações semânticas

O programa é sintaticamente válido, mas viola dez regras de domínio, assinaladas nos comentários. Serve de base para testar a gramática de atributos.

```study
STUDENT Ana LEVEL SECONDARY

UC "Matematica" { CREDITS 6 DIFFICULTY 4 }      // ERRO 1: CREDITS no secundario
UC "Matematica" { DIFFICULTY 2 }                // ERRO 2: UC repetida

RESOURCE TIME 5 HOURS

PLAN {
    STUDY "Matematica" FOR 10 HOURS             // ERRO 3: 10 > 5 horas disponiveis
    STUDY "Fisica" FOR 2 HOURS                  // ERRO 4: UC nao declarada
    total = 3                                   // ERRO 5: variavel nao declarada

    VAR x = 1
    VAR x = 2                                   // ERRO 6: redeclaracao no mesmo bloco

    IF ( x > 0 ) { VAR y = 4 }
    VAR z = y + 1                               // ERRO 7: y fora do ambito

    FOR EACH u IN [ "Matematica" ] {
        VAR w = u.CREDITS                       // ERRO 8: CREDITS no secundario
    }
    VAR w2 = x.DIFFICULTY                       // ERRO 9: x nao e uma UC
    VAR d = 10 / 0                              // ERRO 10: divisao por zero constante
}
```

### Exemplo 4: Programa universitário com violações de nível e de recursos

```study
STUDENT Rui LEVEL UNIVERSITY
UC "Redes" { DIFFICULTY 3 }                     // ERRO: falta CREDITS no universitario
RESOURCE TIME 10 HOURS
RESOURCE TIME 12 HOURS                          // ERRO: dois RESOURCE
PLAN { STUDY "Redes" FOR 0 HOURS }              // ERRO: horas nao positivas
```

### Exemplo 5: Programa sintaticamente inválido

Falta a declaração do nível (`LEVEL`). Este programa é rejeitado já pelo analisador sintático, antes de qualquer análise semântica, o que ilustra a separação entre erros sintáticos e semânticos.

```study
STUDENT Rui
UC "Redes" { CREDITS 3 DIFFICULTY 3 }
PLAN { }
```