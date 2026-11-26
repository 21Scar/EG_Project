"""
Transformações de programas StudyLang.

  * pretty(tree)            árvore -> código fonte (inverso do parser: parse(pretty(t)) == t)
  * optimize(source)        reescrita que preserva o significado, até ao ponto fixo:
                              1. propagação e dobragem de constantes (intervalos singulares)
                              2. simplificação de condições e eliminação de ramos impossíveis
                              3. eliminação de código sem efeito (fora de todas as fatias do PDG)
  * flatten(source)         avaliação parcial: desenrola os ciclos e produz um plano só com
                            STUDY "UC" FOR n HOURS (opcionalmente agregado por UC)
  * export(source, fmt)     tradução do plano efetivo para Markdown, CSV ou JSON
  * meaning(source)         significado de um plano: a sequência de sessões (UC, horas)

O significado de um plano é a sequência de sessões de estudo que ele produz. Uma
transformação está correta se o programa transformado for válido (AG sem erros) e tiver
o mesmo significado (ou, na versão agregada, as mesmas horas por UC).
"""
import json

from lark import Token, Tree

from parte1 import verificador as cs
from parte2 import analise_estatica as analise
from parte2 import representacoes_intermedias as ir

IND = "    "


# --------------------------------------------------------------------------
# Pretty-printer
# --------------------------------------------------------------------------
def pretty(tree):
    name, level, *rest = tree.children
    out = [f"STUDENT {name} LEVEL {level.data.upper()}", ""]
    prev = None
    for d in rest[:-1]:
        if prev is not None and d.data != prev:
            out.append("")
        prev = d.data
        if d.data == "uc_decl":
            parts = " ".join(f"{c.children[0]} {c.children[1]}" for c in d.children[1:] if isinstance(c, Tree))
            out.append(f"UC {d.children[0]} {{ {parts} }}")
        elif d.data == "resource_decl":
            out.append(f"RESOURCE TIME {d.children[0]} HOURS")
        else:
            out.append(f"VAR {d.children[0]} = {ir.src(d.children[1])}")
    if rest[:-1]:
        out.append("")
    out.append("PLAN " + _block(rest[-1].children[0], 0))
    return "\n".join(out) + "\n"


def _block(b, ind):
    if not b.children:
        return "{ }"
    lines = [IND * (ind + 1) + _stmt(s, ind + 1) for s in b.children]
    return "{\n" + "\n".join(lines) + "\n" + IND * ind + "}"


def _stmt(s, ind):
    d = s.data
    if d == "var_decl":
        return f"VAR {s.children[0]} = {ir.src(s.children[1])}"
    if d == "assign_stmt":
        return f"{s.children[0]} = {ir.src(s.children[1])}"
    if d == "study_stmt":
        return f"STUDY {s.children[0]} FOR {ir.src(s.children[1])} HOURS"
    if d == "if_stmt":
        txt = f"IF ( {ir.src(s.children[0])} ) {_block(s.children[1], ind)}"
        if len(s.children) == 3:
            p = s.children[2].children[0]
            txt += " ELSE " + (_stmt(p, ind) if p.data == "if_stmt" else _block(p, ind))
        return txt
    it, lst, b = s.children
    return f"FOR EACH {it} IN [ {', '.join(str(x) for x in lst.children)} ] {_block(b, ind)}"


# --------------------------------------------------------------------------
# Significado e equivalência
# --------------------------------------------------------------------------
def meaning(source):
    """Sequência de sessões (UC, horas) produzida pelo plano (avaliação exata)."""
    P = ir.Program("p", source)
    if not P.valid:
        raise ValueError(f"programa com erros semânticos: {P.errors}")
    return analise.exact(P).trace


def hours_per_uc(trace):
    out = {}
    for uc, h in trace:
        out[uc] = out.get(uc, 0) + h
    return out


# --------------------------------------------------------------------------
# Otimização
# --------------------------------------------------------------------------
def T(data, children, like=None):
    """Novo nó que herda a posição (linha) do nó original `like`."""
    return Tree(data, children, meta=like.meta if like is not None else None)


def _lit(v, like=None):
    num = T("num", [Token("INT", str(abs(v)))], like)
    return num if v >= 0 else T("neg", [num], like)


def _is_lit(e):
    return e.data == "num" or (e.data == "neg" and e.children[0].data == "num")


def _fold_pass(P, log):
    """Passo 1+2: propagação/dobragem de constantes e eliminação de ramos (via intervalos)."""
    I = analise.Interp(P, "interval").run()

    def fold(e):
        v = I.expr_vals.get(id(e))
        if v is not None and v[0] == v[1] and abs(v[0]) != analise.INF and not _is_lit(e):
            log.append(f"l.{ir.line_of(e)}: `{ir.src(e)}` → {v[0]} (constante)")
            return _lit(v[0], e)
        if e.data in ir.OPS:
            return T(e.data, [fold(e.children[0]), fold(e.children[1])], e)
        if e.data == "neg":
            return T("neg", [fold(e.children[0])], e)
        return e

    def cond(c):
        """Devolve 'T', 'F' ou a condição simplificada."""
        o = I.cond_vals.get(id(c))
        if o in ({"T"}, {"F"}):
            return next(iter(o))
        d = c.data
        if d == "compare":
            return T("compare", [fold(c.children[0]), c.children[1], fold(c.children[2])], c)
        if d == "not_":
            x = cond(c.children[0])
            return {"T": "F", "F": "T"}[x] if isinstance(x, str) else T("not_", [x], c)
        x, y = cond(c.children[0]), cond(c.children[1])
        if d == "and_":
            if "F" in (x, y):
                return "F"
            if x == "T" or y == "T":
                kept = y if x == "T" else x
                log.append(f"l.{ir.line_of(c)}: `{ir.src(c)}` → `{kept if isinstance(kept, str) else ir.src(kept)}`"
                           " (parte sempre verdadeira)")
                return kept
            return T("and_", [x, y], c)
        if "T" in (x, y):
            return "T"
        if x == "F" or y == "F":
            kept = y if x == "F" else x
            log.append(f"l.{ir.line_of(c)}: `{ir.src(c)}` → `{kept if isinstance(kept, str) else ir.src(kept)}`"
                       " (parte sempre falsa)")
            return kept
        return T("or_", [x, y], c)

    def inline_ok(stmts):
        # Colocar um ramo no bloco exterior só é seguro se não declarar nomes (âmbitos).
        return not any(s.data == "var_decl" for s in stmts)

    def block(stmts):
        out = []
        for s in stmts:
            out += stmt(s)
        return out

    def ifs(s):
        c = cond(s.children[0])
        line = s.meta.line
        then = block(s.children[1].children)
        else_node = s.children[2].children[0] if len(s.children) == 3 else None

        def else_stmts():
            if else_node is None:
                return None
            return ifs(else_node) if else_node.data == "if_stmt" else block(else_node.children)

        if c == "T":
            if inline_ok(then):
                log.append(f"l.{line}: condição sempre verdadeira, o IF é substituído pelo ramo V")
                return then
            log.append(f"l.{line}: condição sempre verdadeira, o ramo ELSE é removido")
            return [T("if_stmt", [s.children[0], T("block", then, s.children[1])], s)]
        if c == "F":
            e = else_stmts()
            if e is None:
                log.append(f"l.{line}: condição sempre falsa sem ELSE, o IF é removido")
                return []
            if else_node.data == "if_stmt" or inline_ok(e):
                log.append(f"l.{line}: condição sempre falsa, o IF é substituído pelo ramo ELSE")
                return e
            log.append(f"l.{line}: condição sempre falsa, o ramo V fica vazio")
            return [T("if_stmt", [s.children[0], T("block", [], s.children[1]),
                                  T("else_part", [T("block", e, else_node)], s.children[2])], s)]
        kids = [c, T("block", then, s.children[1])]
        if else_node is not None:
            e = else_stmts()
            if else_node.data == "if_stmt":
                if len(e) == 1 and e[0].data == "if_stmt":
                    kids.append(T("else_part", [e[0]], s.children[2]))
                elif e:
                    kids.append(T("else_part", [T("block", e, else_node)], s.children[2]))
            else:
                kids.append(T("else_part", [T("block", e, else_node)], s.children[2]))
        return [T("if_stmt", kids, s)]

    def stmt(s):
        d = s.data
        if d == "if_stmt":
            return ifs(s)
        if d == "foreach_stmt":
            it, lst, b = s.children
            return [T("foreach_stmt", [it, lst, T("block", block(b.children), b)], s)]
        if d in ("var_decl", "assign_stmt", "study_stmt"):
            return [T(d, [s.children[0], fold(s.children[1])], s)]
        return [s]

    _name, level, *rest = P.tree.children
    decls = [T("var_decl", [d.children[0], fold(d.children[1])], d) if d.data == "var_decl" else d
             for d in rest[:-1]]
    plan = T("plan", [T("block", block(rest[-1].children[0].children), rest[-1].children[0])], rest[-1])
    return T("start", [_name, level] + decls + [plan], P.tree)


def _dce_pass(P, log):
    """Passo 3: remove declarações, atribuições, IF e FOR EACH fora de todas as fatias do PDG.
    Um IF ou FOR EACH fora das fatias não contém nenhum STUDY nem nada de que um STUDY dependa."""
    R = analise.analyse(P)
    relevant = R["relevant"]
    # Uma declaração cujo valor nunca é lido continua necessária se a variável for usada
    # ou atribuída por uma instrução que fica (o nome tem de continuar declarado: P5).
    needed = set()
    for n in relevant:
        needed |= P.cfg.nodes[n]["uses"] | set(P.cfg.nodes[n]["defs"])

    def keep(s):
        if s.data == "study_stmt":
            return True
        ok = P.node_of.get(id(s)) in relevant or (s.data == "var_decl" and P.ref[id(s.children[0])] in needed)
        if not ok:
            log.append(f"l.{s.meta.line}: removida instrução sem efeito no plano: "
                       f"`{P.cfg.nodes[P.node_of[id(s)]]['text']}`")
        return ok

    def block(stmts):
        out = []
        for s in stmts:
            if keep(s):
                out.append(rebuild(s))
        return out

    def rebuild(s):
        d = s.data
        if d == "foreach_stmt":
            it, lst, b = s.children
            return T(d, [it, lst, T("block", block(b.children), b)], s)
        if d == "if_stmt":
            kids = [s.children[0], T("block", block(s.children[1].children), s.children[1])]
            if len(s.children) == 3:
                p = s.children[2].children[0]
                if p.data == "if_stmt":
                    if keep(p):
                        kids.append(T("else_part", [rebuild(p)], s.children[2]))
                else:
                    kids.append(T("else_part", [T("block", block(p.children), p)], s.children[2]))
            return T(d, kids, s)
        return s

    _name, level, *rest = P.tree.children
    decls = [d for d in rest[:-1] if d.data != "var_decl" or keep(d)]
    plan = T("plan", [T("block", block(rest[-1].children[0].children), rest[-1].children[0])], rest[-1])
    return T("start", [_name, level] + decls + [plan], P.tree)


def optimize(source, max_rounds=10):
    """Aplica os passos até ao ponto fixo. Devolve (código, registo das alterações, nº de rondas)."""
    P = ir.Program("original", source)
    if not P.valid:
        raise ValueError(f"programa com erros semânticos: {P.errors}")
    # As árvores reescritas guardam as posições do original, por isso o registo indica
    # sempre linhas do ficheiro do utilizador.
    tree, current = P.tree, pretty(P.tree)
    log, rounds = [], 0
    for rounds in range(1, max_rounds + 1):
        changed = False
        for step in (_fold_pass, _dce_pass):
            n = len(log)
            new_tree = step(ir.Program("passo", None, tree=tree), log)
            new = pretty(new_tree)
            if new != current:
                changed, tree, current = True, new_tree, new
            elif len(log) > n:          # alterações registadas mas sem efeito no texto
                del log[n:]
        if not changed:
            break
    return current, log, rounds


# --------------------------------------------------------------------------
# Planificação (avaliação parcial / desenrolamento)
# --------------------------------------------------------------------------
def flatten(source, aggregate=False):
    """Plano equivalente sem variáveis, ciclos nem condições."""
    P = ir.Program("original", source)
    if not P.valid:
        raise ValueError(f"programa com erros semânticos: {P.errors}")
    ex = analise.exact(P)
    if ex.div_zero:
        raise ValueError("o plano tem uma divisão por zero em tempo de execução")
    sessions = list(hours_per_uc(ex.trace).items()) if aggregate else ex.trace
    _name, level, *rest = P.tree.children
    decls = [d for d in rest[:-1] if d.data != "var_decl"]
    plan = Tree("plan", [Tree("block", [
        Tree("study_stmt", [Token("STRING", f'"{uc}"'), _lit(h)]) for uc, h in sessions])])
    return pretty(Tree("start", [_name, level] + decls + [plan]))


# --------------------------------------------------------------------------
# Exportação do plano efetivo
# --------------------------------------------------------------------------
def plan_table(source):
    P = ir.Program("original", source)
    if not P.valid:
        raise ValueError(f"programa com erros semânticos: {P.errors}")
    ex = analise.exact(P)
    per = hours_per_uc(ex.trace)
    total = sum(per.values())
    rows = []
    for uc, a in P.ucs.items():
        h = per.get(uc, 0)
        rows.append({
            "uc": uc, "creditos": a["CREDITS"], "dificuldade": a["DIFFICULTY"], "horas": h,
            "sessoes": sum(1 for u, _ in ex.trace if u == uc),
            "percentagem_do_recurso": round(100 * h / P.limit, 1) if P.limit else None,
            "horas_por_credito": round(h / a["CREDITS"], 2) if a["CREDITS"] else None,
        })
    return {"estudante": P.student, "nivel": P.level, "recurso_horas": P.limit, "total_horas": total,
            "cumpre_recurso": None if P.limit is None else total <= P.limit, "ucs": rows,
            "sessoes": [{"uc": u, "horas": h} for u, h in ex.trace]}


def export(source, fmt="md"):
    t = plan_table(source)
    if fmt == "json":
        return json.dumps(t, ensure_ascii=False, indent=2)
    cols = ["uc", "creditos", "dificuldade", "sessoes", "horas", "percentagem_do_recurso", "horas_por_credito"]
    if fmt == "csv":
        lines = [";".join(cols)]
        for r in t["ucs"]:
            lines.append(";".join("" if r[c] is None else str(r[c]) for c in cols))
        return "\n".join(lines) + "\n"
    head = ["UC", "Créditos", "Dificuldade", "Sessões", "Horas", "% do recurso", "Horas/crédito"]
    md = [f"# Plano de estudo de {t['estudante']} ({t['nivel']})", "",
          f"Total: **{t['total_horas']} h**" + (f" de {t['recurso_horas']} h disponíveis "
                                                f"({'cumpre' if t['cumpre_recurso'] else 'EXCEDE'})"
                                                if t["recurso_horas"] is not None else ""), "",
          "| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for r in t["ucs"]:
        md.append("| " + " | ".join("—" if r[c] is None else str(r[c]) for c in cols) + " |")
    return "\n".join(md) + "\n"
