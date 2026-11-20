"""
Verificação da StudyLang: parse com Lark + avaliação das regras da gramática
de atributos (env herdado, errors/type/const/val/minHours sintetizados).
Uso: python check_studylang.py
"""
from pathlib import Path
from lark import Lark, Tree, Token
from lark.exceptions import UnexpectedInput

HERE = Path(__file__).parent
parser = Lark(
    (HERE / "studylang.lark").read_text(encoding="utf-8"),
    parser="lalr",
    lexer="basic",            # palavras reservadas realmente reservadas (o contextual aceitava VAR STUDY = 1)
    propagate_positions=True,
)

# --------------------------------------------------------------------------
# Ambiente: pilha de âmbitos + nível do estudante
# --------------------------------------------------------------------------
class Env:
    def __init__(self, level, scopes=None):
        self.level = level                      # 'uni' | 'sec'
        self.scopes = scopes or [{}]

    def enter(self):
        return Env(self.level, [dict(s) for s in self.scopes] + [{}])

    def add(self, key, typ):
        sc = [dict(s) for s in self.scopes]
        sc[-1][key] = typ
        return Env(self.level, sc)

    def lookup(self, key):
        for s in reversed(self.scopes):
            if key in s:
                return s[key]
        return None

    def in_current(self, key):
        return key in self.scopes[-1]


def ln(x):
    return x.line if isinstance(x, Token) else x.meta.line


def uc(tok):          # chave do espaço de nomes das UCs
    return ("uc", str(tok)[1:-1])


def idk(tok):         # chave do espaço de nomes de variáveis/iteradores
    return ("id", str(tok))


# --------------------------------------------------------------------------
# Expressões: devolve (type, const, val, errors)
# --------------------------------------------------------------------------
def expr(n, env):
    d = n.data
    if d == "num":
        return "int", True, int(n.children[0]), []
    if d == "var":
        t = env.lookup(idk(n.children[0]))
        if t is None:
            return "err", False, 0, [(ln(n), f"'{n.children[0]}' não declarado")]
        if t != "var":
            return "err", False, 0, [(ln(n), f"'{n.children[0]}' não é numérico")]
        return "int", False, 0, []
    if d == "attr":
        name, attr = n.children[0], n.children[1].children[0]
        t = env.lookup(idk(name))
        errs = []
        if t != "iter":
            errs.append((ln(n), f"'{name}' não é iterador de UC (não tem {attr})"))
        elif attr.type == "CREDITS" and env.level == "sec":
            errs.append((ln(n), "CREDITS não existe no nível SECONDARY"))
        return ("int" if not errs else "err"), False, 0, errs
    if d == "neg":
        t, c, v, e = expr(n.children[0], env)
        return t, c, -v, e
    # binárias
    t1, c1, v1, e1 = expr(n.children[0], env)
    t2, c2, v2, e2 = expr(n.children[1], env)
    t = "int" if t1 == t2 == "int" else "err"
    errs = e1 + e2
    if d == "div":
        if c2 and v2 == 0:
            errs.append((ln(n), "divisão por zero"))
        const = c1 and c2 and v2 != 0
        val = v1 // v2 if const else 0
        return t, const, val, errs
    ops = {"add": lambda a, b: a + b, "sub": lambda a, b: a - b,
           "mul": lambda a, b: a * b}
    const = c1 and c2
    return t, const, (ops[d](v1, v2) if const else 0), errs


def cond(n, env):
    d = n.data
    if d == "compare":
        t1, _, _, e1 = expr(n.children[0], env)
        t2, _, _, e2 = expr(n.children[2], env)
        errs = e1 + e2
        if t1 != "int" or t2 != "int":
            errs.append((ln(n), "tipo: comparação exige inteiros"))
        return errs
    return [e for c in n.children for e in cond(c, env)]


# --------------------------------------------------------------------------
# Instruções: devolve (env_out, errors, minHours)
# --------------------------------------------------------------------------
def check_hours(e, env):
    t, c, v, errs = expr(e, env)
    if t != "int" and not errs:
        errs.append((ln(e), "tipo: horas têm de ser inteiras"))
    if c and v <= 0:
        errs.append((ln(e), "horas têm de ser positivas"))
    return (v if c and v > 0 else 0), errs


def stmt(n, env):
    d = n.data
    if d == "var_decl":
        return var_decl(n, env)
    if d == "assign_stmt":
        name, e = n.children
        t, _, _, errs = expr(e, env)
        if env.lookup(idk(name)) != "var":
            errs.append((ln(n), f"'{name}' não é uma variável declarada"))
        if t != "int" and not errs:
            errs.append((ln(n), "tipo"))
        return env, errs, 0
    if d == "study_stmt":
        target, e = n.children
        mh, errs = check_hours(e, env)
        if target.type == "STRING":
            if env.lookup(uc(target)) != "uc":
                errs.append((ln(n), f"UC {target} não declarada"))
        elif env.lookup(idk(target)) != "iter":
            errs.append((ln(n), f"'{target}' não é iterador de UC"))
        return env, errs, mh
    if d == "if_stmt":
        errs, mh = if_stmt(n, env)
        return env, errs, mh
    if d == "foreach_stmt":
        errs, mh = foreach(n, env)
        return env, errs, mh
    raise ValueError(d)


def var_decl(n, env):
    name, e = n.children
    t, _, _, errs = expr(e, env)
    if env.in_current(idk(name)):
        errs.append((ln(n), f"redeclaração de '{name}' no mesmo bloco"))
    if t != "int" and not errs:
        errs.append((ln(n), "tipo"))
    return env.add(idk(name), "var"), errs, 0


def block(n, env):
    inner = env.enter()
    errs, mh = [], 0
    for s in n.children:
        inner, e, m = stmt(s, inner)
        errs += e
        mh += m
    return errs, mh


def if_stmt(n, env):
    c, b = n.children[0], n.children[1]
    errs = cond(c, env)
    be, bm = block(b, env)
    errs += be
    em = 0
    if len(n.children) == 3:
        part = n.children[2].children[0]
        ee, em = if_stmt(part, env) if part.data == "if_stmt" else block(part, env)
        errs += ee
    return errs, min(bm, em)


def foreach(n, env):
    it, lst, b = n.children
    errs = []
    for s in lst.children:
        if env.lookup(uc(s)) != "uc":
            errs.append((ln(s), f"UC {s} não declarada"))
    inner = env.enter().add(idk(it), "iter")
    be, bm = block(b, inner)
    return errs + be, len(lst.children) * bm


# --------------------------------------------------------------------------
# Programa
# --------------------------------------------------------------------------
def check(tree):
    _name, level, *rest = tree.children
    env = Env("uni" if level.data == "university" else "sec")
    errs, nres, limit = [], 0, 0
    for d in rest[:-1]:
        if d.data == "uc_decl":
            name = d.children[0]
            has_credits = any(c.data == "credits" for c in d.children[1:] if isinstance(c, Tree))
            if env.lookup(uc(name)) is not None:
                errs.append((ln(d), f"UC {name} repetida"))
            if env.level == "uni" and not has_credits:
                errs.append((ln(d), f"UC {name}: CREDITS obrigatório no nível UNIVERSITY"))
            if env.level == "sec" and has_credits:
                errs.append((ln(d), f"UC {name}: CREDITS não existe no nível SECONDARY"))
            env = env.add(uc(name), "uc")
        elif d.data == "resource_decl":
            if nres >= 1:                   # P2: erro na linha do RESOURCE a mais
                errs.append((ln(d), "mais do que um RESOURCE"))
            else:
                limit = int(d.children[0])
            nres += 1
        else:
            env, e, _ = var_decl(d, env)
            errs += e
    pe, mh = block(rest[-1].children[0], env)
    errs += pe
    if nres == 1 and mh > limit:
        errs.append((ln(rest[-1]), f"horas garantidas ({mh}) excedem RESOURCE TIME ({limit})"))
    return sorted(errs)


def run(title, src):
    print(f"\n=== {title} ===")
    try:
        tree = parser.parse(src)
    except UnexpectedInput as e:
        print(f"ERRO SINTÁTICO (linha {e.line}, col {e.column}): token inesperado")
        return None
    errs = check(tree)
    if not errs:
        print("OK: sintaxe e semântica válidas")
    for line, msg in errs:
        print(f"  linha {line}: {msg}")
    return errs


# --------------------------------------------------------------------------
# Exemplos (em exemplos/*.study, partilhados com as ferramentas da Parte II)
# --------------------------------------------------------------------------
def _ex(name):
    return (HERE / "exemplos" / name).read_text(encoding="utf-8")


EX1_UNI = _ex("ex1_universitario.study")
EX2_SEC = _ex("ex2_secundario.study")
EX3_INVALID_SEC = _ex("ex3_erros_secundario.study")
EX4_INVALID_UNI = _ex("ex4_erros_universitario.study")
SYNTAX_ERR = _ex("ex5_erro_sintatico.study")          # falta LEVEL
KEYWORD_AS_NAME = _ex("ex6_palavra_reservada.study")  # palavra reservada usada como nome

if __name__ == "__main__":
    for t, s in [("Ex1 - universitário (válido)", EX1_UNI),
                 ("Ex2 - secundário (válido)", EX2_SEC),
                 ("Ex3 - secundário (10 erros semânticos)", EX3_INVALID_SEC),
                 ("Ex4 - universitário (erros de nível)", EX4_INVALID_UNI),
                 ("Ex5 - erro sintático (falta LEVEL)", SYNTAX_ERR),
                 ("Ex6 - erro sintático (palavra reservada como nome)", KEYWORD_AS_NAME)]:
        run(t, s)