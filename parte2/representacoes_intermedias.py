"""
Representações intermédias da StudyLang (NB08).

A partir da árvore validada pelo verificador da Parte I (parte1/verificador.py) constrói:
  * a resolução de nomes (cada uso ligado à sua declaração, com os âmbitos da AG);
  * o CFG ao nível das instruções e o CFG de blocos básicos;
  * as análises de fluxo de dados (reaching definitions, reaching uses) e o DFG;
  * o PDG (dependências de dados + controlo) e as fatias (slicing).
"""
from collections import defaultdict

import networkx as nx
from lark import Token, Tree

from parte1 import verificador as cs

OPS = {"add": "+", "sub": "-", "mul": "*", "div": "/"}
PREC = {"add": 1, "sub": 1, "mul": 2, "div": 2}


# --------------------------------------------------------------------------
# Impressão de expressões e condições (também usada pelo pretty-printer)
# --------------------------------------------------------------------------
def src(n):
    """Texto de uma expressão/condição; os parênteses repõem exatamente a árvore."""
    if isinstance(n, Token):
        return str(n)
    d = n.data
    if d in ("num", "var"):
        return str(n.children[0])
    if d == "attr":
        return f"{n.children[0]}.{n.children[1].children[0]}"
    if d == "neg":
        c = n.children[0]
        return "-" + (f"({src(c)})" if isinstance(c, Tree) and c.data in PREC else src(c))
    if d in OPS:
        a, b = n.children
        sa, sb = src(a), src(b)
        if isinstance(a, Tree) and PREC.get(a.data, 3) < PREC[d]:
            sa = f"({sa})"
        if isinstance(b, Tree) and PREC.get(b.data, 3) <= PREC[d]:   # associatividade à esquerda
            sb = f"({sb})"
        return f"{sa} {OPS[d]} {sb}"
    if d == "compare":
        return f"{src(n.children[0])} {n.children[1]} {src(n.children[2])}"
    if d == "and_":
        return f"{src(n.children[0])} AND {src(n.children[1])}"
    if d == "or_":
        return f"{src(n.children[0])} OR {src(n.children[1])}"
    if d == "not_":
        return f"NOT {src(n.children[0])}"
    return d


def line_of(n):
    if isinstance(n, Token):
        return n.line
    return getattr(n.meta, "line", None)


# --------------------------------------------------------------------------
# Resolução de nomes (âmbito estático por bloco, igual ao env da AG)
# --------------------------------------------------------------------------
def resolve(tree):
    """Devolve ref: id(token) -> var_id e info: var_id -> {name, line, kind}."""
    ref, info, scopes = {}, {}, [{}]

    def declare(tok, kind):
        vid = f"{tok}@{tok.line}"
        info[vid] = {"name": str(tok), "line": tok.line, "kind": kind}
        scopes[-1][str(tok)] = vid
        ref[id(tok)] = vid

    def lookup(tok):
        ref[id(tok)] = next((s[str(tok)] for s in reversed(scopes) if str(tok) in s), None)

    def ex(n):
        if isinstance(n, Tree):
            if n.data in ("var", "attr"):
                lookup(n.children[0])
            else:
                for c in n.children:
                    ex(c)

    def blk(b):
        scopes.append({})
        for s in b.children:
            st(s)
        scopes.pop()

    def st(n):
        d = n.data
        if d == "var_decl":
            ex(n.children[1])
            declare(n.children[0], "var")
        elif d == "assign_stmt":
            ex(n.children[1])
            lookup(n.children[0])
        elif d == "study_stmt":
            ex(n.children[1])
            if n.children[0].type == "ID":
                lookup(n.children[0])
        elif d == "if_stmt":
            ex(n.children[0])
            blk(n.children[1])
            if len(n.children) == 3:
                p = n.children[2].children[0]
                st(p) if p.data == "if_stmt" else blk(p)
        elif d == "foreach_stmt":
            scopes.append({})
            declare(n.children[0], "iter")
            blk(n.children[2])
            scopes.pop()

    for d in tree.children[2:-1]:
        if d.data == "var_decl":
            st(d)
    blk(tree.children[-1].children[0])
    return ref, info


class Program:
    """Um programa StudyLang analisado: árvore, erros da AG, nomes, UCs e CFG."""

    def __init__(self, name, source, tree=None):
        """`tree` permite analisar uma árvore já transformada (mantém as linhas do original)."""
        self.name, self.source = name, source
        self.tree = tree if tree is not None else cs.parser.parse(source)   # pode lançar UnexpectedInput
        self.errors = cs.check(self.tree)
        self.valid = not self.errors
        self.ucs, self.limit = {}, None
        for d in self.tree.children[2:-1]:
            if d.data == "uc_decl":
                a = {c.data: int(c.children[1]) for c in d.children[1:] if isinstance(c, Tree)}
                self.ucs[str(d.children[0])[1:-1]] = {"CREDITS": a.get("credits"), "DIFFICULTY": a["difficulty"]}
            elif d.data == "resource_decl" and self.limit is None:
                self.limit = int(d.children[0])
        self.level = self.tree.children[1].data.upper()
        self.student = str(self.tree.children[0])
        self.node_of = {}
        if self.valid:
            self.ref, self.vars = resolve(self.tree)
            self.cfg = build_cfg(self)

    def vname(self, vid):
        """Nome legível de uma variável; mostra a linha se houver sombreamento."""
        info = self.vars[vid]
        same = [v for v in self.vars if self.vars[v]["name"] == info["name"]]
        return info["name"] if len(same) == 1 else f"{info['name']}@{info['line']}"

    def uses_of(self, n):
        out = set()
        if isinstance(n, Tree):
            if n.data in ("var", "attr"):
                v = self.ref.get(id(n.children[0]))
                if v:
                    out.add(v)
            else:
                for c in n.children:
                    out |= self.uses_of(c)
        return out


# --------------------------------------------------------------------------
# CFG
# --------------------------------------------------------------------------
def build_cfg(P):
    """CFG ao nível das instruções. Nós: entry, exit, basic, cond (IF), loop (FOR EACH)."""
    G = nx.DiGraph()
    cnt = [0]

    def node(kind, text, line, tree=None, defs=(), uses=(), ctrl=None, **kw):
        cnt[0] += 1
        n = f"S{cnt[0]}"
        G.add_node(n, kind=kind, text=text, line=line, defs=list(defs), uses=set(uses),
                   ctrl=ctrl, order=cnt[0], **kw)
        if tree is not None:
            P.node_of[id(tree)] = n
        return n

    def link(preds, n):
        for p, lab in preds:
            if G.has_edge(p, n):
                G.edges[p, n]["label"] = G.edges[p, n].get("label", "") + "/" + (lab or "")
            elif lab:
                G.add_edge(p, n, label=lab)
            else:
                G.add_edge(p, n)

    def stmts(lst, preds, ctrl):
        for s in lst:
            preds = stmt(s, preds, ctrl)
        return preds

    def stmt(s, preds, ctrl):
        d = s.data
        line = s.meta.line
        if d == "var_decl":
            name, e = s.children
            n = node("basic", f"VAR {name} = {src(e)}", line, s, [P.ref[id(name)]], P.uses_of(e), ctrl)
        elif d == "assign_stmt":
            name, e = s.children
            n = node("basic", f"{name} = {src(e)}", line, s, [P.ref[id(name)]], P.uses_of(e), ctrl)
        elif d == "study_stmt":
            t, e = s.children
            u = P.uses_of(e) | ({P.ref[id(t)]} if t.type == "ID" and P.ref.get(id(t)) else set())
            n = node("basic", f"STUDY {t} FOR {src(e)} HOURS", line, s, [], u, ctrl, study=True)
        elif d == "if_stmt":
            c = node("cond", f"IF ( {src(s.children[0])} )", line, s, [], P.uses_of(s.children[0]), ctrl)
            link(preds, c)
            t = stmts(s.children[1].children, [(c, "V")], (c, "V"))
            if len(s.children) == 3:
                p = s.children[2].children[0]
                f = stmt(p, [(c, "F")], (c, "F")) if p.data == "if_stmt" else stmts(p.children, [(c, "F")], (c, "F"))
            else:
                f = [(c, "F")]
            return t + f
        else:  # foreach
            it, lst, b = s.children
            names = ", ".join(str(x) for x in lst.children)
            h = node("loop", f"FOR EACH {it} IN [{names}]", line, s, [P.ref[id(it)]], [], ctrl,
                     count=len(lst.children))
            link(preds, h)
            body = stmts(b.children, [(h, "próximo")], (h, "próximo"))
            for p, lab in body:
                if G.has_edge(p, h):
                    G.edges[p, h]["back"] = True
                else:
                    G.add_edge(p, h, back=True, **({"label": lab} if lab else {}))
            return [(h, "fim")]
        link(preds, n)
        return [(n, None)]

    _name, level, *rest = P.tree.children
    entry = node("entry", f"ENTRY\nSTUDENT {_name} LEVEL {level.data.upper()}", P.tree.meta.line)
    preds = [(entry, None)]
    for d in rest[:-1]:
        if d.data == "var_decl":
            preds = stmt(d, preds, None)
        else:
            if d.data == "uc_decl":
                txt = f"UC {d.children[0]} {{ " + " ".join(
                    f"{c.children[0]} {c.children[1]}" for c in d.children[1:] if isinstance(c, Tree)) + " }"
            else:
                txt = f"RESOURCE TIME {d.children[0]} HOURS"
            n = node("basic", txt, d.meta.line, d, decl=True)
            link(preds, n)
            preds = [(n, None)]
    preds = stmts(rest[-1].children[0].children, preds, None)
    ex = node("exit", "EXIT", 0)
    link(preds, ex)
    G.graph["entry"], G.graph["exit"] = entry, ex
    return G


def back_edges(G, start):
    back, color = set(), {}

    def dfs(u):
        color[u] = 1
        for v in G.successors(u):
            if color.get(v) == 1:
                back.add((u, v))
            elif v not in color:
                dfs(v)
        color[u] = 2

    dfs(start)
    return back


def basic_blocks(G):
    """Agrupa instruções consecutivas em blocos básicos (como o merge do NB08)."""
    order = sorted(G.nodes, key=lambda n: G.nodes[n]["order"])
    leader = {}
    for n in order:
        preds = list(G.predecessors(n))
        p = preds[0] if len(preds) == 1 else None
        if (G.nodes[n]["kind"] == "basic" and p is not None and G.nodes[p]["kind"] == "basic"
                and G.out_degree(p) == 1 and not G.edges[p, n].get("back")):
            leader[n] = leader[p]
        else:
            leader[n] = n
    groups = defaultdict(list)
    for n in order:
        groups[leader[n]].append(n)
    B = nx.DiGraph()
    name, k = {}, 0
    for ld in sorted(groups, key=lambda n: G.nodes[n]["order"]):
        kind = G.nodes[ld]["kind"]
        if kind in ("entry", "exit"):
            name[ld] = kind.upper()
        else:
            k += 1
            name[ld] = f"B{k}"
        B.add_node(name[ld], kind=kind, stmts=groups[ld])
    for u, v, d in G.edges(data=True):
        bu, bv = name[leader[u]], name[leader[v]]
        if bu != bv or d.get("back"):
            B.add_edge(bu, bv, **d)
    return B, {n: name[leader[n]] for n in G}


def count_paths(B):
    """Caminhos ENTRY→EXIT em que cada ciclo é percorrido no máximo uma vez:
    cada aresta de retorno u→h passa a ligar u à saída do ciclo (sucessor 'fim' de h)."""
    def loop_exit(h):
        # sucessor 'fim' do cabeçalho; se a saída for ela própria uma aresta de retorno
        # (ciclo interior no fim do corpo de outro), sobe para a saída do ciclo exterior
        for v in B.successors(h):
            if "fim" in B.edges[h, v].get("label", "").split("/"):
                return loop_exit(v) if B.edges[h, v].get("back") else v
        return None

    D = B.copy()
    for u, h, d in list(B.edges(data=True)):
        if d.get("back"):
            D.remove_edge(u, h)
            v = loop_exit(h)
            if v is not None:
                D.add_edge(u, v)
    paths = {n: 0 for n in D}
    paths["ENTRY"] = 1
    for n in nx.topological_sort(D):
        for v in D.successors(n):
            paths[v] += paths[n]
    return paths["EXIT"]


def exec_bound(G, n):
    """Número máximo de execuções de uma instrução (produto dos tamanhos das listas dos ciclos)."""
    k, c = 1, G.nodes[n]["ctrl"]
    if G.nodes[n]["kind"] == "loop":
        k = G.nodes[n]["count"] + 1
    while c is not None:
        cn = c[0]
        if G.nodes[cn]["kind"] == "loop":
            k *= G.nodes[cn]["count"]
        c = G.nodes[cn]["ctrl"]
    return k


def cfg_metrics(P):
    G = P.cfg
    B, bb_of = basic_blocks(G)
    back = back_edges(B, "ENTRY")
    depth = 0
    for n in G:
        k, c = 0, G.nodes[n]["ctrl"]
        while c is not None:
            k, c = k + 1, G.nodes[c[0]]["ctrl"]
        depth = max(depth, k)
    plan = [n for n in G if G.nodes[n]["kind"] in ("basic", "cond", "loop") and not G.nodes[n].get("decl")]
    return {
        "B": B, "bb_of": bb_of, "back": sorted(back),
        "stmts": G.number_of_nodes() - 2, "blocks": B.number_of_nodes() - 2,
        "nodes": B.number_of_nodes(), "edges": B.number_of_edges(),
        "decisions": sum(1 for _, d in B.nodes(data=True) if d["kind"] in ("cond", "loop")),
        "cyclomatic": B.number_of_edges() - B.number_of_nodes() + 2,
        "paths": count_paths(B), "depth": depth,
        "unreachable": sorted(set(G) - nx.descendants(G, G.graph["entry"]) - {G.graph["entry"]}),
        "max_exec": sum(exec_bound(G, n) for n in plan),
    }


# --------------------------------------------------------------------------
# Fluxo de dados
# --------------------------------------------------------------------------
def dataflow(G, gen, extra, kill_by):
    """Análise para a frente até ao ponto fixo (NB08):
    IN[n] = ∪ OUT[p];  OUT[n] = gen[n] ∪ {f ∈ IN[n] ∪ extra[n] | não kill(n, f)}."""
    order = sorted(G.nodes, key=lambda n: G.nodes[n]["order"])
    IN = {n: frozenset() for n in G}
    OUT = {n: frozenset() for n in G}
    it, changed = 0, True
    while changed:
        changed, it = False, it + 1
        for n in order:
            i = frozenset().union(*(OUT[p] for p in G.predecessors(n)))
            o = frozenset({f for f in i | extra(n) if not kill_by(n, f)} | gen(n))
            if i != IN[n] or o != OUT[n]:
                IN[n], OUT[n], changed = i, o, True
    return IN, OUT, it


def reaching_definitions(G, key=lambda v: v):
    gen = {n: {(key(v), n) for v in G.nodes[n]["defs"]} for n in G}
    defvars = {n: {key(v) for v in G.nodes[n]["defs"]} for n in G}
    return dataflow(G, lambda n: frozenset(gen[n]), lambda n: frozenset(),
                    lambda n, f: f[0] in defvars[n] and f[1] != n)


def def_use_edges(G, IN, key=lambda v: v):
    edges, undefined = set(), []
    for n in G:
        for v in G.nodes[n]["uses"]:
            ds = [d for (w, d) in IN[n] if w == key(v)]
            if not ds:
                undefined.append((n, v))
            for d in ds:
                edges.add((d, n, key(v)))
    return edges, undefined


def reaching_uses(G):
    defvars = {n: set(G.nodes[n]["defs"]) for n in G}
    return dataflow(G, lambda n: frozenset(), lambda n: frozenset((v, n) for v in G.nodes[n]["uses"]),
                    lambda n, f: f[0] in defvars[n])


def dependencies(P):
    """Dependências verdadeiras, anti e de saída; versão ingénua sem âmbitos; definições mortas."""
    G = P.cfg
    IN, OUT, iters = reaching_definitions(G)
    du, undefined = def_use_edges(G, IN)
    INu, _, _ = reaching_uses(G)
    anti = sorted({(s, d, v) for d in G for v in G.nodes[d]["defs"] for (w, s) in INu[d] if w == v and s != d})
    output = sorted({(d0, d, v) for d in G for v in G.nodes[d]["defs"] for (w, d0) in IN[d] if w == v})
    name_of = lambda v: P.vars[v]["name"]
    IN_n, _, _ = reaching_definitions(G, key=name_of)
    du_n, _ = def_use_edges(G, IN_n, key=name_of)
    false_deps = du_n - {(a, b, name_of(v)) for a, b, v in du}
    used = {(v, d) for d, _, v in du}
    dead = [(v, n) for n in G for v in G.nodes[n]["defs"] if (v, n) not in used]
    return {"IN": IN, "iterations": iters, "du": du, "undefined": undefined, "anti": anti,
            "output": output, "naive": du_n, "false": sorted(false_deps), "dead": dead}


def pdg(P, du):
    """PDG: arestas de controlo (estrutura) + arestas de dados (DFG)."""
    G = P.cfg
    entry = G.graph["entry"]
    PD = nx.DiGraph()
    for n in G:
        d = G.nodes[n]
        if d["kind"] == "exit" or d.get("decl"):
            continue
        PD.add_node(n)
        if d["kind"] != "entry":
            c = d["ctrl"]
            PD.add_edge(c[0] if c else entry, n, kind="ctrl", label=c[1] if c else "")
    for a, b, v in du:
        if PD.has_edge(a, b) and PD.edges[a, b]["kind"] == "ctrl":
            PD.edges[a, b]["also_data"] = P.vname(v)
        elif PD.has_edge(a, b):
            PD.edges[a, b]["label"] += ", " + P.vname(v)
        else:
            PD.add_edge(a, b, kind="data", label=P.vname(v))
    return PD


def slices(P, PD):
    """Fatia para trás de cada STUDY e união (instruções relevantes para o plano)."""
    G = P.cfg
    studies = [n for n in G if G.nodes[n].get("study")]
    sl = {s: nx.ancestors(PD, s) | {s} for s in studies}
    relevant = set().union(*sl.values()) if sl else set()
    irrelevant = [n for n in G if G.nodes[n]["kind"] in ("basic", "cond", "loop")
                  and not G.nodes[n].get("decl") and n not in relevant]
    return sl, relevant, irrelevant
