# 1. Desenho da Linguagem

## 1.1. Domínio e Propósito da Linguagem

A linguagem desenvolvida neste projeto (denominada provisoriamente de *StudyLang*) é uma Linguagem de Domínio Específico (DSL) desenhada para o planeamento, gestão e otimização de sessões de estudo.

O problema central que esta linguagem visa resolver é a dificuldade que muitos estudantes enfrentam na alocação eficiente do seu tempo disponível pelas diversas Unidades Curriculares (UCs) ou disciplinas. Frequentemente, os alunos precisam de equilibrar o peso académico (créditos ECTS) e a dificuldade inerente de cada matéria com um número limitado de horas de estudo. A *StudyLang* permite que o estudante declare as variáveis do seu semestre e defina um plano de estudo, validando automaticamente se as restrições de tempo e os pré-requisitos são respeitados.

## 1.2. Utilizadores e Contexto de Utilização

Os utilizadores alvo desta linguagem são estudantes (tanto de nível universitário como do ensino secundário) que procurem uma forma estruturada e programática de organizar o seu calendário de revisões. O contexto de utilização pressupõe que o aluno conheça o seu plano de estudos (UCs matriculadas), o grau de dificuldade percecionado de cada uma, e a sua disponibilidade temporal real para o estudo autónomo.

## 1.3. Conceitos Principais e Abstrações

Para suportar o seu propósito, a linguagem baseia-se nas seguintes abstrações principais:

* **Unidades Curriculares (UC):** Representam os blocos de conhecimento a estudar. Cada UC encapsula atributos como `CREDITS` (peso académico) e `DIFFICULTY` (nível de exigência). Os atributos de uma UC são acedidos através de um iterador, por exemplo `u.CREDITS`.
* **Recursos (RESOURCE):** Representam as restrições físicas do estudante, primariamente o tempo disponível (`TIME`).
* **Plano de Estudos (PLAN e STUDY):** O núcleo da linguagem, onde as horas de estudo são efetivamente alocadas às UCs declaradas.
* **Variáveis e Âmbitos:** As variáveis (`VAR`) podem ser declaradas no âmbito global (antes do `PLAN`) ou localmente em qualquer bloco `{ ... }` do plano. A linguagem adota **âmbito estático por bloco**: um nome é visível desde a sua declaração até ao fim do bloco onde foi declarado, incluindo blocos aninhados; blocos internos podem *sombrear* (shadowing) nomes de blocos exteriores, mas não é permitido redeclarar um nome no mesmo bloco. O iterador de um `FOR EACH` é local ao corpo do ciclo.
* **Controlo de Fluxo:** Utilização de estruturas como `FOR EACH` e `IF-ELSE` (incluindo `ELSE IF` e condições compostas com `AND`, `OR` e `NOT`) para permitir a geração de planos de estudo dinâmicos e adaptáveis com base nas propriedades de cada UC (ex: estudar mais horas se a dificuldade for elevada).

## 1.4. Exemplos Representativos de Programas

Abaixo apresentam-se três exemplos que demonstram a sintaxe e a semântica da linguagem.

### Exemplo 1: Programa Simples (Linear)

Este exemplo ilustra a declaração básica de entidades e um plano de estudos direto.

```study
STUDENT Leonor

// Declaracao de UCs e os seus atributos
UC "Sistemas Distribuidos" {
    CREDITS 6
    DIFFICULTY 4
}

UC "Engenharia Gramatical" {
    CREDITS 6
    DIFFICULTY 5
}

// Definicao do tempo total disponivel
RESOURCE TIME 20 HOURS

// Alocacao de tempo de estudo
PLAN {
    STUDY "Sistemas Distribuidos" FOR 8 HOURS
    STUDY "Engenharia Gramatical" FOR 10 HOURS
}
```

### Exemplo 2: Programa Avançado (Com Controlo de Fluxo e Âmbitos)

Este exemplo demonstra variáveis globais e locais, iteração sobre conjuntos de UCs, acesso a atributos de UC através do iterador e ramificação condicional (incluindo `ELSE IF` e condições compostas) para um planeamento dinâmico.

```study
STUDENT Joao

UC "Engenharia" { CREDITS 6 DIFFICULTY 3 }
UC "Fisica"     { CREDITS 6 DIFFICULTY 5 }

RESOURCE TIME 30 HOURS

VAR max_session_hours = 4          // variavel global

PLAN {
    // Iteracao pelas UCs declaradas; "u" so existe dentro do ciclo
    FOR EACH u IN [ "Engenharia", "Fisica" ] {

        VAR h = u.CREDITS * 2      // variavel local ao corpo do ciclo

        // Alocacao dinamica baseada nos atributos da UC
        IF ( u.DIFFICULTY > 3 AND h <= max_session_hours * 3 ) {
            STUDY u FOR h HOURS
        } ELSE IF ( u.DIFFICULTY == 3 ) {
            STUDY u FOR max_session_hours HOURS
        } ELSE {
            STUDY u FOR 2 HOURS
        }
    }
}
```

### Exemplo 3: Programa com Violações Semânticas

O código abaixo é sintaticamente válido, mas falha nas regras de semântica de domínio. Servirá de base para a implementação da gramática de atributos.

```study
STUDENT Ana

UC "Matematica" { CREDITS 6 DIFFICULTY 4 }
UC "Matematica" { CREDITS 5 DIFFICULTY 2 }   // ERRO 1: UC declarada duas vezes

RESOURCE TIME 5 HOURS

PLAN {
    // ERRO 2: aloca 10 horas quando apenas 5 estao disponiveis.
    STUDY "Matematica" FOR 10 HOURS

    // ERRO 3: UC "Fisica" nao foi declarada.
    STUDY "Fisica" FOR 2 HOURS

    // ERRO 4: variavel "total" usada sem declaracao.
    total = 3

    VAR x = 1
    VAR x = 2                                  // ERRO 5: redeclaracao de "x" no mesmo bloco

    IF ( x > 0 ) {
        VAR y = 4
    }
    VAR z = y + 1                              // ERRO 6: "y" fora do seu ambito

    VAR w = x.CREDITS                          // ERRO 7: "x" nao e uma UC, nao tem CREDITS

    VAR d = 10 / 0                             // ERRO 8: divisao por zero constante
}
```
