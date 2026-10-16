# CV pipeline

`_cv/main.tex` is the only source. On every push, GitHub Actions:

1. compiles it to `files/TianyangChen_CV.pdf` (download link),
2. converts it to `_includes/cv-body.html` with `_cv/tex2html.py` (the web page),
3. builds and deploys the Jekyll site.

## Install (one time)

1. Copy `_cv/`, `.githooks/`, `_includes/cv-style.html`, `_pages/cv.html` and
   `.github/workflows/build-site.yml` into the site repo.
2. Delete the old `_pages/cv.md` (same permalink as `cv.html`).
3. Add to `.gitignore`:
   ```
   _includes/cv-body.html
   files/TianyangChen_CV.pdf
   .cv-blocklist
   ```
4. Turn on the local commit guard (once per clone):
   ```
   git config core.hooksPath .githooks
   ```
   and create `.cv-blocklist` with one term per line — names of anything that
   must never appear in the public repo, e.g. unpublished project names.
5. Settings -> Pages -> Build and deployment -> Source: **GitHub Actions**.

## Shelved content

Comment things out as usual and keep them as long as you like:

- `% \item ...` single lines
- `\begin{comment} ... \end{comment}` blocks
- `\iffalse ... \fi` blocks

They are dropped from both the PDF and the web page, and the build prints them
as `info: shelved ...` so you can see what is currently hidden. Uncomment to
bring them back.

Shelved content is still **visible in the public repo** (it is in the .tex).
That is fine for things like old awards. For anything that must stay private,
put its name in `.cv-blocklist`: the pre-commit hook then refuses the commit if
that term appears anywhere in `_cv/main.tex`, comments included. The check runs
before the commit on purpose — a check in GitHub Actions would run only after
the content is already public.

## Updating the CV

Copy `main.tex` from Overleaf over `_cv/main.tex`, commit, push. The site is
updated in about 1-2 minutes.

The build fails on purpose when the source uses a LaTeX command the converter
doesn't know (add a rule to `tex2html.py`, or avoid the command).

## Local preview

```
python3 _cv/tex2html.py _cv/main.tex -o _includes/cv-body.html
bundle exec jekyll serve
```
