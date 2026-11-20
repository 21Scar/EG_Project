# Como testar o projeto StudyLang

Este guia permite a qualquer pessoa instalar, correr e rever o projeto: a linguagem (Parte I) e a ferramenta com representações intermédias, análise estática e transformações (Parte II). Os passos vão do mais simples (correr comandos e ver resultados) ao mais aprofundado (ler o código).

Os comandos estão escritos para serem corridos **na pasta raiz do repositório**. Quando um comando difere entre sistemas, são indicadas as duas versões: Windows (PowerShell) e Linux/macOS.

---

## Passo 0: preparar o ambiente

É preciso **Python 3.10 ou superior**. Para instalar as dependências (`lark` e `networkx`):

```bash
pip install -r requirements.txt
```

O Graphviz **não é necessário**. Os grafos são desenhados no browser pelas páginas HTML que a ferramenta gera (é preciso ligação à internet para carregar a biblioteca de desenho). Se o Graphviz estiver instalado, os scripts geram também ficheiros SVG e PNG.

No Windows, se os acentos aparecerem estragados no terminal, corre antes:

```powershell
$env:PYTHONIOENCODING="utf-8"
```

---

## Passo 1: verificador da Parte I

```bash
python check_studylang.py
```

**Resultado esperado:**

| Exemplo | Resultado |
|---|---|
| Ex1 e Ex2 | `OK: sintaxe e semântica válidas` |
| Ex3 | 10 erros semânticos |
| Ex4 | 3 erros semânticos |
| Ex5 e Ex6 | erro sintático |

Os programas de exemplo estão em `exemplos/*.study` e podem ser abertos em qualquer editor de texto.

---

## Passo 2: a ferramenta `studylang.py`, comando a comando

Lista de comandos:

```bash
python studylang.py --help
```

### a) `verificar`: sintaxe e gramática de atributos

```bash
python studylang.py verificar exemplos/ex2_secundario.study
```

```bash
python studylang.py verificar exemplos/ex5_erro_sintatico.study
```

**O que observar:** o erro sintático indica o que era esperado (`esperado: LEVEL`) e aponta a coluna com `^`.

### b) `analisar`: análise estática

```bash
python studylang.py analisar exemplos/ex2_secundario.study
```

**O que observar:** a linha `Horas` compara três análises:

| Análise | Resultado |
|---|---|
| Gramática de atributos | `≥ 0` h |
| Intervalos | `[12, 27]` h |
| Avaliação exata | `21` h, e há só 20 disponíveis |

Por isso aparece o erro `HORAS`, que a verificação da Parte I não deteta.

```bash
python studylang.py analisar exemplos/ex7_analise.study
```

**O que observar:** aparecem os avisos `COND_CONST`, `INALCANCAVEL`, `DEF_MORTA` e `SEM_EFEITO`. Abre `exemplos/ex7_analise.study` e confirma, linha a linha, que cada aviso corresponde ao comentário escrito no programa.

Há mais duas formas de saída: `--md` dá o relatório completo, com as tabelas de *reaching definitions* e de *slicing*, e `--json` dá o resultado em JSON.

```bash
python studylang.py analisar exemplos/ex1_universitario.study --md
```

### c) `otimizar`: transformação que preserva o plano

```bash
python studylang.py otimizar exemplos/ex7_analise.study
```

**O que observar:**
- o programa passa de 11 para 3 instruções;
- o registo no fim (linhas `//`) explica cada alteração com a linha do ficheiro original;
- a mensagem `mesmo plano: sim` confirma que o significado foi preservado.

### d) `planificar`: desenrolar o plano

```bash
python studylang.py planificar exemplos/ex1_universitario.study
```

```bash
python studylang.py planificar exemplos/ex2_secundario.study --agregar
```

**O que observar:** o resultado só tem instruções `STUDY "UC" FOR n HOURS`. No Ex2, a última linha mostra que o verificador da Parte I passa a rejeitar o plano. Isto acontece porque, com todas as horas constantes, a propriedade P11 fica exata.

### e) `exportar`: plano efetivo noutro formato

```bash
python studylang.py exportar exemplos/ex1_universitario.study --formato csv
```

Os formatos disponíveis são `md`, `csv` e `json`.

### f) `relatorio`: página HTML com tudo

```bash
python studylang.py relatorio exemplos/ex7_analise.study
```

A página fica em `relatorio_ex7_analise/index.html`. Para a abrir:

```powershell
start relatorio_ex7_analise/index.html        # Windows
```

```bash
xdg-open relatorio_ex7_analise/index.html     # Linux  (macOS: open ...)
```

**O que observar:** o programa, os diagnósticos, a tabela das horas, o código otimizado e planificado lado a lado, e os grafos AST, CFG, DFG e PDG. Os relatórios dos três exemplos válidos já estão gerados na pasta `relatorios/`.

---

## Passo 3: todos os grafos (gramática, gramática de atributos e programas)

```bash
python grafos.py
```

Depois abre `grafos/index.html` no browser, da mesma forma que no passo 2 f).

São 25 grafos ao todo:
- o grafo de dependências da gramática;
- os grafos de dependências da gramática de atributos;
- para os exemplos Ex1, Ex2 e Ex7: AST, CFG, CFG por blocos básicos, DFG e PDG.

O ficheiro `grafos/analise.md` tem as tabelas e os números. A interpretação está em [fase_5_grafos_e_dependencias.md](fase_5_grafos_e_dependencias.md).

---

## Passo 4: testes automáticos

```bash
python -m unittest discover -s tests -v
```

**Resultado esperado:** 16 testes, todos `ok`, em poucos segundos.

Os testes da classe `TestPropriedades` correm sobre 150 programas válidos gerados aleatoriamente, com semente fixa para que os resultados sejam reprodutíveis. Verificam que:
- o *pretty-printer* é o inverso do parser;
- a otimização e a planificação preservam o significado do plano;
- a otimização é idempotente;
- as análises são sólidas, ou seja, as horas exatas ficam sempre dentro dos intervalos.

Para ver um dos programas gerados:

```bash
python -c "import sys; sys.path.insert(0,'tests'); import test_studylang as t; print(t.RANDOM[0])"
```

---

## Passo 5: experiências (a melhor forma de perceber a ferramenta)

Faz uma cópia do Ex2:

```powershell
copy exemplos\ex2_secundario.study teste.study      # Windows
```

```bash
cp exemplos/ex2_secundario.study teste.study        # Linux/macOS
```

Aplica **uma alteração de cada vez** ao `teste.study`. Depois de cada alteração, corre `python studylang.py analisar teste.study` e compara com o resultado esperado:

| # | Alteração | Resultado esperado |
|---|---|---|
| 1 | Mudar `RESOURCE TIME 20 HOURS` para `25` | O erro `HORAS` passa a uma nota `info`: os intervalos admitem até 27 h, mas o valor exato (21 h) cumpre o limite |
| 2 | No corpo do `FOR EACH`, antes de `VAR h = ...`, acrescentar `VAR k = 10 / (u.DIFFICULTY - 2)` | Erro `DIV_ZERO` "com u = Portugues", porque essa UC tem dificuldade 2. A gramática de atributos não o deteta, porque o divisor não é constante. Aparece também `DEF_MORTA` para `k`, que nunca é lido |
| 3 | Acrescentar a UC `UC "Ingles" { DIFFICULTY 1 }` sem a usar no plano | Aviso `UC_SEM_ESTUDO` |
| 4 | Antes de `extra = extra + 1`, acrescentar `IF ( base > 5 ) { STUDY "Fisica" FOR 3 HOURS }` | Avisos `COND_CONST` (a condição é sempre falsa) e `INALCANCAVEL` |

Na experiência 4 corre também `python studylang.py otimizar teste.study`. O registo deve mostrar `condição sempre falsa sem ELSE, o IF é removido` e terminar com `mesmo plano: sim`.

---

## Passo 6: ler o código

Recomenda-se esta ordem, porque cada ficheiro usa os anteriores. A arquitetura está descrita em [fase_7_ferramenta.md](fase_7_ferramenta.md).

| Ordem | Ficheiro | Papel | O que ler |
|---|---|---|---|
| 1 | [studylang.lark](studylang.lark) e [check_studylang.py](check_studylang.py) | Parte I: parser e gramática de atributos | as regras da gramática; `check`, `block`, `expr` |
| 2 | [ir.py](ir.py) | Representações intermédias | `resolve` (liga nomes a declarações, como o `env` da AG); `Program`; `build_cfg`; `basic_blocks`; `dataflow` e `reaching_definitions` (ponto fixo); `pdg` e `slices` |
| 3 | [analise.py](analise.py) | Análise estática | `Interp` (modos `exact`, `interval` e `nocond`); `analyse`; `diagnostics` |
| 4 | [transformacoes.py](transformacoes.py) | Transformações | `pretty`; `meaning` (definição de "mesmo significado"); `_fold_pass` e `_dce_pass` (os dois passos do otimizador); `optimize`; `flatten`; `export` |
| 5 | [grafos.py](grafos.py) | Visualização | conversão para DOT e página HTML; grafos da gramática e da AG |
| 6 | [studylang.py](studylang.py) | Interface | uma função `cmd_*` por comando, cada uma só chama os módulos anteriores |
| 7 | [tests/test_studylang.py](tests/test_studylang.py) | Testes | `Gen` (gerador de programas aleatórios) e `TestPropriedades` |

---

## Documentação relacionada

| Ficheiro | Conteúdo |
|---|---|
| [README.md](README.md) | Visão geral do projeto |
| [fase_1_desenho_da_linguagem.md](fase_1_desenho_da_linguagem.md) a [fase_4_qualidade.md](fase_4_qualidade.md) | Parte I: desenho, gramática, gramática de atributos e qualidade |
| [fase_5_grafos_e_dependencias.md](fase_5_grafos_e_dependencias.md) | Representações intermédias, análise estática e diagnósticos |
| [fase_6_transformacoes.md](fase_6_transformacoes.md) | Transformações e evidência de correção |
| [fase_7_ferramenta.md](fase_7_ferramenta.md) | Arquitetura, utilização e demonstração |
