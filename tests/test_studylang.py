"""
Testes da toolchain StudyLang:  python -m unittest discover -s tests -v

  * exemplos: resultados esperados do verificador, das análises e das transformações;
  * propriedades sobre programas válidos gerados aleatoriamente (semente fixa):
      - pretty-printer: parse(pretty(t)) == t
      - otimização e planificação preservam o significado (sequência de sessões)
      - otimização é idempotente e nunca aumenta o número de instruções
      - análises sólidas: minHours (AG) ≤ horas exatas ∈ intervalos
"""
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import analise  # noqa: E402
import check_studylang as cs  # noqa: E402
import ir  # noqa: E402
import transformacoes as T  # noqa: E402
import studylang  # noqa: E402

EX = ROOT / "exemplos"


def ex(name):
    return (EX / name).read_text(encoding="utf-8")


def n_stmts(source):
    return sum(1 for l in source.splitlines() if l.strip().split(" ")[0] in ("VAR", "STUDY", "IF", "FOR")
               or " = " in l and not l.strip().startswith(("UC", "VAR")))


# --------------------------------------------------------------------------
# Gerador de programas aleatórios
# --------------------------------------------------------------------------
class Gen:
    def __init__(self, rng):
        self.r = rng

    def program(self):
        r = self.r
        self.uni = r.random() < 0.5
        self.ucs = [f"UC{i}" for i in range(r.randint(1, 4))]
        lines = [f"STUDENT Teste LEVEL {'UNIVERSITY' if self.uni else 'SECONDARY'}"]
        for u in self.ucs:
            cr = f"CREDITS {r.randint(1, 9)} " if self.uni else ""
            lines.append(f'UC "{u}" {{ {cr}DIFFICULTY {r.randint(1, 5)} }}')
        self.scopes = [{}]
        for _ in range(r.randint(0, 2)):
            lines.append(self.var_decl())
        lines.append("PLAN " + self.block(0))
        return "\n".join(lines) + "\n"

    def visible(self, kind):
        seen = {}
        for s in self.scopes:
            seen.update(s)
        return [n for n, k in seen.items() if k == kind]

    def expr(self, d=0):
        r = self.r
        opts = ["int"] + (["var"] if self.visible("var") else []) + (["attr"] if self.visible("iter") else [])
        if d < 2:
            opts += ["bin", "bin"]
        k = r.choice(opts)
        if k == "int":
            return str(r.randint(0, 6))
        if k == "var":
            return r.choice(self.visible("var"))
        if k == "attr":
            a = r.choice(["DIFFICULTY", "CREDITS"] if self.uni else ["DIFFICULTY"])
            return f"{r.choice(self.visible('iter'))}.{a}"
        op = r.choice(["+", "+", "-", "*", "/"])
        rhs = str(r.randint(1, 3)) if op == "/" else self.expr(d + 1)   # divisor sempre positivo
        return f"({self.expr(d + 1)} {op} {rhs})"

    def cond(self, d=0):
        r = self.r
        k = r.random()
        if d < 1 and k < 0.2:
            return f"{self.cond(d + 1)} {r.choice(['AND', 'OR'])} {self.cond(d + 1)}"
        if d < 1 and k < 0.3:
            return f"NOT {self.expr()} {r.choice(['<', '<=', '>', '>=', '==', '!='])} {self.expr()}"
        return f"{self.expr()} {r.choice(['<', '<=', '>', '>=', '==', '!='])} {self.expr()}"

    def var_decl(self):
        free = [n for n in "abchxy" if n not in self.scopes[-1]]
        name = self.r.choice(free)
        e = self.expr()
        self.scopes[-1][name] = "var"
        return f"VAR {name} = {e}"

    def block(self, depth):
        self.scopes.append({})
        stmts = [self.stmt(depth) for _ in range(self.r.randint(0 if depth else 1, 4))]
        self.scopes.pop()
        ind = "    " * (depth + 1)
        return "{\n" + "".join(f"{ind}{s}\n" for s in stmts) + "    " * depth + "}"

    def stmt(self, depth):
        r = self.r
        opts = ["var", "study", "study"]
        if self.visible("var"):
            opts.append("assign")
        if depth < 3:
            opts += ["if", "for"]
        k = r.choice(opts)
        if k == "var":
            return self.var_decl()
        if k == "assign":
            return f"{r.choice(self.visible('var'))} = {self.expr()}"
        if k == "study":
            its = self.visible("iter")
            target = r.choice(its) if its and r.random() < 0.6 else f'"{r.choice(self.ucs)}"'
            return f"STUDY {target} FOR {self.expr()} + 1 HOURS"
        if k == "if":
            s = f"IF ( {self.cond()} ) {self.block(depth + 1)}"
            if r.random() < 0.6:
                s += f" ELSE {self.block(depth + 1)}"
            return s
        it = r.choice([n for n in "uvw" if n not in self.visible("iter")] or ["u"])
        lst = r.sample(self.ucs, r.randint(1, len(self.ucs)))
        self.scopes.append({it: "iter"})
        body = self.block(depth + 1)
        self.scopes.pop()
        return f"FOR EACH {it} IN [ {', '.join(chr(34) + u + chr(34) for u in lst)} ] {body}"


def random_programs(n, seed=2627):
    rng, out, tries = random.Random(seed), [], 0
    while len(out) < n and tries < 50 * n:
        tries += 1
        s = Gen(rng).program()
        P = ir.Program("aleatorio", s)
        if not P.valid:
            continue
        trace = analise.exact(P).trace
        if trace and all(h > 0 for _, h in trace) and len(trace) <= 200:
            out.append(s)
    return out


RANDOM = random_programs(150)


# --------------------------------------------------------------------------
# Exemplos
# --------------------------------------------------------------------------
class TestExemplos(unittest.TestCase):
    def test_verificador_parte1(self):
        self.assertEqual(cs.check(cs.parser.parse(ex("ex1_universitario.study"))), [])
        self.assertEqual(cs.check(cs.parser.parse(ex("ex2_secundario.study"))), [])
        self.assertEqual(len(cs.check(cs.parser.parse(ex("ex3_erros_secundario.study")))), 10)
        self.assertEqual(len(cs.check(cs.parser.parse(ex("ex4_erros_universitario.study")))), 3)

    def test_erro_sintatico_indica_esperado(self):
        with self.assertRaises(studylang.SyntaxProblem) as c:
            studylang.load(EX / "ex5_erro_sintatico.study")
        self.assertIn("esperado: LEVEL", str(c.exception))

    def test_horas(self):
        for f, exact, interval, mh in (("ex1_universitario.study", 29, (9, 39), 3),
                                       ("ex2_secundario.study", 21, (12, 27), 0),
                                       ("ex7_analise.study", 14, (6, 22), 0)):
            P = ir.Program(f, ex(f))
            R = analise.analyse(P)
            self.assertEqual(R["interp"]["exact"].hours, (exact, exact), f)
            self.assertEqual(R["interp"]["interval"].hours, interval, f)
            self.assertEqual(R["min_hours"], mh, f)

    def test_ex2_excede_recurso(self):
        P = ir.Program("ex2", ex("ex2_secundario.study"))
        codes = [d[2] for d in analise.diagnostics(P) if d[0] == "erro"]
        self.assertEqual(codes, ["HORAS"])

    def test_ex7_ramo_inalcancavel_e_codigo_morto(self):
        P = ir.Program("ex7", ex("ex7_analise.study"))
        codes = {d[2] for d in analise.diagnostics(P)}
        self.assertTrue({"COND_CONST", "INALCANCAVEL", "DEF_MORTA", "SEM_EFEITO"} <= codes)

    def test_ambitos_evitam_dependencia_falsa(self):
        P = ir.Program("ex2", ex("ex2_secundario.study"))
        self.assertEqual(len(ir.dependencies(P)["false"]), 1)

    def test_otimizacao_ex7(self):
        new, log, _ = T.optimize(ex("ex7_analise.study"))
        self.assertNotIn("IF (", new)
        self.assertNotIn("total", new)
        self.assertIn("STUDY u FOR h + 1 HOURS", new)
        self.assertEqual(T.meaning(new), T.meaning(ex("ex7_analise.study")))
        self.assertTrue(any(l.startswith("l.15:") for l in log))   # linhas do ficheiro original

    def test_planificar_torna_p11_exata(self):
        flat = T.flatten(ex("ex2_secundario.study"), aggregate=True)
        P = ir.Program("flat", flat)
        self.assertTrue(any("excedem RESOURCE TIME" in m for _, m in P.errors))

    def test_exportar(self):
        t = T.plan_table(ex("ex1_universitario.study"))
        self.assertEqual(t["total_horas"], 29)
        self.assertTrue(t["cumpre_recurso"])


# --------------------------------------------------------------------------
# Propriedades sobre programas aleatórios
# --------------------------------------------------------------------------
class TestPropriedades(unittest.TestCase):
    def test_ha_programas_suficientes(self):
        self.assertGreaterEqual(len(RANDOM), 150)

    def test_pretty_printer_inverso_do_parser(self):
        for s in RANDOM + [ex("ex1_universitario.study"), ex("ex2_secundario.study"), ex("ex7_analise.study")]:
            t = cs.parser.parse(s)
            p = T.pretty(t)
            self.assertEqual(cs.parser.parse(p), t, s)
            self.assertEqual(T.pretty(cs.parser.parse(p)), p)

    def test_otimizacao_preserva_significado(self):
        for s in RANDOM:
            new, _, _ = T.optimize(s)
            self.assertTrue(ir.Program("o", new).valid, new)
            self.assertEqual(T.meaning(new), T.meaning(s), s)
            self.assertLessEqual(n_stmts(new), n_stmts(T.pretty(cs.parser.parse(s))), s)

    def test_otimizacao_idempotente(self):
        for s in RANDOM[:60]:
            once, _, _ = T.optimize(s)
            twice, log, _ = T.optimize(once)
            self.assertEqual(once, twice, s)
            self.assertEqual(log, [])

    def test_planificacao_preserva_significado(self):
        for s in RANDOM:
            self.assertEqual(T.meaning(T.flatten(s)), T.meaning(s), s)
            agg = T.meaning(T.flatten(s, aggregate=True))
            self.assertEqual(T.hours_per_uc(agg), T.hours_per_uc(T.meaning(s)), s)

    def test_analises_solidas(self):
        for s in RANDOM:
            P = ir.Program("a", s)
            h = analise.exact(P).hours[0]
            for mode in ("interval", "nocond"):
                lo, hi = analise.Interp(P, mode).run().hours
                self.assertTrue(lo <= h <= hi, (mode, s))
            self.assertLessEqual(analise.ag_min_hours(P), h, s)

    def test_ag_l_atribuida_nos_aleatorios(self):
        import grafos
        for s in RANDOM[:40]:
            g, root = grafos.ag_instance(cs.parser.parse(s))
            self.assertEqual(grafos.check_l_attributed(g), [])
            self.assertEqual(grafos.single_pass_order(g, root), [])


if __name__ == "__main__":
    unittest.main()
