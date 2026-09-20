#!/usr/bin/env python3
"""Migrate the original notebooks, and PROVE nothing was lost."""
from __future__ import annotations
import ast, json, re, sys
from pathlib import Path

REPO="IgnatiusEzeani/spatial-humanities-2026"; REF="sh2026-workshop"
HEADER=(f"!wget -q https://raw.githubusercontent.com/{REPO}/{REF}/workshop/sh2026_setup.py\n\n"
        "import sh2026_setup as sh\nctx = sh.setup()\n\n"
        "# Bound from the shared context: the cells below were written against these.\n"
        "repo_dir = ctx.repo\ndata_dir = ctx.data\n")

PATHS=[('"projects"/"sh2026"/"workshop"','"workshop"'),
       ('"projects" / "sh2026" / "workshop"','"workshop"'),
       ('"projects"/"sh2026"/"demo"','"demo"'),
       ('"projects" / "sh2026" / "demo"','"demo"'),
       ("projects/sh2026/workshop/","workshop/"),
       ("projects/sh2026/demo/","demo/"),
       ("projects/sh2026/docs/","docs/"),
       ("projects/sh2026/","")]

# Only these exact line shapes are bootstrap. Nothing else is touched.
LINE_DROP=re.compile(r"^\s*(?:"
    r"!(?:pip|git|wget|apt)\b"
    r"|%(?:pip|cd)\b"
    r"|import\s+(?:subprocess|sys|os|pathlib|shutil)(?:\s*,|\s*$)"
    r"|from\s+pathlib\s+import\b"
    r"|sys\.path\."
    r"|os\.chdir"
    r"|subprocess\.(?:run|check_call|check_output)"
    r")")

def names_assigned(code:str)->set:
    try: tree=ast.parse(code)
    except SyntaxError: return set()
    out=set()
    for n in ast.walk(tree):
        if isinstance(n,ast.Name) and isinstance(n.ctx,ast.Store): out.add(n.id)
        elif isinstance(n,ast.alias): out.add((n.asname or n.name).split(".")[0])
        elif isinstance(n,(ast.FunctionDef,ast.ClassDef)): out.add(n.name)
    return out

def is_setup(src:str)->bool:
    """Only the bootstrap cell clones the repository.

    A two-marker test ("subprocess.run" plus "pip install") also matched the
    heavyweight-route cells in notebooks 03 and 05, which pip-install
    transformers. Treating those as setup cells stripped the if/else blocks that
    define hf_source and transformer_rows. `git clone` appears in exactly one
    cell per notebook and nowhere else.
    """
    # The clone is written as subprocess.run(["git","clone",...]), so the
    # literal string "git clone" never appears. Match the argument pair.
    return bool(re.search(r'["\']git["\']\s*,\s*["\']clone["\']', src)) \
        or "git clone" in src

def migrate_setup(src:str)->str:
    """Keep every statement that is not bootstrap MACHINERY.

    Filter at STATEMENT level on the ORIGINAL source, which parses. The earlier
    version deleted lines first and then tried to parse the wreckage; the parse
    failed, the fallback returned nothing, and FAST_MODE and json vanished from
    three notebooks while the script reported success.
    """
    BOOT={"subprocess","sys","os","pathlib","shutil","site","importlib"}
    MACHINERY=("git clone","subprocess","pip install","Path.cwd","REPO_URL",
               "BRANCH =","sys.path","os.chdir","exists()")
    kept=[]
    for stmt in _statements(src):
        if not stmt.strip(): continue
        # shared import line: keep the names that are not bootstrap
        m=re.match(r"^import\s+([\w\s,\.]+?)\s*$", stmt.strip())
        if m:
            names=[n.strip() for n in m.group(1).split(",")]
            keep=[n for n in names if n.split(".")[0] not in BOOT]
            if keep: kept.append("import " + ", ".join(keep))
            continue
        if stmt.strip().startswith("from pathlib import"): continue
        if any(x in stmt for x in MACHINERY): continue
        if re.match(r"^\s*repo_dir\s*=", stmt): continue
        kept.append(stmt)
    body="\n".join(kept)
    for a,b in PATHS: body=body.replace(a,b)
    return HEADER + ("\n"+body+"\n" if body.strip() else "")


def _statements(code:str)->list:
    code="\n".join(l for l in code.splitlines() if not l.lstrip().startswith(("!","%")))
    try: tree=ast.parse(code)
    except SyntaxError: return []
    return [ast.get_source_segment(code,n) or "" for n in tree.body]

def run(src_dir:Path,out_dir:Path)->int:
    out_dir.mkdir(parents=True,exist_ok=True)
    print(f"{'notebook':38s} {'setup':>5s} {'paths':>5s} {'lost names':>40s}")
    bad=0
    for f in sorted(src_dir.glob("*.ipynb")):
        nb=json.loads(f.read_text(encoding="utf-8"))
        before=set(); after=set(); nsetup=npaths=0
        for c in nb["cells"]:
            if c["cell_type"]!="code": continue
            src="".join(c["source"])
            before|=names_assigned("\n".join(l for l in src.splitlines()
                                             if not l.lstrip().startswith(("!","%"))))
            new=src
            if is_setup(src):
                new=migrate_setup(src); nsetup+=1
            else:
                for a,b in PATHS:
                    if a in new: new=new.replace(a,b); npaths+=1
                # SHOW_REFERENCE only when it is a real assignment, never inside a string
                new=re.sub(r"(?m)^(SHOW_REFERENCE\s*=\s*)True\s*$",
                           r'\1False  # @param {type:"boolean"}',new)
            after|=names_assigned("\n".join(l for l in new.splitlines()
                                            if not l.lstrip().startswith(("!","%"))))
            c["source"]=new.splitlines(keepends=True)
        for c in nb["cells"]:
            if c["cell_type"]=="markdown":
                t="".join(c["source"])
                for a,b in PATHS: t=t.replace(a,b)
                t=t.replace("projects/sh2026/workshop","workshop")
                t=t.replace("fix/sh2026-demo-release-gates",REF)
                t=t.replace("IgnatiusEzeani/spatio-textual",REPO)
            else:
                t="".join(c["source"])
            # nbformat: every line but the last keeps its newline
            c["source"]=t.splitlines(keepends=True)
        lost=before-after-{"subprocess","sys","os","pathlib","shutil","Path","repo_dir",
                          "cwd","BRANCH","REPO_URL"}
        if lost: bad+=1
        print(f"{f.name:38s} {nsetup:5d} {npaths:5d} {str(sorted(lost)) if lost else 'none':>40s}")
        (out_dir/f.name).write_text(json.dumps(nb,indent=1,ensure_ascii=False),encoding="utf-8")
    return bad

if __name__=="__main__":
    bad=run(Path(sys.argv[1]),Path(sys.argv[2]))
    print(f"\n{bad} notebooks lost names" if bad else "\nno names lost in any notebook")
