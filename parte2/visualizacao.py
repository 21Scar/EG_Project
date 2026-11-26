"""
Grafos de dependências e análise estática da StudyLang (NB07 + NB08).

Gera, na pasta resultados/grafos/:
  * gramática (NB07): grafo de dependências entre não-terminais (recursividade, SCCs);
  * gramática de atributos (NB07): grafos de dependências locais de cada produção,
    grafo global de atributos (métricas de grau) e grafo instanciado numa árvore
    (prova de não-circularidade e de avaliação L-atribuída numa só passagem);
  * programas (NB08): AST anotada, CFG (instruções e blocos básicos), DFG
    (reaching definitions), PDG (dependências de dados + controlo) com slicing;
  * análise estática das horas: AG (minHours), intervalos e avaliação exata.

As representações e as análises estão em representacoes_intermedias.py e
analise_estatica.py; este módulo só as desenha. Os grafos são escritos em DOT. Se o Graphviz (`dot`) estiver instalado,
são também convertidos em SVG e PNG. O ficheiro resultados/grafos/index.html mostra todos os
grafos no browser, sem precisar de Graphviz.

Uso: python studylang.py grafos-todos      (ou: python -m parte2.visualizacao)
     (para um só programa: python studylang.py grafos FICHEIRO)
"""
import html
import json
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

import networkx as nx
from lark import Token, Tree

from parte1 import verificador as cs
from parte2 import analise_estatica as analise
from parte2 import representacoes_intermedias as ir
from parte2.representacoes_intermedias import OPS, src

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent      # raiz do projeto
OUT = ROOT / "resultados" / "grafos"
EXEMPLOS = ROOT / "exemplos"
INF = float("inf")

# Paleta (cores claras para preenchimento)
C_INH, C_SYN, C_LEX = "#d8f0d2", "#fde2c4", "#e6e6e6"
C_STMT, C_EXPR, C_COND, C_LOOP = "#dbe9f7", "#fff6c9", "#f9d9d9", "#e6dcf5"
C_DEAD, C_SLICE = "#eeeeee", "#c8ecd0"


# ==========================================================================
# 0. Utilitários: escrita de DOT e impressão de expressões
# ==========================================================================
def q(s):
    s = str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{s}"'


DOT_KEYS = {"label", "shape", "style", "fillcolor", "color", "penwidth", "fontcolor",
            "constraint", "arrowhead", "dir", "fontsize", "xlabel", "weight", "peripheries",
            "lhead", "ltail", "minlen"}


def _attrs(d):
    a = {k: v for k, v in d.items() if k in DOT_KEYS}
    return (" [" + ", ".join(f"{k}={q(v)}" for k, v in a.items()) + "]") if a else ""


def to_dot(G, name, rankdir="TB", extra=""):
    """Converte um nx.DiGraph em DOT. G.graph['clusters'] = {id: {label, nodes}}."""
    out = [f"digraph {q(name)} {{", f"  rankdir={rankdir};", "  compound=true;",
           '  node [fontname="Helvetica", fontsize=11, style=filled, fillcolor="white"];',
           '  edge [fontname="Helvetica", fontsize=9];']
    if extra:
        out.append("  " + extra)
    clusters = G.graph.get("clusters", {})
    in_cluster = set()
    for i, (cid, c) in enumerate(clusters.items()):
        out.append(f"  subgraph cluster_{i} {{")
        out.append(f"    label={q(c.get('label', ''))}; style=\"rounded\"; color=\"#999999\";")
        for n in c["nodes"]:
            out.append(f"    {q(n)}{_attrs(G.nodes[n])};")
            in_cluster.add(n)
        out.append("  }")
    for n, d in G.nodes(data=True):
        if n not in in_cluster:
            out.append(f"  {q(n)}{_attrs(d)};")
    for u, v, d in G.edges(data=True):
        out.append(f"  {q(u)} -> {q(v)}{_attrs(d)};")
    out.append("}")
    return "\n".join(out)


GRAPHS = []   # (ficheiro, secção, título, descrição, dot); escritos por write_graphs()


def save(fname, section, title, desc, dot):
    GRAPHS.append((fname, section, title, desc, dot))



# ==========================================================================
# 1. Grafo de dependências da gramática (NB07)
# ==========================================================================
def grammar_dependency_graph(report):
    rules = cs.parser.rules
    G = nx.DiGraph()
    prods = defaultdict(list)
    for r in rules:
        a = r.origin.name
        G.add_node(a)
        prods[a].append(r)
        for s in r.expansion:
            if not s.is_term:
                G.add_edge(a, s.name)
    nts = list(G.nodes)

    # recursividade: componentes fortemente ligadas
    sccs = [c for c in nx.strongly_connected_components(G)
            if len(c) > 1 or any(G.has_edge(n, n) for n in c)]
    direct = sorted(n for n in nts if G.has_edge(n, n))
    indirect = [sorted(c) for c in sccs if len(c) > 1]

    # símbolos acessíveis e produtivos (sem símbolos inúteis)
    reach = nx.descendants(G, "start") | {"start"}
    productive, changed = set(), True
    while changed:
        changed = False
        for a, rs in prods.items():
            if a not in productive and any(all(s.is_term or s.name in productive for s in r.expansion) for r in rs):
                productive.add(a)
                changed = True

    # profundidade: caminho mais longo no grafo condensado (DAG das SCCs)
    cond = nx.condensation(G)
    depth = nx.dag_longest_path_length(cond)

    palette = ["#fbd5d5", "#d5e8fb", "#d9f5d3", "#f7e7c4", "#e8d9f7", "#d2f1f1"]
    color = {}
    for i, c in enumerate(sorted(sccs, key=lambda c: -len(c))):
        for n in c:
            color[n] = palette[i % len(palette)]
    for n in nts:
        aux = n.startswith("__")
        G.nodes[n].update(label=("(aux) " + n) if aux else n, shape="box",
                          style="filled,dashed" if aux else "filled",
                          fillcolor=color.get(n, "white"))
    for u, v in G.edges:
        if u == v:
            G.edges[u, v]["color"] = "#c0392b"
    save("gramatica_dependencias", "Gramática (NB07)",
         "Grafo de dependências entre não-terminais",
         "Aresta A → B: B aparece no lado direito de uma produção de A (gramática compilada pelo Lark, "
         "como em parte1/metricas_gramatica.py). Cores = componentes fortemente ligadas (recursividade); "
         "laços vermelhos = recursividade direta; caixas a tracejado = regras auxiliares geradas pelo Lark.",
         to_dot(G, "gramatica", "LR"))

    indeg = Counter(v for _, v in G.edges)
    outdeg = Counter(u for u, _ in G.edges)
    r = report
    r.append("## 1. Grafo de dependências da gramática\n")
    r.append(f"- Não-terminais: {len(nts)}; arestas distintas: {G.number_of_edges()}")
    r.append(f"- Grau médio de entrada/saída: {sum(indeg[n] for n in nts)/len(nts):.2f} / "
             f"{sum(outdeg[n] for n in nts)/len(nts):.2f}")
    top_in = sorted(nts, key=lambda n: -indeg[n])[:5]
    r.append("- Maior grau de entrada (símbolos mais reutilizados): " +
             ", ".join(f"`{n}` ({indeg[n]})" for n in top_in))
    r.append(f"- Recursividade direta ({len(direct)}): " + ", ".join(f"`{n}`" for n in direct))
    r.append(f"- Recursividade indireta ({len(indirect)} ciclos):")
    for c in indirect:
        r.append("  - {" + ", ".join(f"`{n}`" for n in c) + "}")
    r.append(f"- Símbolos inacessíveis a partir de `start`: {sorted(set(nts) - reach) or 'nenhum'}")
    r.append(f"- Símbolos improdutivos: {sorted(set(nts) - productive) or 'nenhum'}")
    r.append(f"- Profundidade do grafo condensado (níveis de SCCs a partir de `start`): {depth}\n")


# ==========================================================================
# 2. Gramática de atributos: grafos de dependências (NB07)
# ==========================================================================
INHERITED = {"env_in", "env", "nres_in", "limit_in"}
LEXICAL = {"kind", "val", "name", "present"}
TERMINALS = {"ID", "STRING", "INT", "level", "credits", "attr_name"}


def attr_kind(sym, attr):
    if sym in TERMINALS or attr in LEXICAL and sym in TERMINALS:
        return "lex"
    return "inh" if attr in INHERITED else "syn"


class AG:
    """Ocorrências de símbolos e dependências entre os seus atributos."""

    def __init__(self):
        self.G = nx.DiGraph()
        self.sym, self.label, self.parent, self.pos, self.children = {}, {}, {}, {}, defaultdict(list)
        self.prod_of = {}
        self.k = 0

    def occ(self, sym, label=None):
        self.k += 1
        o = f"o{self.k}"
        self.sym[o], self.label[o] = sym, label or sym
        return o

    def kids(self, L, ks, prod):
        self.prod_of[L] = prod
        for i, k in enumerate(ks):
            if k is not None:
                self.parent[k], self.pos[k] = L, i
                self.children[L].append(k)

    def dep(self, so, sa, do, da):
        self.G.add_edge((so, sa), (do, da))


# ---- regras semânticas (uma função por produção; espelham a secção 3.4) ----
def P_start(g, L, level, decls, plan):
    g.kids(L, [level] + decls + [plan], "start → STUDENT ID LEVEL level decl* plan")
    prev = None
    for d in decls:
        if prev is None:
            g.dep(level, "kind", d, "env_in")                # env_0 = emptyEnv(level.kind)
        else:
            for a, b in (("env_out", "env_in"), ("nres_out", "nres_in"), ("limit_out", "limit_in")):
                g.dep(prev, a, d, b)
        g.dep(d, "errors", L, "errors")
        prev = d
    if prev is None:
        g.dep(level, "kind", plan, "env_in")
    else:
        g.dep(prev, "env_out", plan, "env_in")
        g.dep(prev, "nres_out", L, "errors")                 # P11
        g.dep(prev, "limit_out", L, "errors")
    g.dep(plan, "errors", L, "errors")
    g.dep(plan, "minHours", L, "errors")


def P_decl(g, L, X, kind):
    g.kids(L, [X], f"decl → {kind}")
    g.dep(L, "env_in", X, "env_in")
    g.dep(X, "env_out", L, "env_out")
    g.dep(X, "errors", L, "errors")
    if kind == "resource_decl":
        g.dep(L, "nres_in", X, "nres_in")
        g.dep(L, "limit_in", X, "limit_in")
        g.dep(X, "nres_out", L, "nres_out")
        g.dep(X, "limit_out", L, "limit_out")
    else:
        g.dep(L, "nres_in", L, "nres_out")
        g.dep(L, "limit_in", L, "limit_out")


def P_uc(g, L, STRING, credits):
    g.kids(L, [STRING, credits], "uc_decl → UC STRING { credits? difficulty }")
    g.dep(L, "env_in", L, "errors")                          # P1 (lookup) e P3 (level)
    g.dep(STRING, "name", L, "errors")
    if credits is not None:
        g.dep(credits, "present", L, "errors")
    g.dep(L, "env_in", L, "env_out")
    g.dep(STRING, "name", L, "env_out")


def P_res(g, L, INT):
    g.kids(L, [INT], "resource_decl → RESOURCE TIME INT HOURS")
    g.dep(L, "env_in", L, "env_out")
    g.dep(L, "nres_in", L, "nres_out")
    g.dep(L, "nres_in", L, "limit_out")
    g.dep(L, "limit_in", L, "limit_out")
    g.dep(INT, "val", L, "limit_out")
    g.dep(L, "nres_in", L, "errors")                         # P2


def P_var(g, L, ID, E):
    g.kids(L, [ID, E], "var_decl → VAR ID = expr")
    g.dep(L, "env_in", E, "env")
    g.dep(E, "errors", L, "errors")
    g.dep(E, "type", L, "errors")                            # P8
    g.dep(L, "env_in", L, "errors")                          # P6 inCurrent
    g.dep(ID, "name", L, "errors")
    g.dep(L, "env_in", L, "env_out")
    g.dep(ID, "name", L, "env_out")


def P_plan(g, L, B):
    g.kids(L, [B], "plan → PLAN block")
    g.dep(L, "env_in", B, "env_in")
    g.dep(B, "errors", L, "errors")
    g.dep(B, "minHours", L, "minHours")


def P_block(g, L, stmts):
    g.kids(L, stmts, "block → { stmt* }")
    prev = None
    for s in stmts:
        if prev is None:
            g.dep(L, "env_in", s, "env_in")                  # enter(block.env_in)
        else:
            g.dep(prev, "env_out", s, "env_in")
        g.dep(s, "errors", L, "errors")
        g.dep(s, "minHours", L, "minHours")
        prev = s


def P_stmt(g, L, X, kind):
    g.kids(L, [X], f"stmt → {kind}")
    g.dep(L, "env_in", X, "env_in")
    g.dep(X, "errors", L, "errors")
    if kind == "var_decl":
        g.dep(X, "env_out", L, "env_out")
    else:
        g.dep(L, "env_in", L, "env_out")
        g.dep(X, "minHours", L, "minHours")


def P_assign(g, L, ID, E):
    g.kids(L, [ID, E], "assign_stmt → ID = expr")
    g.dep(L, "env_in", E, "env")
    for a in ("errors", "type"):
        g.dep(E, a, L, "errors")
    g.dep(L, "env_in", L, "errors")                          # P5
    g.dep(ID, "name", L, "errors")


def P_study(g, L, T, E, is_id):
    g.kids(L, [T, E], f"study_stmt → STUDY {'ID' if is_id else 'STRING'} FOR expr HOURS")
    g.dep(L, "env_in", E, "env")
    for a in ("errors", "type", "const", "val"):
        g.dep(E, a, L, "errors")                             # P8, P10
    g.dep(L, "env_in", L, "errors")                          # P4
    g.dep(T, "name", L, "errors")
    g.dep(E, "const", L, "minHours")
    g.dep(E, "val", L, "minHours")


def P_if(g, L, C, B, EL):
    g.kids(L, [C, B, EL], "if_stmt → IF ( cond ) block else_part?")
    g.dep(L, "env_in", C, "env")
    g.dep(L, "env_in", B, "env_in")
    g.dep(C, "errors", L, "errors")
    g.dep(B, "errors", L, "errors")
    g.dep(B, "minHours", L, "minHours")
    if EL is not None:
        g.dep(L, "env_in", EL, "env_in")
        g.dep(EL, "errors", L, "errors")
        g.dep(EL, "minHours", L, "minHours")


def P_else(g, L, X, kind):
    g.kids(L, [X], f"else_part → ELSE {kind}")
    g.dep(L, "env_in", X, "env_in")
    g.dep(X, "errors", L, "errors")
    g.dep(X, "minHours", L, "minHours")


def P_foreach(g, L, ID, SL, B):
    g.kids(L, [ID, SL, B], "foreach_stmt → FOR EACH ID IN [ string_list ] block")
    g.dep(L, "env_in", SL, "env")
    g.dep(L, "env_in", B, "env_in")                          # add(enter(env_in), id:ID, iter)
    g.dep(ID, "name", B, "env_in")
    g.dep(SL, "errors", L, "errors")
    g.dep(B, "errors", L, "errors")
    g.dep(SL, "count", L, "minHours")
    g.dep(B, "minHours", L, "minHours")


def P_slist(g, L, strings):
    g.kids(L, strings, "string_list → STRING (, STRING)*")
    g.dep(L, "env", L, "errors")                             # P4
    for s in strings:
        g.dep(s, "name", L, "errors")
        g.dep(s, "name", L, "count")


def P_num(g, L, INT):
    g.kids(L, [INT], "expr → INT")
    g.dep(INT, "val", L, "val")


def P_ref(g, L, ID):
    g.kids(L, [ID], "expr → ID")
    for a in ("type", "errors"):
        g.dep(L, "env", L, a)
        g.dep(ID, "name", L, a)


def P_attr(g, L, ID, A):
    g.kids(L, [ID, A], "expr → ID . attr_name")
    for a in ("errors", "type"):
        g.dep(L, "env", L, a)                                # P7, P3
        g.dep(ID, "name", L, a)
        g.dep(A, "kind", L, a)


def P_neg(g, L, E):
    g.kids(L, [E], "expr → - expr")
    g.dep(L, "env", E, "env")
    for a in ("type", "const", "val", "errors"):
        g.dep(E, a, L, a)


def P_bin(g, L, E1, E2, op):
    g.kids(L, [E1, E2], f"expr → expr {op} expr")
    for e in (E1, E2):
        g.dep(L, "env", e, "env")
        for a in ("type", "const", "val", "errors"):
            g.dep(e, a, L, a)
        g.dep(e, "const", L, "val")
    if op == "/":                                            # P9 e const depende de val ≠ 0
        g.dep(E2, "const", L, "errors")
        g.dep(E2, "val", L, "errors")
        g.dep(E2, "val", L, "const")


def P_cmp(g, L, E1, E2):
    g.kids(L, [E1, E2], "cond → expr REL_OP expr")
    for e in (E1, E2):
        g.dep(L, "env", e, "env")
        g.dep(e, "errors", L, "errors")
        g.dep(e, "type", L, "errors")                        # P8


def P_logic(g, L, C1, C2, op):
    g.kids(L, [C1, C2], f"cond → cond {op} cond")
    for c in (C1, C2):
        g.dep(L, "env", c, "env")
        g.dep(c, "errors", L, "errors")


def P_not(g, L, C):
    g.kids(L, [C], "cond → NOT cond")
    g.dep(L, "env", C, "env")
    g.dep(C, "errors", L, "errors")


# ---- produções em forma "local" (uma ocorrência por símbolo da produção) ----
def local_productions():
    """Devolve [(título, AG)] com o grafo local de cada produção."""
    res = []

    def mk(builder):
        g = AG()
        builder(g)
        res.append(g)
        return g

    mk(lambda g: P_start(g, g.occ("start"), g.occ("level"),
                         [g.occ("decl", "decl₁"), g.occ("decl", "decl₂")], g.occ("plan")))
    for k in ("uc_decl", "resource_decl", "var_decl"):
        mk(lambda g, k=k: P_decl(g, g.occ("decl"), g.occ(k), k))
    mk(lambda g: P_uc(g, g.occ("uc_decl"), g.occ("STRING"), g.occ("credits")))
    mk(lambda g: P_res(g, g.occ("resource_decl"), g.occ("INT")))
    mk(lambda g: P_var(g, g.occ("var_decl"), g.occ("ID"), g.occ("expr")))
    mk(lambda g: P_plan(g, g.occ("plan"), g.occ("block")))
    mk(lambda g: P_block(g, g.occ("block"), [g.occ("stmt", "stmt₁"), g.occ("stmt", "stmt₂")]))
    for k in ("var_decl", "assign_stmt", "study_stmt", "if_stmt", "foreach_stmt"):
        mk(lambda g, k=k: P_stmt(g, g.occ("stmt"), g.occ(k), k))
    mk(lambda g: P_assign(g, g.occ("assign_stmt"), g.occ("ID"), g.occ("expr")))
    mk(lambda g: P_study(g, g.occ("study_stmt"), g.occ("STRING"), g.occ("expr"), False))
    mk(lambda g: P_study(g, g.occ("study_stmt"), g.occ("ID"), g.occ("expr"), True))
    mk(lambda g: P_if(g, g.occ("if_stmt"), g.occ("cond"), g.occ("block"), g.occ("else_part")))
    mk(lambda g: P_else(g, g.occ("else_part"), g.occ("if_stmt"), "if_stmt"))
    mk(lambda g: P_else(g, g.occ("else_part"), g.occ("block"), "block"))
    mk(lambda g: P_foreach(g, g.occ("foreach_stmt"), g.occ("ID"), g.occ("string_list"), g.occ("block")))
    mk(lambda g: P_slist(g, g.occ("string_list"), [g.occ("STRING", "STRING₁"), g.occ("STRING", "STRING₂")]))
    mk(lambda g: P_num(g, g.occ("expr"), g.occ("INT")))
    mk(lambda g: P_ref(g, g.occ("expr"), g.occ("ID")))
    mk(lambda g: P_attr(g, g.occ("expr"), g.occ("ID"), g.occ("attr_name")))
    mk(lambda g: P_neg(g, g.occ("expr"), g.occ("expr", "expr₁")))
    for op in ("+", "/"):
        mk(lambda g, op=op: P_bin(g, g.occ("expr"), g.occ("expr", "expr₁"), g.occ("expr", "expr₂"), op))
    mk(lambda g: P_cmp(g, g.occ("cond"), g.occ("expr", "expr₁"), g.occ("expr", "expr₂")))
    mk(lambda g: P_logic(g, g.occ("cond"), g.occ("cond", "cond₁"), g.occ("cond", "cond₂"), "AND"))
    mk(lambda g: P_not(g, g.occ("cond"), g.occ("cond", "cond₁")))
    return res


def check_l_attributed(g):
    """Verifica, aresta a aresta, as condições de uma AG L-atribuída e bem definida."""
    problems = []
    for (so, sa), (do, da) in g.G.edges:
        dk = attr_kind(g.sym[do], da)
        if dk == "inh":
            # herdado de X_j: só do herdado do pai ou de atributos de irmãos à esquerda
            p = g.parent.get(do)
            if not ((so == p and attr_kind(g.sym[so], sa) == "inh") or
                    (g.parent.get(so) == p and p is not None and g.pos[so] < g.pos[do])):
                problems.append(f"{g.label[so]}.{sa} → {g.label[do]}.{da}")
        elif dk == "syn":
            # sintetizado de A: só de atributos de A ou dos seus filhos
            if not (so == do or g.parent.get(so) == do):
                problems.append(f"{g.label[so]}.{sa} → {g.label[do]}.{da}")
        else:
            problems.append(f"atributo léxico definido por regra: {g.label[do]}.{da}")
    return problems


def ag_graph_to_nx(g, title=None, tree_edges=False):
    """Desenha um grafo de atributos com um cluster por ocorrência."""
    H = nx.DiGraph()
    clusters = {}
    for o in g.sym:
        attrs = sorted({a for (oo, a) in g.G.nodes if oo == o})
        if not attrs:
            continue
        head = f"{o}#"
        H.add_node(head, label=g.label[o], shape="plaintext", style="", fontsize="12")
        nodes = [head]
        for a in attrs:
            k = attr_kind(g.sym[o], a)
            n = f"{o}.{a}"
            H.add_node(n, label=a, shape="ellipse",
                       fillcolor={"inh": C_INH, "syn": C_SYN, "lex": C_LEX}[k], fontsize="10")
            nodes.append(n)
        clusters[o] = {"label": "", "nodes": nodes}
    H.graph["clusters"] = clusters
    for (so, sa), (do, da) in g.G.edges:
        # a posição dos nós é dada pela árvore; as dependências não alteram o layout
        H.add_edge(f"{so}.{sa}", f"{do}.{da}", constraint="false")
    for c, p in g.parent.items():
        if f"{c}#" in H and f"{p}#" in H:
            H.add_edge(f"{p}#", f"{c}#", style="invis" if not tree_edges else "dotted",
                       color="#aaaaaa", arrowhead="none", weight="5",
                       ltail=f"cluster_{list(clusters).index(p)}",
                       lhead=f"cluster_{list(clusters).index(c)}")
    return H


def ag_instance(tree):
    """Instancia as regras da AG numa árvore concreta (grafo de dependências da árvore)."""
    g = AG()

    def tok(t, sym):
        o = g.occ(sym, f"{sym} {t}")
        return o

    def ex(n):
        L = g.occ("expr", f"expr  {src(n)}")
        d = n.data
        if d == "num":
            P_num(g, L, tok(n.children[0], "INT"))
        elif d == "var":
            P_ref(g, L, tok(n.children[0], "ID"))
        elif d == "attr":
            P_attr(g, L, tok(n.children[0], "ID"), g.occ("attr_name", str(n.children[1].children[0])))
        elif d == "neg":
            P_neg(g, L, ex(n.children[0]))
        else:
            P_bin(g, L, ex(n.children[0]), ex(n.children[1]), OPS[d])
        return L

    def cn(n):
        L = g.occ("cond", f"cond  {src(n)}")
        d = n.data
        if d == "compare":
            P_cmp(g, L, ex(n.children[0]), ex(n.children[2]))
        elif d == "not_":
            P_not(g, L, cn(n.children[0]))
        else:
            P_logic(g, L, cn(n.children[0]), cn(n.children[1]), "AND" if d == "and_" else "OR")
        return L

    def vd(n):
        L = g.occ("var_decl", f"var_decl {n.children[0]}")
        P_var(g, L, tok(n.children[0], "ID"), ex(n.children[1]))
        return L

    def blk(b):
        L = g.occ("block")
        P_block(g, L, [st(s) for s in b.children])
        return L

    def ifs(n):
        L = g.occ("if_stmt")
        c, b = cn(n.children[0]), blk(n.children[1])
        el = None
        if len(n.children) == 3:
            p = n.children[2].children[0]
            el = g.occ("else_part")
            if p.data == "if_stmt":
                P_else(g, el, ifs(p), "if_stmt")
            else:
                P_else(g, el, blk(p), "block")
        P_if(g, L, c, b, el)
        return L

    def st(n):
        L = g.occ("stmt")
        d = n.data
        if d == "var_decl":
            X = vd(n)
        elif d == "assign_stmt":
            X = g.occ("assign_stmt", f"assign {n.children[0]}")
            P_assign(g, X, tok(n.children[0], "ID"), ex(n.children[1]))
        elif d == "study_stmt":
            t = n.children[0]
            X = g.occ("study_stmt")
            P_study(g, X, tok(t, t.type), ex(n.children[1]), t.type == "ID")
        elif d == "if_stmt":
            X = ifs(n)
        else:
            it, lst, b = n.children
            X = g.occ("foreach_stmt")
            sl = g.occ("string_list")
            P_slist(g, sl, [tok(s, "STRING") for s in lst.children])
            P_foreach(g, X, tok(it, "ID"), sl, blk(b))
        P_stmt(g, L, X, d)
        return L

    root = g.occ("start")
    _name, level, *rest = tree.children
    lv = g.occ("level", f"level {level.data.upper()}")
    decls = []
    for d in rest[:-1]:
        D = g.occ("decl")
        if d.data == "uc_decl":
            X = g.occ("uc_decl", f"uc_decl {d.children[0]}")
            cr = next((c for c in d.children[1:] if isinstance(c, Tree) and c.data == "credits"), None)
            P_uc(g, X, tok(d.children[0], "STRING"), g.occ("credits") if cr is not None else None)
        elif d.data == "resource_decl":
            X = g.occ("resource_decl")
            P_res(g, X, tok(d.children[0], "INT"))
        else:
            X = vd(d)
        P_decl(g, D, X, d.data)
        decls.append(D)
    pl = g.occ("plan")
    P_plan(g, pl, blk(rest[-1].children[0]))
    P_start(g, root, lv, decls, pl)
    return g, root


def single_pass_order(g, root):
    """Ordem de uma passagem em profundidade, da esquerda para a direita:
    herdados ao entrar num nó, sintetizados ao sair. Devolve as arestas violadas."""
    t, time = [0], {}

    def visit(o):
        for (oo, a) in g.G.nodes:
            if oo == o and attr_kind(g.sym[o], a) in ("inh", "lex"):
                t[0] += 1
                time[(oo, a)] = t[0]
        for c in g.children[o]:
            visit(c)
        for (oo, a) in g.G.nodes:
            if oo == o and attr_kind(g.sym[o], a) == "syn":
                t[0] += 1
                time[(oo, a)] = t[0]

    visit(root)
    return [(u, v) for u, v in g.G.edges if time[u] >= time[v]]


def attribute_grammar_graphs(report, programs):
    r = report
    locs = local_productions()

    # (a) grafo global, união dos grafos locais com nós "símbolo.atributo" (como no NB07)
    Gg = nx.DiGraph()
    rules_count = 0
    for g in locs:
        lab = {o: g.label[o] for o in g.sym}
        defined = set()
        for (so, sa), (do, da) in g.G.edges:
            Gg.add_edge(f"{lab[so]}.{sa}", f"{lab[do]}.{da}")
            defined.add((do, da))
        rules_count += len(defined)
    nodes = list(Gg.nodes)
    indeg = Counter(v for _, v in Gg.edges)
    outdeg = Counter(u for u, _ in Gg.edges)
    for n in nodes:
        sym, a = n.rsplit(".", 1)
        base = sym.rstrip("₁₂")
        k = attr_kind(base, a)
        Gg.nodes[n].update(label=n, shape="ellipse",
                           fillcolor={"inh": C_INH, "syn": C_SYN, "lex": C_LEX}[k])
    save("ag_global", "Gramática de atributos (NB07)",
         "Grafo global de dependências de atributos",
         "União dos grafos locais de todas as produções; cada nó é símbolo.atributo "
         "(verde = herdado, laranja = sintetizado, cinzento = léxico). É sobre este grafo que se "
         "calculam as métricas de dependência de atributos do NB07.",
         to_dot(Gg, "ag_global", "LR"))

    # (b) grafos locais de produções escolhidas
    chosen = {"start → STUDENT ID LEVEL level decl* plan": "ag_local_start",
              "block → { stmt* }": "ag_local_block",
              "foreach_stmt → FOR EACH ID IN [ string_list ] block": "ag_local_foreach",
              "if_stmt → IF ( cond ) block else_part?": "ag_local_if",
              "var_decl → VAR ID = expr": "ag_local_var_decl",
              "study_stmt → STUDY STRING FOR expr HOURS": "ag_local_study",
              "expr → expr / expr": "ag_local_div"}
    all_problems = []
    for g in locs:
        lhs = next(o for o in g.sym if o not in g.parent)
        prod = g.prod_of[lhs]
        all_problems += check_l_attributed(g)
        if prod in chosen:
            save(chosen[prod], "Gramática de atributos (NB07)", f"Grafo local: {prod}",
                 "Dependências entre os atributos dos símbolos desta produção "
                 "(verde = herdado, laranja = sintetizado, cinzento = léxico).",
                 to_dot(ag_graph_to_nx(g), prod, "TB"))

    r.append("## 2. Grafos de dependências da gramática de atributos\n")
    r.append(f"- Produções com regras semânticas: {len(locs)}")
    r.append(f"- Regras de avaliação (atributos definidos, contando por produção): {rules_count}")
    r.append(f"- Grafo global: {len(nodes)} nós (ocorrências símbolo.atributo), {Gg.number_of_edges()} arestas")
    r.append(f"- Grau médio de entrada/saída: {sum(indeg[n] for n in nodes)/len(nodes):.2f} / "
             f"{sum(outdeg[n] for n in nodes)/len(nodes):.2f}")
    r.append("- Maior grau de entrada (atributos com mais dependências): " +
             ", ".join(f"`{n}` ({indeg[n]})" for n in sorted(nodes, key=lambda n: -indeg[n])[:5]))
    r.append("- Maior grau de saída (atributos mais usados): " +
             ", ".join(f"`{n}` ({outdeg[n]})" for n in sorted(nodes, key=lambda n: -outdeg[n])[:5]))
    r.append(f"- Verificação L-atribuída (todas as produções): "
             f"{'OK, nenhuma aresta viola a condição' if not all_problems else all_problems}\n")

    # (c) grafo instanciado em árvores concretas: acíclico e avaliável numa passagem
    r.append("### Grafo de dependências instanciado nas árvores dos exemplos\n")
    r.append("| Programa | Ocorrências | Atributos (nós) | Dependências (arestas) | Acíclico | "
             "Violações L-atribuída | Violações da ordem de uma passagem |")
    r.append("|---|---|---|---|---|---|---|")
    for P in programs:
        g, root = ag_instance(P.tree)
        acyclic = nx.is_directed_acyclic_graph(g.G)
        viol = check_l_attributed(g)
        order = single_pass_order(g, root)
        r.append(f"| {P.name} | {len(g.sym)} | {g.G.number_of_nodes()} | {g.G.number_of_edges()} | "
                 f"{'sim' if acyclic else 'NÃO'} | {len(viol)} | {len(order)} |")
    r.append("")
    tiny = cs.parser.parse(TINY)
    g, root = ag_instance(tiny)
    topo = list(nx.topological_sort(g.G))
    save("ag_instancia_mini", "Gramática de atributos (NB07)",
         "Grafo de dependências instanciado (programa mínimo)",
         "Regras da AG aplicadas à árvore do programa mínimo (ver analise.md). Cada caixa é um nó da árvore; "
         "as setas pontilhadas cinzentas são as arestas da árvore e as pretas as dependências entre atributos. "
         "O grafo é acíclico, por isso há uma ordem de avaliação (ordenação topológica).",
         to_dot(ag_graph_to_nx(g, tree_edges=True), "ag_instancia", "TB"))
    r.append("Programa mínimo usado no grafo `ag_instancia_mini`:\n")
    r.append("```study\n" + TINY.strip() + "\n```\n")
    r.append(f"O grafo instanciado do programa mínimo tem {len(g.sym)} ocorrências, {len(topo)} atributos e "
             f"{g.G.number_of_edges()} dependências; é acíclico, logo existe uma ordem de avaliação "
             f"(ordenação topológica), e a passagem única em profundidade respeita-a "
             f"({len(single_pass_order(g, root))} violações).\n")


def annotated_ast(P, fname):
    ann = {}
    orig = {k: getattr(cs, k) for k in ("expr", "stmt", "block", "if_stmt", "foreach")}

    def w_expr(n, env):
        t, c, v, e = orig["expr"](n, env)
        ann[id(n)] = f"type={t}" + (f", val={v}" if c else ", const=false")
        return t, c, v, e

    def w_stmt(n, env):
        r = orig["stmt"](n, env)
        if n.data == "study_stmt":
            ann[id(n)] = f"minHours={r[2]}"
        return r

    def w_block(n, env):
        e, m = orig["block"](n, env)
        ann[id(n)] = f"minHours={m}"
        return e, m

    def w_if(n, env):
        e, m = orig["if_stmt"](n, env)
        ann[id(n)] = f"minHours={m}"
        return e, m

    def w_fe(n, env):
        e, m = orig["foreach"](n, env)
        ann[id(n)] = f"minHours={m}"
        return e, m

    for k, f in (("expr", w_expr), ("stmt", w_stmt), ("block", w_block), ("if_stmt", w_if), ("foreach", w_fe)):
        setattr(cs, k, f)
    try:
        cs.check(P.tree)
    finally:
        for k, f in orig.items():
            setattr(cs, k, f)

    G, cnt = nx.DiGraph(), [0]
    expr_kinds = set(OPS) | {"num", "var", "attr", "neg"}
    cond_kinds = {"compare", "and_", "or_", "not_"}

    def walk(n):
        cnt[0] += 1
        me = f"n{cnt[0]}"
        if isinstance(n, Token):
            G.add_node(me, label=f"{n.type}\n{n}", shape="box", fillcolor=C_LEX, fontsize="10")
            return me
        lab = n.data
        if n.data in ("var_decl", "assign_stmt", "study_stmt", "foreach_stmt", "if_stmt"):
            fill = C_STMT
        elif n.data in expr_kinds:
            fill = C_EXPR
        elif n.data in cond_kinds:
            fill = C_COND
        else:
            fill = "white"
        if id(n) in ann:
            lab += "\n" + ann[id(n)]
        G.add_node(me, label=lab, shape="ellipse", fillcolor=fill)
        for c in n.children:
            G.add_edge(me, walk(c))
        return me

    walk(P.tree)
    save(fname, P.name, f"AST anotada ({P.name})",
         "Árvore sintática do Lark com os atributos sintetizados que o verificador calcula: "
         "type/val nas expressões (amarelo) e minHours nas instruções e blocos (azul).",
         to_dot(G, fname, "TB"))
    return G.number_of_nodes()


# ---------------- CFG ----------------
def draw_cfg(P, G, fname, infeasible=frozenset(), unreachable=frozenset()):
    """CFG ao nível das instruções (para a análise de fluxo de dados)."""
    H = nx.DiGraph()
    for n, d in G.nodes(data=True):
        shape = {"entry": "oval", "exit": "oval", "basic": "box", "cond": "diamond", "loop": "hexagon"}[d["kind"]]
        fill = {"cond": C_COND, "loop": C_LOOP, "entry": "white", "exit": "white"}.get(d["kind"], C_STMT)
        if d.get("decl"):
            fill = "white"
        lab = f"{n}  (l.{d['line']})\n{d['text']}" if d["kind"] not in ("entry", "exit") else d["text"]
        if n in unreachable:
            fill, lab = C_DEAD, lab + "\n[inalcançável]"
        H.add_node(n, label=lab, shape=shape, fillcolor=fill)
    for u, v, d in G.edges(data=True):
        a = {"label": d.get("label", "")}
        if d.get("back"):
            a.update(color="#c0392b", fontcolor="#c0392b", label=(a["label"] + " (retorno)").strip())
        if (u, v) in infeasible:
            a.update(style="dashed", color="#999999", label=a["label"] + " [nunca]")
        H.add_edge(u, v, **a)
    save(fname, P.name, f"CFG por instrução ({P.name})",
         "Um nó por instrução: losango = IF, hexágono = cabeçalho do FOR EACH, a vermelho = aresta de "
         "retorno do ciclo. As arestas a tracejado 'nunca' são ramos que a análise de intervalos prova "
         "impossíveis; os nós a cinzento ficam inalcançáveis.",
         to_dot(H, fname, "TB"))


def draw_bb(P, G, B, fname, unreachable=frozenset()):
    H = nx.DiGraph()
    for b, d in B.nodes(data=True):
        if d["kind"] in ("entry", "exit"):
            H.add_node(b, label=b, shape="oval")
            continue
        lines = [f"l.{G.nodes[s]['line']}: {G.nodes[s]['text']}" for s in d["stmts"]]
        shape = {"basic": "box", "cond": "diamond", "loop": "hexagon"}[d["kind"]]
        fill = {"basic": C_STMT, "cond": C_COND, "loop": C_LOOP}[d["kind"]]
        if all(s in unreachable for s in d["stmts"]):
            fill = C_DEAD
            lines.append("[inalcançável]")
        H.add_node(b, label=b + "\n" + "\n".join(lines), shape=shape, fillcolor=fill)
    for u, v, d in B.edges(data=True):
        a = {"label": d.get("label", "")}
        if d.get("back"):
            a.update(color="#c0392b", fontcolor="#c0392b")
        H.add_edge(u, v, **a)
    save(fname, P.name, f"CFG por blocos básicos ({P.name})",
         "Instruções consecutivas sem ramificação agrupadas em blocos básicos, como no NB08. "
         "A aresta vermelha é a aresta de retorno do FOR EACH (o cabeçalho do ciclo é o loop header).",
         to_dot(H, fname, "TB"))


# ---------------- fluxo de dados ----------------


def draw_dfg(P, R, fname):
    G, dead = P.cfg, R["deps"]["dead"]
    H = nx.DiGraph()
    for n in G:
        d = G.nodes[n]
        if d["kind"] in ("entry", "exit") or d.get("decl") or (not d["defs"] and not d["uses"]):
            continue
        isdead = any(n == dn for _, dn in dead)
        H.add_node(n, label=f"{n} (l.{d['line']})\n{d['text']}", shape="box",
                   fillcolor=C_DEAD if isdead else {"cond": C_COND, "loop": C_LOOP}.get(d["kind"], C_STMT),
                   style="filled,dashed" if isdead else "filled")
    for a, b, v in sorted(R["deps"]["du"]):
        lb = P.vname(v)
        if (a, b) in H.edges:
            H.edges[a, b]["label"] += ", " + lb
        else:
            H.add_edge(a, b, label=lb)
    save(fname, P.name, f"DFG ({P.name})",
         "Aresta d → u: a definição em d chega ao uso em u (reaching definitions sobre o CFG, com os "
         "âmbitos resolvidos). Nós a tracejado: definições cujo valor nunca é lido.",
         to_dot(H, fname, "TB"))


def draw_pdg(P, R, fname):
    G, PD, relevant = P.cfg, R["pdg"], R["relevant"]
    H = nx.DiGraph()
    for n in PD:
        d = G.nodes[n]
        if d["kind"] == "entry":
            H.add_node(n, label="ENTRY", shape="oval")
            continue
        H.add_node(n, label=f"{n} (l.{d['line']})\n{d['text']}",
                   shape={"cond": "diamond", "loop": "hexagon"}.get(d["kind"], "box"),
                   fillcolor=C_SLICE if n in relevant else C_DEAD,
                   peripheries="2" if d.get("study") else "1")
    for a, b, d in PD.edges(data=True):
        if d["kind"] == "ctrl":
            lab = d.get("label", "") + (f" + dados: {d['also_data']}" if d.get("also_data") else "")
            H.add_edge(a, b, style="dashed", color="#555555", label=lab)
        else:
            H.add_edge(a, b, label=d["label"], color="#1f5fa8", fontcolor="#1f5fa8")
    save(fname, P.name, f"PDG ({P.name})",
         "Dependências de controlo a tracejado (V/F/próximo) e de dados a azul. A verde: instruções "
         "que pertencem à fatia de algum STUDY (contorno duplo). A cinzento: instruções que não "
         "influenciam nenhuma hora do plano.",
         to_dot(H, fname, "TB"))


def program_graphs(P, R, tag):
    """Acrescenta a GRAPHS os grafos de um programa (AST, CFG, blocos, DFG, PDG)."""
    annotated_ast(P, f"{tag}_ast")
    draw_cfg(P, P.cfg, f"{tag}_cfg", R["infeasible"], R["unreachable"])
    draw_bb(P, P.cfg, R["cfg"]["B"], f"{tag}_cfg_blocos", R["unreachable"])
    draw_dfg(P, R, f"{tag}_dfg")
    draw_pdg(P, R, f"{tag}_pdg")


# ==========================================================================
# 4. Escrita: DOT (+ SVG/PNG com Graphviz) e visualizador HTML
# ==========================================================================
def write_graphs(outdir, graphs):
    outdir.mkdir(parents=True, exist_ok=True)
    for f in outdir.glob("*"):
        if f.suffix in (".dot", ".svg", ".png"):
            f.unlink()
    for fname, _s, _t, _d, dot in graphs:
        (outdir / f"{fname}.dot").write_text(dot, encoding="utf-8")
    dot = shutil.which("dot")
    if dot:
        for fname, *_ in graphs:
            for fmt in ("svg", "png"):
                subprocess.run([dot, f"-T{fmt}", str(outdir / f"{fname}.dot"), "-o",
                                str(outdir / f"{fname}.{fmt}")], check=False)
    return bool(dot)


VIEWER = """<!doctype html>
<html lang="pt"><head><meta charset="utf-8"><title>__TITLE__</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
 body{font-family:system-ui,Segoe UI,Helvetica,sans-serif;margin:0;background:#fafafa;color:#222}
 header{padding:12px 24px;background:#fff;border-bottom:1px solid #ddd;position:sticky;top:0;z-index:2}
 nav a{margin-right:12px;font-size:14px} main{padding:16px 24px;max-width:1400px}
 h2{margin-top:32px;border-bottom:2px solid #ddd;padding-bottom:4px}
 .card{background:#fff;border:1px solid #ddd;border-radius:8px;padding:12px 16px;margin:16px 0}
 .card h3{margin:0 0 4px} .desc{color:#555;font-size:14px;margin:0 0 8px}
 .g{overflow:auto;max-height:85vh;border-top:1px solid #eee;padding-top:8px}
 .g svg{max-width:none;height:auto} button{font-size:12px;margin-right:6px}
 body.fit .g{max-height:none} body.fit .g svg{width:100%;height:auto}
 pre{background:#f4f4f4;padding:8px 12px;border-radius:6px;overflow:auto;font-size:13px}
 table{border-collapse:collapse;font-size:14px;margin:8px 0} td,th{border:1px solid #ccc;padding:4px 8px;text-align:left}
 .erro{color:#b00020;font-weight:600} .aviso{color:#9a5b00} .info{color:#555}
 .cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:12px}
</style></head><body>
<header><b>__TITLE__</b>
 <label style="margin-left:16px;font-size:14px"><input type="checkbox" onchange="document.body.classList.toggle('fit',this.checked)"> ajustar à largura</label>
 <nav id="nav"></nav></header>
<main id="main">__INTRO__</main>
<script src="https://cdn.jsdelivr.net/npm/viz.js@2.1.2/viz.js"></script>
<script src="https://cdn.jsdelivr.net/npm/viz.js@2.1.2/full.render.js"></script>
<script>
const GRAPHS = __DATA__;
const main = document.getElementById('main'), nav = document.getElementById('nav');
document.querySelectorAll('main > h2').forEach((h, i) => { h.id = 'i' + i;
  const a = document.createElement('a'); a.href = '#' + h.id; a.textContent = h.textContent; nav.appendChild(a); });
let sec = null;
function download(name, text, type){const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([text],{type}));a.download=name;a.click();}
(async () => {
  for (const g of GRAPHS) {
    if (g.section !== sec) { sec = g.section; const h = document.createElement('h2'); h.textContent = sec;
      h.id = 's' + nav.children.length; main.appendChild(h);
      const a = document.createElement('a'); a.href = '#' + h.id; a.textContent = sec; nav.appendChild(a); }
    const c = document.createElement('div'); c.className = 'card';
    c.innerHTML = `<h3></h3><p class="desc"></p><div class="btn"></div><div class="g">a desenhar…</div>`;
    c.querySelector('h3').textContent = g.title; c.querySelector('.desc').textContent = g.desc;
    main.appendChild(c);
    try {
      const svg = await new Viz().renderString(g.dot);
      c.querySelector('.g').innerHTML = svg;
      const b1 = document.createElement('button'); b1.textContent = 'Descarregar SVG';
      b1.onclick = () => download(g.file + '.svg', svg, 'image/svg+xml');
      const b2 = document.createElement('button'); b2.textContent = 'Descarregar DOT';
      b2.onclick = () => download(g.file + '.dot', g.dot, 'text/plain');
      c.querySelector('.btn').append(b1, b2);
    } catch (e) { c.querySelector('.g').textContent = 'Erro: ' + e; }
  }
})();
</script></body></html>"""


def write_viewer(path, graphs, title, intro_html=""):
    data = [{"file": f, "section": s, "title": t, "desc": d, "dot": dot} for f, s, t, d, dot in graphs]
    page = (VIEWER.replace("__TITLE__", html.escape(title)).replace("__INTRO__", intro_html)
            .replace("__DATA__", json.dumps(data, ensure_ascii=False)))
    path.write_text(page, encoding="utf-8")


# ==========================================================================
# 5. Programas analisados
# ==========================================================================
TINY = '''STUDENT Ana LEVEL SECONDARY
UC "Fisica" { DIFFICULTY 3 }
PLAN {
    VAR h = 2
    STUDY "Fisica" FOR h * 2 HOURS
}
'''

EXAMPLES = [("Ex1 universitário", "ex1_universitario.study"),
            ("Ex2 secundário", "ex2_secundario.study"),
            ("Ex7 análise", "ex7_analise.study")]


def main():
    programs = [ir.Program(name, (EXEMPLOS / f).read_text(encoding="utf-8")) for name, f in EXAMPLES]
    report = ["# Grafos e análise estática da StudyLang (gerado por parte2/visualizacao.py)\n",
              "Ficheiro gerado automaticamente: não editar à mão. "
              "Os grafos estão em `resultados/grafos/*.dot` e podem ser vistos em `resultados/grafos/index.html`.\n"]
    grammar_dependency_graph(report)
    attribute_grammar_graphs(report, programs)
    report.append("# 3. Grafos dos programas (NB08)\n")
    for P in programs:
        R = analise.analyse(P)
        report += analise.report_md(P, R)
        program_graphs(P, R, P.name.split(" ")[0].lower())
    rendered = write_graphs(OUT, GRAPHS)
    (OUT / "analise.md").write_text("\n".join(report), encoding="utf-8")
    write_viewer(OUT / "index.html", GRAPHS, "StudyLang: grafos de dependências e de fluxo")
    print("\n".join(report))
    print(f"\n{len(GRAPHS)} grafos escritos em {OUT}"
          + (" (DOT, SVG e PNG)" if rendered else " (DOT; instale o Graphviz para gerar SVG/PNG, "
                                                  "ou abra resultados/grafos/index.html)"))


if __name__ == "__main__":
    main()
