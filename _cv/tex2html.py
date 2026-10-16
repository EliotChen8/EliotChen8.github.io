#!/usr/bin/env python3
"""tex2html.py — convert Eliot's CV main.tex into an HTML fragment for the website.

Only the macro vocabulary actually used in the CV is supported. Anything
unknown makes the build FAIL (exit 1) instead of silently disappearing.

Commented-out ("shelved") content is fully supported: %-comments,
\\begin{comment}...\\end{comment} and \\iffalse...\\fi are removed from the
output exactly as LaTeX removes them from the PDF, and listed as info so you
can see what is currently shelved.

Usage:
    python3 tex2html.py main.tex -o _includes/cv-body.html
    python3 tex2html.py main.tex --check --blocklist .cv-blocklist

--blocklist FILE  fail if any term in FILE (one per line, case-insensitive,
                  '#' lines ignored) appears ANYWHERE in the source, comments
                  included. Used by the local pre-commit hook so that names of
                  unpublished projects never get committed to the public repo.
--check           validate only, write nothing.
"""
import argparse
import html
import re
import sys

# ---------------------------------------------------------------- vocabulary
DROP_WITH_ARG = {"vspace", "hspace", "qrcode", "vspace*", "hspace*"}  # \cmd[opt]{arg}
DROP_NO_ARG = {"hfill", "raggedleft", "raggedright", "centering", "noindent",
               "par", "newline", "smallskip", "medskip", "bigskip"}
SIZE_CMDS = {"tiny", "scriptsize", "footnotesize", "small", "normalsize",
             "large", "Large", "LARGE", "huge", "Huge"}
SYMBOLS = {"&": "&amp;", "%": "%", "$": "$", "#": "#", "_": "_",
           "{": "{", "}": "}", " ": " ", ",": "\u2009"}
WORD_SYMBOLS = {"textbar": "|", "LaTeX": "LaTeX", "TeX": "TeX",
                "textendash": "\u2013", "textemdash": "\u2014", "ldots": "\u2026",
                "dots": "\u2026", "textasciitilde": "~"}
MATH = {r"\sim": "\u223c", r"\cdot": "\u00b7", r"\times": "\u00d7",
        r"\pm": "\u00b1", r"\approx": "\u2248", r"\geq": "\u2265", r"\leq": "\u2264"}


class TexError(Exception):
    pass


# ---------------------------------------------------------------- preprocessing
def strip_comments(src, warnings):
    """Remove shelved content exactly as LaTeX would; record what was hidden."""
    def kill_block(m):
        body = m.group(1).strip()
        first = body.splitlines()[0][:70] if body else ""
        warnings.append(f"shelved block: {first!r} ...")
        return ""
    src = re.sub(r"\\begin\{comment\}(.*?)\\end\{comment\}", kill_block, src, flags=re.S)
    src = re.sub(r"\\iffalse\b(.*?)\\fi\b", kill_block, src, flags=re.S)

    out = []
    for line in src.splitlines():
        m = re.search(r"(?<!\\)%", line)
        if m:
            hidden = line[m.end():].strip()
            if re.search(r"\\(item|cventry|resumesection)\b", hidden):
                warnings.append(f"shelved line: {hidden[:70]!r}")
            line = line[:m.start()]
            if not line.strip():
                continue          # whole-line comment: drop line completely
        out.append(line)
    return "\n".join(out)


def document_body(src):
    m = re.search(r"\\begin\{document\}(.*)\\end\{document\}", src, flags=re.S)
    if not m:
        raise TexError("no \\begin{document} ... \\end{document}")
    return m.group(1)


# ---------------------------------------------------------------- parser
class Parser:
    def __init__(self, s):
        self.s, self.i = s, 0

    def peek(self, n=1):
        return self.s[self.i:self.i + n]

    def eof(self):
        return self.i >= len(self.s)

    def skip_ws(self):
        while not self.eof() and self.s[self.i] in " \t\n":
            self.i += 1

    def read_group(self, open_="{", close="}"):
        """Return raw text of a balanced group; cursor must be on `open_`."""
        self.skip_ws()
        if self.peek() != open_:
            raise TexError(f"expected '{open_}' at: {self.s[self.i:self.i+40]!r}")
        depth, start = 0, self.i
        while not self.eof():
            c = self.s[self.i]
            if c == "\\":
                self.i += 2
                continue
            if c == open_:
                depth += 1
            elif c == close:
                depth -= 1
                if depth == 0:
                    self.i += 1
                    return self.s[start + 1:self.i - 1]
            self.i += 1
        raise TexError("unbalanced braces")

    def read_optional(self):
        save = self.i
        self.skip_ws()
        if self.peek() == "[":
            return self.read_group("[", "]")
        self.i = save
        return None

    def read_cmd_name(self):
        assert self.peek() == "\\"
        self.i += 1
        m = re.match(r"[A-Za-z]+\*?", self.s[self.i:])
        if m:
            self.i += m.end()
            return m.group(0)
        c = self.s[self.i]
        self.i += 1
        return c


# ---------------------------------------------------------------- inline render
def inline(text):
    """Render inline LaTeX to HTML (no block structures allowed here)."""
    p = Parser(text)
    out = []
    while not p.eof():
        c = p.peek()
        if p.peek(2) == "``":
            out.append("\u201c"); p.i += 2
        elif p.peek(2) == "''":
            out.append("\u201d"); p.i += 2
        elif p.peek(3) == "---":
            out.append("\u2014"); p.i += 3
        elif p.peek(2) == "--":
            out.append("\u2013"); p.i += 2
        elif c == "'":
            out.append("\u2019"); p.i += 1
        elif c == "~":
            out.append("&nbsp;"); p.i += 1
        elif c == "$":
            end = text.index("$", p.i + 1)
            out.append(math(text[p.i + 1:end])); p.i = end + 1
        elif c == "{":
            grp = p.read_group()
            m = re.match(r"\s*\\(" + "|".join(SIZE_CMDS) + r")\b(.*)", grp, flags=re.S)
            if m:
                out.append(f'<span class="cv-{m.group(1).lower()}">{inline(m.group(2))}</span>')
            else:
                out.append(inline(grp))
        elif c == "\\":
            if p.peek(2) == "\\\\":            # line break \\ or \\[len]
                p.i += 2
                p.read_optional()
                out.append("<br>")
                continue
            name = p.read_cmd_name()
            if name in SYMBOLS:
                out.append(SYMBOLS[name])
            elif name in WORD_SYMBOLS:
                if p.peek(2) == "{}":
                    p.i += 2
                out.append(WORD_SYMBOLS[name])
            elif name == "textbf":
                out.append(f"<strong>{inline(p.read_group())}</strong>")
            elif name in ("textit", "emph"):
                out.append(f"<em>{inline(p.read_group())}</em>")
            elif name == "underline":
                out.append(f"<u>{inline(p.read_group())}</u>")
            elif name == "href":
                url = p.read_group()
                label = inline(p.read_group())
                out.append(f'<a href="{html.escape(url, quote=True)}">{label}</a>')
            elif name == "url":
                url = p.read_group()
                out.append(f'<a href="{html.escape(url, quote=True)}">{html.escape(url)}</a>')
            elif name in DROP_WITH_ARG:
                p.read_optional(); p.read_group()
            elif name in DROP_NO_ARG or name in SIZE_CMDS:
                pass
            else:
                raise TexError(f"unsupported command \\{name}")
        elif c in "<>&":
            out.append(html.escape(c)); p.i += 1
        else:
            out.append(c); p.i += 1
    return re.sub(r"\s+", " ", "".join(out)).strip()


def math(expr):
    expr = expr.strip()
    for k, v in MATH.items():
        expr = expr.replace(k, v)
    if "\\" in expr:
        raise TexError(f"unsupported math ${expr}$")
    return html.escape(expr)


# ---------------------------------------------------------------- block render
BLOCK_RE = re.compile(r"\\(resumesection|cventry|begin\{cvlist\}|begin\{minipage\})")


def blocks(text):
    """Render a run of block-level LaTeX into HTML."""
    out, para = [], []

    def flush():
        joined = " ".join(para).strip()
        para.clear()
        for chunk in re.split(r"\n\s*\n", joined):
            if chunk.strip():
                rendered = inline(chunk)
                if rendered:
                    out.append(f"<p>{rendered}</p>")

    p = Parser(text)
    while not p.eof():
        m = BLOCK_RE.search(text, p.i)
        if not m:
            para.append(text[p.i:]); break
        para.append(text[p.i:m.start()])
        p.i = m.start()
        flush()
        kind = m.group(1)
        if kind == "resumesection":
            p.read_cmd_name()
            out.append(("SECTION", inline(p.read_group())))
        elif kind == "cventry":
            p.read_cmd_name()
            a, b, c, d, e = (p.read_group() for _ in range(5))
            out.append(
                '<div class="cv-entry">'
                f'<div class="cv-row"><strong>{inline(a)}</strong><strong>{inline(b)}</strong></div>'
                f'<div class="cv-row cv-sub"><em>{inline(c)}</em><strong>{inline(d)}</strong></div>'
                f'{blocks(e)}</div>')
        elif kind == "begin{cvlist}":
            p.i = m.end()
            end = find_env_end(text, p.i, "cvlist")
            out.append(cvlist(text[p.i:end]))
            p.i = end + len(r"\end{cvlist}")
        elif kind == "begin{minipage}":
            p.i = m.end()
            p.read_optional(); p.read_group()          # [t]{width}
            end = find_env_end(text, p.i, "minipage")
            inner = blocks(text[p.i:end])
            if inner.strip():                         # QR-code-only minipage -> nothing
                out.append(f'<div class="cv-minipage">{inner}</div>')
            p.i = end + len(r"\end{minipage}")
    flush()

    # assemble sections
    html_out, open_sec = [], False
    for item in out:
        if isinstance(item, tuple):
            if open_sec:
                html_out.append("</section>")
            html_out.append(f'<section class="cv-section"><h2>{item[1]}</h2>')
            open_sec = True
        else:
            html_out.append(item)
    if open_sec:
        html_out.append("</section>")
    return "\n".join(html_out)


def find_env_end(text, start, env):
    depth, i = 1, start
    pat = re.compile(r"\\(begin|end)\{" + env + r"\}")
    while True:
        m = pat.search(text, i)
        if not m:
            raise TexError(f"unterminated {env} environment")
        depth += 1 if m.group(1) == "begin" else -1
        if depth == 0:
            return m.start()
        i = m.end()


def cvlist(body):
    items = re.split(r"\\item\b", body)
    if items[0].strip():
        raise TexError(f"text before first \\item in cvlist: {items[0].strip()[:40]!r}")
    lis = []
    for it in items[1:]:
        rendered = inline(it)
        if rendered:                       # empty placeholder \item is skipped
            lis.append(f"<li>{rendered}</li>")
        else:
            WARNINGS.append("empty \\item skipped (it renders as an empty bullet in the PDF)")
    return '<ul class="cv-list">' + "".join(lis) + "</ul>"


WARNINGS = []


def convert(src):
    src = strip_comments(src, WARNINGS)
    body = document_body(src)
    first = body.find(r"\resumesection")
    header, rest = (body[:first], body[first:]) if first > 0 else ("", body)
    parts = []
    if header.strip():
        parts.append(f'<header class="cv-header">{blocks(header)}</header>')
    parts.append(blocks(rest))
    return ('{% raw %}\n<div class="cv-tex">\n' + "\n".join(parts) +
            "\n</div>\n{% endraw %}\n")


def check_blocklist(src, path):
    """Return a list of 'line N: term' hits for blocklisted terms anywhere in src."""
    try:
        terms = [t.strip() for t in open(path, encoding="utf-8")
                 if t.strip() and not t.lstrip().startswith("#")]
    except FileNotFoundError:
        print(f"tex2html: note: blocklist {path} not found, skipping check", file=sys.stderr)
        return []
    hits = []
    for n, line in enumerate(src.splitlines(), 1):
        low = line.lower()
        for t in terms:
            if t.lower() in low:
                hits.append(f"line {n}: contains blocklisted term {t!r}")
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tex")
    ap.add_argument("-o", "--output")
    ap.add_argument("--check", action="store_true", help="validate only")
    ap.add_argument("--blocklist", metavar="FILE")
    args = ap.parse_args()
    if not args.check and not args.output:
        ap.error("-o/--output is required unless --check is given")
    src = open(args.tex, encoding="utf-8").read()

    if args.blocklist:
        hits = check_blocklist(src, args.blocklist)
        if hits:
            for h in hits:
                print(f"tex2html: BLOCKED: {h}", file=sys.stderr)
            print("tex2html: remove these from the file before committing "
                  "(comments count: the .tex itself is public).", file=sys.stderr)
            sys.exit(1)

    try:
        result = convert(src)
    except TexError as e:
        print(f"tex2html: ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    for w in WARNINGS:
        tag = "info" if w.startswith("shelved") else "warning"
        print(f"tex2html: {tag}: {w}", file=sys.stderr)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result)


if __name__ == "__main__":
    main()
