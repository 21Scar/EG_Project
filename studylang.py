"""
studylang: ferramenta de linha de comandos para a StudyLang.

    python studylang.py verificar  FICHEIRO               sintaxe + gramática de atributos (Parte I)
    python studylang.py analisar   FICHEIRO [--md|--json]  análise estática e diagnósticos
    python studylang.py grafos     FICHEIRO [-o PASTA]     AST, CFG, DFG e PDG (DOT + visualizador HTML)
    python studylang.py otimizar   FICHEIRO [-o SAIDA]     propagação de constantes, ramos e código morto
    python studylang.py planificar FICHEIRO [--agregar]    plano desenrolado, só com STUDY constantes
    python studylang.py exportar   FICHEIRO [--formato md|csv|json]
    python studylang.py relatorio  FICHEIRO [-o PASTA]     página HTML com tudo (para demonstração)

Arquitetura (cada componente usa o anterior):
    studylang.lark + check_studylang.py   front-end: parser LALR(1) e gramática de atributos
    ir.py                                 representações intermédias: nomes, CFG, DFG, PDG
    analise.py                            análise estática: intervalos, avaliação exata, diagnósticos
    transformacoes.py                     pretty-printer, otimização, planificação, exportação
    grafos.py                             visualização (DOT e HTML)
    studylang.py                          esta interface
"""
import argparse
import html
import json
import sys
from pathlib import Path

from lark.exceptions import UnexpectedCharacters, UnexpectedInput, UnexpectedToken

import analise
import grafos
import ir
import transformacoes as T

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

LEVEL_MARK = {"erro": "✖", "aviso": "⚠", "info": "ℹ"}

# nomes legíveis para os terminais anónimos do Lark nas mensagens de erro
TERMINAL_NAMES = {"LBRACE": "{", "RBRACE": "}", "LPAR": "(", "RPAR": ")", "LSQB": "[", "RSQB": "]",
                  "COMMA": ",", "EQUAL": "=", "DOT": ".", "PLUS": "+", "MINUS": "-", "STAR": "*",
                  "SLASH": "/", "ID": "identificador", "STRING": "texto entre aspas", "INT": "número",
                  "REL_OP": "operador relacional", "$END": "fim do ficheiro"}


class SyntaxProblem(Exception):
    pass


def load(path):
    p = Path(path)
    source = p.read_text(encoding="utf-8")
    try:
        return ir.Program(p.stem, source)
    except UnexpectedInput as e:
        raise SyntaxProblem(syntax_message(e, source)) from None


def syntax_message(e, source):
    """Mensagem de erro sintático com a linha e os tokens esperados (melhoria da Parte I)."""
    msg = f"erro sintático na linha {e.line}, coluna {e.column}"
    if isinstance(e, UnexpectedToken):
        msg += f": encontrado '{e.token}'"
        exp = sorted(TERMINAL_NAMES.get(t, t) for t in e.expected)
        if exp:
            msg += "; esperado: " + ", ".join(exp)
    elif isinstance(e, UnexpectedCharacters):
        msg += f": carácter inesperado '{source[e.pos_in_stream]}'"
    lines = source.splitlines()
    if 0 < e.line <= len(lines):
        msg += f"\n    {lines[e.line - 1]}\n    {' ' * (e.column - 1)}^"
    return msg


def print_diagnostics(diags):
    for lvl, ln, code, msg in diags:
        print(f"  {LEVEL_MARK[lvl]} {lvl:5} l.{ln:<3} [{code}] {msg}")


# --------------------------------------------------------------------------
# Comandos
# --------------------------------------------------------------------------
def cmd_verificar(a):
    P = load(a.ficheiro)
    if P.valid:
        print(f"{a.ficheiro}: OK, sintaxe e semântica válidas")
        return 0
    print(f"{a.ficheiro}: {len(P.errors)} erro(s) semântico(s)")
    for ln, msg in P.errors:
        print(f"  ✖ l.{ln}: {msg}")
    return 1


def cmd_analisar(a):
    P = load(a.ficheiro)
    if not P.valid:
        print_diagnostics(analise.diagnostics(P))
        print("(a análise de fluxo só é feita sobre programas sem erros semânticos)")
        return 1
    R = analise.analyse(P)
    diags = analise.diagnostics(P, R)
    if a.md:
        print("\n".join(analise.report_md(P, R)))
    elif a.json:
        ex, iv = R["interp"]["exact"], R["interp"]["interval"]
        print(json.dumps({
            "programa": a.ficheiro, "recurso": P.limit, "horas_exatas": ex.hours[0],
            "horas_intervalo": list(iv.hours), "horas_minimas_ag": R["min_hours"],
            "horas_por_uc": dict(ex.per_uc),
            "cfg": {k: R["cfg"][k] for k in ("blocks", "edges", "cyclomatic", "paths", "depth", "max_exec")},
            "dependencias": {"fluxo": len(R["deps"]["du"]), "anti": len(R["deps"]["anti"]),
                             "saida": len(R["deps"]["output"])},
            "diagnosticos": [{"nivel": l, "linha": n, "codigo": c, "mensagem": m} for l, n, c, m in diags],
        }, ensure_ascii=False, indent=2))
    else:
        ex, iv, c = R["interp"]["exact"], R["interp"]["interval"], R["cfg"]
        print(f"{a.ficheiro}: {P.student} ({P.level}), {len(P.ucs)} UC(s), RESOURCE TIME = {P.limit}")
        print(f"  CFG: {c['blocks']} blocos básicos, V(G) = {c['cyclomatic']}, {c['paths']} caminhos, "
              f"aninhamento {c['depth']}, termina em ≤ {c['max_exec']} execuções")
        print(f"  Dependências: {len(R['deps']['du'])} de fluxo, {len(R['deps']['anti'])} anti, "
              f"{len(R['deps']['output'])} de saída")
        print(f"  Horas: AG ≥ {R['min_hours']} | intervalos {analise.fmt_iv(iv.hours)} | "
              f"exatas {analise.fmt_iv(ex.hours)}  ->  {analise.verdict(ex.hours, P.limit)}")
        print("  Por UC: " + ", ".join(f"{k} {v} h" for k, v in ex.per_uc.items()))
        print(f"  Diagnósticos ({len(diags)}):")
        print_diagnostics(diags)
    return 1 if any(d[0] == "erro" for d in diags) else 0


def cmd_grafos(a):
    P = load(a.ficheiro)
    if not P.valid:
        print("o programa tem erros semânticos; corrija-os primeiro (python studylang.py verificar)")
        return 1
    out = Path(a.o or f"grafos_{P.name}")
    grafos.GRAPHS.clear()
    grafos.program_graphs(P, analise.analyse(P), P.name)
    rendered = grafos.write_graphs(out, grafos.GRAPHS)
    grafos.write_viewer(out / "index.html", grafos.GRAPHS, f"StudyLang: grafos de {P.name}")
    print(f"{len(grafos.GRAPHS)} grafos em {out}/ ({'DOT, SVG e PNG' if rendered else 'DOT'}); "
          f"abra {out / 'index.html'} no browser")
    return 0


def _write_or_print(text, out):
    if out:
        Path(out).write_text(text, encoding="utf-8")
        print(f"escrito em {out}")
    else:
        print(text, end="")
        sys.stdout.flush()


def cmd_otimizar(a):
    P = load(a.ficheiro)
    new, log, rounds = T.optimize(P.source)
    same = T.meaning(P.source) == T.meaning(new)
    _write_or_print(new, a.o)
    print(f"\n// {len(log)} alteração(ões) em {rounds} ronda(s); mesmo plano: {'sim' if same else 'NÃO'}",
          file=sys.stderr)
    for line in log:
        print("//   " + line, file=sys.stderr)
    return 0 if same else 2


def cmd_planificar(a):
    P = load(a.ficheiro)
    new = T.flatten(P.source, aggregate=a.agregar)
    _write_or_print(new, a.o)
    after = ir.Program("planificado", new)
    n = sum(1 for line in new.splitlines() if line.strip().startswith("STUDY"))
    # No plano planificado as horas são constantes, por isso a P11 da AG passa a ser exata.
    print(f"\n// plano planificado: {n} sessões; verificação da AG sobre o resultado: "
          + ("OK" if after.valid else "; ".join(m for _, m in after.errors)), file=sys.stderr)
    return 0 if after.valid else 1


def cmd_exportar(a):
    P = load(a.ficheiro)
    _write_or_print(T.export(P.source, a.formato), a.o)
    return 0


def cmd_relatorio(a):
    P = load(a.ficheiro)
    out = Path(a.o or f"relatorio_{P.name}")
    out.mkdir(parents=True, exist_ok=True)
    e = html.escape
    parts = [f"<h2>Programa</h2><p><b>{e(P.student)}</b> ({P.level}), {len(P.ucs)} UC(s), "
             f"RESOURCE TIME = {P.limit}</p><pre>{e(P.source)}</pre>"]
    diags = analise.diagnostics(P)
    rows = "".join(f"<tr><td class='{l}'>{l}</td><td>{n}</td><td>{c}</td><td>{e(m)}</td></tr>"
                   for l, n, c, m in diags)
    parts.append("<h2>Diagnósticos</h2>" + (f"<table><tr><th>Nível</th><th>Linha</th><th>Código</th>"
                                            f"<th>Mensagem</th></tr>{rows}</table>" if diags else "<p>Nenhum.</p>"))
    grafos.GRAPHS.clear()
    if P.valid:
        R = analise.analyse(P)
        ex, iv, ni = R["interp"]["exact"], R["interp"]["interval"], R["interp"]["nocond"]
        parts.append(
            "<h2>Horas do plano</h2><table><tr><th>Análise</th><th>Horas</th><th>Veredicto</th></tr>"
            f"<tr><td>AG (minHours)</td><td>≥ {R['min_hours']}</td><td>"
            f"{analise.verdict((R['min_hours'], analise.INF), P.limit, True)}</td></tr>"
            + "".join(f"<tr><td>{lab}</td><td>{analise.fmt_iv(x.hours)}</td><td>{analise.verdict(x.hours, P.limit)}</td></tr>"
                      for lab, x in (("Intervalos sem condições", ni), ("Intervalos com condições", iv),
                                     ("Avaliação exata", ex)))
            + "</table>")
        parts.append("<h2>Plano efetivo</h2>" + _md_table_html(T.export(P.source, "md")))
        new, log, rounds = T.optimize(P.source)
        flat = T.flatten(P.source, aggregate=True)
        parts.append(
            "<h2>Transformações</h2><div class='cols'>"
            f"<div><h3>Otimizado ({len(log)} alterações)</h3><pre>{e(new)}</pre>"
            f"<p>Mesmo plano que o original: <b>{'sim' if T.meaning(new) == T.meaning(P.source) else 'NÃO'}</b></p>"
            f"<details><summary>Registo</summary><pre>{e(chr(10).join(log))}</pre></details></div>"
            f"<div><h3>Planificado (agregado por UC)</h3><pre>{e(flat)}</pre></div></div>")
        (out / f"{P.name}_otimizado.study").write_text(new, encoding="utf-8")
        (out / f"{P.name}_planificado.study").write_text(flat, encoding="utf-8")
        (out / "analise.md").write_text("\n".join(analise.report_md(P, R)), encoding="utf-8")
        grafos.program_graphs(P, R, P.name)
        grafos.write_graphs(out, grafos.GRAPHS)
    grafos.write_viewer(out / "index.html", grafos.GRAPHS, f"StudyLang: relatório de {P.name}", "".join(parts))
    print(f"relatório em {out / 'index.html'}")
    return 0


def _md_table_html(md):
    out, rows = [], [l for l in md.splitlines() if l.startswith("|")]
    for l in md.splitlines():
        if l.startswith("Total"):
            out.append(f"<p>{html.escape(l).replace('**', '')}</p>")
    cells = [[c.strip() for c in r.strip("|").split("|")] for r in rows if not set(r) <= set("|-")]
    if cells:
        out.append("<table>" + "".join("<tr>" + "".join(f"<{'th' if i == 0 else 'td'}>{html.escape(c)}</{'th' if i == 0 else 'td'}>"
                                                         for c in row) + "</tr>" for i, row in enumerate(cells)) + "</table>")
    return "".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="studylang", description="Ferramentas para a linguagem StudyLang.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("verificar", help="sintaxe e gramática de atributos")
    s.add_argument("ficheiro")
    s = sub.add_parser("analisar", help="análise estática e diagnósticos")
    s.add_argument("ficheiro")
    g = s.add_mutually_exclusive_group()
    g.add_argument("--md", action="store_true", help="relatório completo em Markdown")
    g.add_argument("--json", action="store_true", help="resultado em JSON")
    s = sub.add_parser("grafos", help="AST, CFG, DFG e PDG")
    s.add_argument("ficheiro")
    s.add_argument("-o", help="pasta de saída")
    s = sub.add_parser("otimizar", help="transformação que preserva o plano")
    s.add_argument("ficheiro")
    s.add_argument("-o", help="ficheiro de saída")
    s = sub.add_parser("planificar", help="plano desenrolado, só com STUDY constantes")
    s.add_argument("ficheiro")
    s.add_argument("--agregar", action="store_true", help="uma sessão por UC")
    s.add_argument("-o", help="ficheiro de saída")
    s = sub.add_parser("exportar", help="plano efetivo em Markdown, CSV ou JSON")
    s.add_argument("ficheiro")
    s.add_argument("--formato", choices=["md", "csv", "json"], default="md")
    s.add_argument("-o", help="ficheiro de saída")
    s = sub.add_parser("relatorio", help="página HTML com análise, transformações e grafos")
    s.add_argument("ficheiro")
    s.add_argument("-o", help="pasta de saída")
    a = ap.parse_args(argv)
    try:
        return globals()[f"cmd_{a.cmd}"](a)
    except SyntaxProblem as e:
        print(f"{a.ficheiro}: {e}")
        return 1
    except ValueError as e:
        print(f"{a.ficheiro}: {e}")
        return 1
    except FileNotFoundError:
        print(f"ficheiro não encontrado: {a.ficheiro}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
