"""
Análise estática da StudyLang.

  * Interp: interpretação abstrata com o domínio de intervalos (NB08) e avaliação exata.
    A avaliação exata é possível porque os programas são fechados (sem entrada de dados)
    e os ciclos são limitados por listas literais finitas.
  * analyse(P): junta as métricas do CFG, as dependências (DFG/PDG), as fatias e a análise
    das horas num único resultado.
  * diagnostics(P, R): erros e avisos para o utilizador (P11 exata, divisão por zero em
    tempo de execução, ramos impossíveis, código sem efeito, UCs sem estudo, ...).
"""
from collections import Counter, defaultdict

import networkx as nx

import check_studylang as cs
import ir

INF = float("inf")


# --------------------------------------------------------------------------
# Domínio de intervalos
# --------------------------------------------------------------------------
def i_add(a, b):
    return (a[0] + b[0], a[1] + b[1])


def i_neg(a):
    return (-a[1], -a[0])


def i_mul(a, b):
    m = lambda x, y: 0 if x == 0 or y == 0 else x * y
    ps = [m(x, y) for x in a for y in b]
    return (min(ps), max(ps))


def i_div(a, b):
    """Divisão inteira (//, como no verificador). Divisor que pode ser 0 → ⊤."""
    if b[0] <= 0 <= b[1] or INF in (abs(a[0]), abs(a[1]), abs(b[0]), abs(b[1])):
        return (-INF, INF)
    ps = [x // y for x in a for y in b]
    return (min(ps), max(ps))


def i_hull(a, b):
    """Junção (⊔) de dois intervalos; None é ⊥ (sem valor)."""
    if a is None:
        return b
    if b is None:
        return a
    return (min(a[0], b[0]), max(a[1], b[1]))


def fmt_iv(h):
    f = lambda x: "∞" if x == INF else ("-∞" if x == -INF else str(x))
    return f(h[0]) if h[0] == h[1] else f"[{f(h[0])}, {f(h[1])}]"


def verdict(h, limit, lower_only=False):
    if limit is None:
        return "sem RESOURCE"
    if h[0] > limit:
        return f"excede de certeza ({fmt_iv((h[0], h[0]))} > {limit})"
    if lower_only:
        return "não deteta excesso"
    if h[1] > limit:
        return "pode exceder (alarme possível)"
    return "cumpre de certeza"


# --------------------------------------------------------------------------
# Interpretação abstrata / avaliação exata
# --------------------------------------------------------------------------
class Interp:
    """modes:
      'exact'    o iterador é ligado a cada UC da lista, uma volta de cada vez (avaliação exata);
      'interval' o iterador vale todas as UCs da lista (intervalos); as condições são avaliadas
                 em lógica de três valores (T, F, ?) e os ramos impossíveis são descartados;
      'nocond'   como 'interval', mas os dois ramos de cada IF são sempre considerados.
    Regista, para cada nó, os valores observados (usados pelas transformações)."""

    def __init__(self, P, mode):
        self.P, self.mode = P, mode
        self.outcomes = defaultdict(set)      # nó do CFG (IF) -> {T, F, ?}
        self.expr_vals = {}                   # id(expr) -> junção dos intervalos observados
        self.cond_vals = defaultdict(set)     # id(cond) -> {T, F, ?}
        self.visits = Counter()               # nó do CFG -> número de execuções
        self.per_uc = Counter()
        self.trace = []                       # sessões (UC, horas) pela ordem de execução
        self.nonpositive, self.div_zero = [], []
        self.state = None

    # ---- expressões ----
    def ev(self, e, st, it):
        v = self._ev(e, st, it)
        self.expr_vals[id(e)] = i_hull(self.expr_vals.get(id(e)), v)
        return v

    def _ev(self, e, st, it):
        d = e.data
        if d == "num":
            v = int(e.children[0])
            return (v, v)
        if d == "var":
            return st[self.P.ref[id(e.children[0])]]
        if d == "attr":
            vals = [self.P.ucs[u][str(e.children[1].children[0])] for u in it[self.P.ref[id(e.children[0])]]]
            vals = [v for v in vals if v is not None] or [0]
            return (min(vals), max(vals))
        if d == "neg":
            return i_neg(self.ev(e.children[0], st, it))
        a, b = self.ev(e.children[0], st, it), self.ev(e.children[1], st, it)
        if d == "add":
            return i_add(a, b)
        if d == "sub":
            return i_add(a, i_neg(b))
        if d == "mul":
            return i_mul(a, b)
        if b[0] <= 0 <= b[1] and not (b == (0, 0) and e.children[1].data == "num"):
            self.div_zero.append((e.meta.line, b == (0, 0), ir.src(e), dict(it)))
        return i_div(a, b)

    # ---- condições (lógica de três valores) ----
    def evc(self, c, st, it):
        v = self._evc(c, st, it)
        self.cond_vals[id(c)].add(v)
        return v

    def _evc(self, c, st, it):
        d = c.data
        if d == "compare":
            a, op, b = self.ev(c.children[0], st, it), str(c.children[1]), self.ev(c.children[2], st, it)
            if op == "<":
                return "T" if a[1] < b[0] else "F" if a[0] >= b[1] else "?"
            if op == "<=":
                return "T" if a[1] <= b[0] else "F" if a[0] > b[1] else "?"
            if op == ">":
                return "T" if a[0] > b[1] else "F" if a[1] <= b[0] else "?"
            if op == ">=":
                return "T" if a[0] >= b[1] else "F" if a[1] < b[0] else "?"
            eq = "T" if a[0] == a[1] == b[0] == b[1] else "F" if a[1] < b[0] or b[1] < a[0] else "?"
            return eq if op == "==" else {"T": "F", "F": "T", "?": "?"}[eq]
        if d == "not_":
            return {"T": "F", "F": "T", "?": "?"}[self.evc(c.children[0], st, it)]
        x, y = self.evc(c.children[0], st, it), self.evc(c.children[1], st, it)
        if d == "and_":
            return "F" if "F" in (x, y) else "T" if x == y == "T" else "?"
        return "T" if "T" in (x, y) else "F" if x == y == "F" else "?"

    # ---- instruções ----
    @staticmethod
    def join(a, b):
        return {k: i_hull(a.get(k), b.get(k)) for k in set(a) | set(b)}

    def block(self, stmts, st, it):
        for s in stmts:
            st = self.stmt(s, st, it)
        return st

    def stmt(self, s, st, it):
        d = s.data
        node = self.P.node_of.get(id(s))
        if node:
            self.visits[node] += 1
        if d in ("var_decl", "assign_stmt"):
            st = dict(st)
            st[self.P.ref[id(s.children[0])]] = self.ev(s.children[1], st, it)
            return st
        if d == "study_stmt":
            t, e = s.children
            h = self.ev(e, st, it)
            st = dict(st)
            st["HOURS"] = i_add(st["HOURS"], h)
            if self.mode == "exact":
                uc = str(t)[1:-1] if t.type == "STRING" else it[self.P.ref[id(t)]][0]
                self.per_uc[uc] += h[0]
                self.trace.append((uc, h[0]))
                if h[0] <= 0:
                    self.nonpositive.append((s.meta.line, uc, h[0]))
            return st
        if d == "if_stmt":
            res = "?" if self.mode == "nocond" else self.evc(s.children[0], st, it)
            self.outcomes[node].add(res)
            then = lambda: self.block(s.children[1].children, st, it)

            def other():
                if len(s.children) < 3:
                    return st
                p = s.children[2].children[0]
                return self.stmt(p, st, it) if p.data == "if_stmt" else self.block(p.children, st, it)

            if res == "T":
                return then()
            if res == "F":
                return other()
            return self.join(then(), other())
        # FOR EACH: ciclo limitado pelo tamanho da lista, por isso não precisa de widening
        itv, lst, b = s.children
        vid = self.P.ref[id(itv)]
        items = [str(x)[1:-1] for x in lst.children]
        if self.mode == "exact":
            for u in items:
                st = self.block(b.children, st, {**it, vid: [u]})
        else:
            for _ in items:
                st = self.block(b.children, st, {**it, vid: items})
        return st

    def run(self):
        st = {"HOURS": (0, 0)}
        for d in self.P.tree.children[2:-1]:
            if d.data == "var_decl":
                st = self.stmt(d, st, {})
        self.state = self.block(self.P.tree.children[-1].children[0].children, st, {})
        return self

    @property
    def hours(self):
        return self.state["HOURS"]


def exact(P):
    return Interp(P, "exact").run()


def ag_min_hours(P):
    """O minHours que a AG (Parte I) calcula para o plano."""
    orig, last = cs.block, {}

    def w(n, env):
        res = orig(n, env)
        last["r"] = res
        return res

    cs.block = w
    try:
        cs.check(P.tree)
    finally:
        cs.block = orig
    return last["r"][1]


# --------------------------------------------------------------------------
# Análise completa de um programa
# --------------------------------------------------------------------------
def analyse(P):
    """Resultado de todas as análises (só para programas semanticamente válidos)."""
    assert P.valid, "a análise de fluxo exige um programa sem erros semânticos"
    G = P.cfg
    R = {"cfg": ir.cfg_metrics(P)}
    R["deps"] = ir.dependencies(P)
    R["pdg"] = ir.pdg(P, R["deps"]["du"])
    R["slices"], R["relevant"], R["irrelevant"] = ir.slices(P, R["pdg"])
    R["min_hours"] = ag_min_hours(P)
    R["interp"] = {m: Interp(P, m).run() for m in ("nocond", "interval", "exact")}
    iv, ex = R["interp"]["interval"], R["interp"]["exact"]

    infeasible, never, conds = set(), [], []
    for n in G:
        if G.nodes[n]["kind"] != "cond":
            continue
        ai, ee = iv.outcomes.get(n, set()), ex.outcomes.get(n, set())
        conds.append((n, ai, ee))
        for lab, val in (("V", "T"), ("F", "F")):
            if ai and val not in ai and "?" not in ai:
                for v in G.successors(n):
                    if lab in G.edges[n, v].get("label", "").split("/"):
                        infeasible.add((n, v))
            if ee and val not in ee:
                never.append((n, lab))
    Gf = G.copy()
    Gf.remove_edges_from(infeasible)
    unreachable = set(G) - nx.descendants(Gf, G.graph["entry"]) - {G.graph["entry"], G.graph["exit"]}
    R.update(conds=conds, infeasible=infeasible, unreachable=unreachable, never=never)
    return R


# --------------------------------------------------------------------------
# Diagnósticos (o que a ferramenta mostra ao utilizador)
# --------------------------------------------------------------------------
def diagnostics(P, R=None):
    """Lista de (nível, linha, código, mensagem), ordenada por linha."""
    out = [("erro", ln, "AG", msg) for ln, msg in P.errors]
    if not P.valid:
        return out
    R = R or analyse(P)
    G = P.cfg
    ex, iv = R["interp"]["exact"], R["interp"]["interval"]
    plan_line = P.tree.children[-1].meta.line
    h = ex.hours
    ag_flagged = any("RESOURCE TIME" in m for _, _, _, m in out)
    if P.limit is not None and h[0] > P.limit and not ag_flagged:
        out.append(("erro", plan_line, "HORAS",
                    f"o plano aloca {fmt_iv(h)} h e só há {P.limit} h em RESOURCE TIME "
                    f"(a AG só garante ≥ {R['min_hours']} h e não deteta o excesso)"))
    elif P.limit is not None and iv.hours[1] > P.limit >= h[0]:
        out.append(("info", plan_line, "HORAS",
                    f"os intervalos admitem até {fmt_iv((iv.hours[1],) * 2)} h, mas a avaliação exata "
                    f"dá {fmt_iv(h)} h ≤ {P.limit}: o limite é cumprido"))
    for ln, certain, txt, it in ex.div_zero:
        out.append(("erro", ln, "DIV_ZERO", f"divisão por zero em tempo de execução em `{txt}`"
                    + (f" (com {', '.join(f'{P.vname(k)} = {v[0]}' for k, v in it.items())})" if it else "")))
    for ln, uc, v in ex.nonpositive:
        out.append(("erro", ln, "HORAS_POS", f"STUDY de \"{uc}\" com {v} h (as horas têm de ser positivas)"))
    for n, ai, _ in R["conds"]:
        if ai in ({"T"}, {"F"}):
            out.append(("aviso", G.nodes[n]["line"], "COND_CONST",
                        f"condição sempre {'verdadeira' if ai == {'T'} else 'falsa'}: `{G.nodes[n]['text']}`"))
    for n in sorted(R["unreachable"], key=lambda n: G.nodes[n]["order"]):
        out.append(("aviso", G.nodes[n]["line"], "INALCANCAVEL", f"instrução inalcançável: `{G.nodes[n]['text']}`"))
    dead_nodes = {n for _, n in R["deps"]["dead"]}
    for v, n in R["deps"]["dead"]:
        out.append(("aviso", G.nodes[n]["line"], "DEF_MORTA",
                    f"o valor de `{P.vname(v)}` definido aqui nunca é lido: `{G.nodes[n]['text']}`"))
    for n in R["irrelevant"]:
        if n not in dead_nodes and n not in R["unreachable"]:
            out.append(("aviso", G.nodes[n]["line"], "SEM_EFEITO",
                        f"não influencia nenhuma hora de estudo: `{G.nodes[n]['text']}`"))
    for n, lab in R["never"]:
        if not any(a == n for a, _ in R["infeasible"]):
            out.append(("info", G.nodes[n]["line"], "RAMO_NAO_EXEC",
                        f"o ramo {lab} de `{G.nodes[n]['text']}` nunca é executado com as UCs deste plano"))
    for uc in P.ucs:
        if ex.per_uc.get(uc, 0) == 0:
            out.append(("aviso", P.tree.children[-1].meta.line, "UC_SEM_ESTUDO",
                        f"a UC \"{uc}\" está declarada mas não tem horas no plano"))
    rank = {"erro": 0, "aviso": 1, "info": 2}
    return sorted(out, key=lambda d: (d[1] or 0, rank[d[0]]))


# --------------------------------------------------------------------------
# Relatório em Markdown
# --------------------------------------------------------------------------
def report_md(P, R):
    G = P.cfg
    nm = P.vname
    c, d = R["cfg"], R["deps"]
    B = c["B"]
    r = [f"## {P.name}\n", "```study\n" + P.source.strip() + "\n```\n",
         f"Erros semânticos (check_studylang): {len(P.errors) or 'nenhum'}\n",
         "### Grafo de fluxo de controlo (CFG)\n",
         f"- Instruções no CFG: {c['stmts']}; blocos básicos: {c['blocks']} (+ENTRY, EXIT)",
         f"- Arestas entre blocos: {c['edges']}; arestas de retorno (ciclos): " +
         (", ".join(f"{u}→{v}" for u, v in c["back"]) or "nenhuma"),
         f"- Complexidade ciclomática V(G) = E − N + 2 = {c['edges']} − {c['nodes']} + 2 = {c['cyclomatic']} "
         f"(= decisões + 1 = {c['decisions']} + 1)",
         f"- Caminhos ENTRY→EXIT com cada ciclo percorrido 0 ou 1 vezes: {c['paths']} "
         f"(o caminho que salta o ciclo é impossível na prática: as listas do FOR EACH nunca são vazias)",
         f"- Profundidade máxima de aninhamento: {c['depth']}",
         f"- Instruções estruturalmente inalcançáveis: {len(c['unreachable']) or 'nenhuma'}",
         f"- Terminação: o único ciclo é FOR EACH sobre uma lista literal finita, por isso o programa "
         f"termina sempre; no máximo {c['max_exec']} execuções de instruções do plano.\n",
         "| Bloco | Instruções |", "|---|---|"]
    for b, bd in B.nodes(data=True):
        if bd["kind"] not in ("entry", "exit"):
            r.append(f"| {b} | " + "<br>".join(f"l.{G.nodes[s]['line']} `{G.nodes[s]['text']}`" for s in bd["stmts"]) + " |")
    r += ["", "### Definições e usos; reaching definitions (DFG)\n",
          f"Ponto fixo atingido em {d['iterations']} iterações.\n",
          "| Nó | Linha | Instrução | Def | Use | Definições que chegam aos usos |", "|---|---|---|---|---|---|"]
    for n in sorted(G, key=lambda n: G.nodes[n]["order"]):
        nd = G.nodes[n]
        if nd["kind"] in ("entry", "exit") or nd.get("decl"):
            continue
        reach_u = sorted({f"{nm(v)}←{dd}" for (v, dd) in d["IN"][n] if v in nd["uses"]})
        r.append(f"| {n} | {nd['line']} | `{nd['text']}` | {', '.join(nm(v) for v in nd['defs'])} | "
                 f"{', '.join(sorted(nm(v) for v in nd['uses']))} | {', '.join(reach_u)} |")
    r += ["",
          f"- Dependências verdadeiras (fluxo): {len(d['du'])}",
          f"- Antidependências (lê antes de ser reescrita): {len(d['anti'])} — " +
          (", ".join(f"{s}→{t} ({nm(v)})" for s, t, v in d["anti"]) or "nenhuma"),
          f"- Dependências de saída (duas escritas da mesma variável): {len(d['output'])} — " +
          (", ".join(f"{a}→{b} ({nm(v)}{', entre iterações' if a == b else ''})" for a, b, v in d["output"]) or "nenhuma"),
          f"- Se ignorássemos os âmbitos (variáveis só pelo nome): {len(d['naive'])} dependências, "
          f"{len(d['false'])} falsas" +
          (" — " + ", ".join(f"{a}→{b} ({v})" for a, b, v in d["false"]) if d["false"] else "") + "\n",
          "### PDG e slicing\n",
          "Fatia para trás (backward slice) de cada STUDY, seguindo dependências de dados e de controlo:\n",
          "| Critério | Instruções na fatia (linhas) |", "|---|---|"]
    for s, sl in R["slices"].items():
        lines = sorted({G.nodes[x]["line"] for x in sl if G.nodes[x]["kind"] != "entry"})
        r.append(f"| l.{G.nodes[s]['line']} `{G.nodes[s]['text']}` | {', '.join(map(str, lines))} |")
    r += ["",
          "- Definições nunca lidas: " +
          (", ".join(f"`{G.nodes[n]['text']}` (l.{G.nodes[n]['line']})" for _, n in d["dead"]) or "nenhuma"),
          "- Instruções fora de todas as fatias (não influenciam nenhuma hora de estudo): " +
          (", ".join(f"`{G.nodes[n]['text']}` (l.{G.nodes[n]['line']})" for n in R["irrelevant"]) or "nenhuma") + "\n",
          "### Análise estática das horas (P11)\n",
          f"RESOURCE TIME = {P.limit if P.limit is not None else '—'} horas.\n",
          "| Análise | Horas do plano | Veredicto |", "|---|---|---|",
          f"| AG atual (`minHours`, só constantes) | ≥ {R['min_hours']} | "
          f"{verdict((R['min_hours'], INF), P.limit, lower_only=True)} |"]
    for m, lab in (("nocond", "Intervalos, sem avaliar condições"),
                   ("interval", "Intervalos, com condições (abstract interpretation)"),
                   ("exact", "Avaliação exata (ciclos desenrolados por UC)")):
        h = R["interp"][m].hours
        r.append(f"| {lab} | {fmt_iv(h)} | {verdict(h, P.limit)} |")
    ex = R["interp"]["exact"]
    r.append("")
    if ex.per_uc:
        r.append("Plano efetivo (avaliação exata): " + ", ".join(f"{k}: {v} h" for k, v in ex.per_uc.items()) + "\n")
    if R["conds"]:
        r += ["| Condição | Intervalos (T = sempre verdadeira, F = sempre falsa, ? = depende) | "
              "Valores observados na avaliação exata |", "|---|---|---|"]
        for n, ai, ee in R["conds"]:
            r.append(f"| l.{G.nodes[n]['line']} `{G.nodes[n]['text']}` | {'/'.join(sorted(ai)) or '—'} | "
                     f"{'/'.join(sorted(ee)) or 'nunca avaliada'} |")
        r.append("")
    r.append("- Ramos impossíveis provados pela análise de intervalos: " +
             (", ".join(f"{a}→{b}" for a, b in sorted(R["infeasible"])) or "nenhum") +
             "; instruções inalcançáveis: " +
             (", ".join(f"`{G.nodes[n]['text']}` (l.{G.nodes[n]['line']})" for n in sorted(R["unreachable"])) or "nenhuma"))
    r.append("- Ramos nunca executados com estes dados (avaliação exata): " +
             (", ".join(f"l.{G.nodes[n]['line']} ramo {lab}" for n, lab in R["never"]) or "nenhum"))
    r.append("")
    r += ["### Diagnósticos\n", "| Nível | Linha | Código | Mensagem |", "|---|---|---|---|"]
    for lvl, ln, code, msg in diagnostics(P, R):
        r.append(f"| {lvl} | {ln} | {code} | {msg} |")
    r.append("")
    return r
