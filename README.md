# CV — Christopher D. R. Wyatt

My curriculum vitae, written in LaTeX and built to a PDF automatically by
GitHub Actions ("CV as code").

📄 **Latest PDF:** [cv.pdf](https://chriswyatt1.github.io/cv/cv.pdf)
*(available once the workflow has run on `main` and GitHub Pages is enabled — see below)*

## How it works

- [`cv.tex`](cv.tex) is the single source of truth.
- On every push to `main`, [`.github/workflows/build.yml`](.github/workflows/build.yml)
  compiles it to `cv.pdf` and publishes the PDF to the `gh-pages` branch,
  giving it a stable URL.
- The PDF is also attached to each run as a downloadable build artifact.

## Editing

Edit `cv.tex`, commit, and push. The PDF rebuilds itself.

Each role uses the `\cventry{title}{institution}{dates}{description}` macro,
so adding a new position is a one-line block.

## Building locally (optional)

```sh
latexmk -pdf cv.tex      # produces cv.pdf
# or, without latexmk:
pdflatex cv.tex
```

## One-time GitHub setup

1. Push this repo to `https://github.com/chriswyatt1/cv`.
2. After the first successful Actions run, a `gh-pages` branch is created.
3. In **Settings → Pages**, set the source to the `gh-pages` branch (root).
   The CV is then served at `https://chriswyatt1.github.io/cv/cv.pdf`.
