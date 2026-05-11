# Compile the one-pager.
# Requires: latexmk + a TeX distribution (TeX Live, MiKTeX, or MacTeX).
# Install on Debian/Ubuntu:   sudo apt install texlive-latex-extra latexmk
# Install on macOS (brew):    brew install --cask mactex-no-gui

TEX_SRC = one-pager.tex
PDF = $(TEX_SRC:.tex=.pdf)

.PHONY: all clean watch

all: $(PDF)

$(PDF): $(TEX_SRC) refs.bib
	latexmk -pdf -interaction=nonstopmode $(TEX_SRC)

watch:
	latexmk -pdf -pvc -interaction=nonstopmode $(TEX_SRC)

clean:
	latexmk -C
