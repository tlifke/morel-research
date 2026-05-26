# Compile the one-pager.
# Requires: latexmk + xelatex (needed for fontspec / Morel typography).
# Install on Debian/Ubuntu:   sudo apt install texlive-xetex latexmk
# Install on macOS (brew):    brew install --cask mactex-no-gui

TEX_SRC = one-pager.tex
PDF = $(TEX_SRC:.tex=.pdf)

.PHONY: all clean watch

all: $(PDF)

$(PDF): $(TEX_SRC) refs.bib
	latexmk -xelatex -interaction=nonstopmode $(TEX_SRC)

watch:
	latexmk -xelatex -pvc -interaction=nonstopmode $(TEX_SRC)

clean:
	latexmk -C
