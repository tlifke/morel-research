# Compile the one-pager.
# Requires: latexmk + pdflatex (TeX Live / MacTeX).

TEX_SRC := one-pager.tex
PDF     := $(TEX_SRC:.tex=.pdf)

.PHONY: all clean watch

all: $(PDF)

$(PDF): $(TEX_SRC)
	latexmk -pdf -interaction=nonstopmode $(TEX_SRC)

watch:
	latexmk -pdf -pvc -interaction=nonstopmode $(TEX_SRC)

clean:
	latexmk -C
