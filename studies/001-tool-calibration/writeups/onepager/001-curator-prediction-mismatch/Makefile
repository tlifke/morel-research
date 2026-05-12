# Compile the one-pager.
# Requires: latexmk + xelatex (TeX Live / MacTeX). xelatex is needed for
# the fontspec/brand-font setup in morel.sty.
#
# Install on macOS:        brew install --cask mactex-no-gui
# Install on Debian/Ubuntu: sudo apt install texlive-xetex latexmk \
#                                            texlive-fonts-extra

TEX_SRC := one-pager.tex
PDF     := $(TEX_SRC:.tex=.pdf)

# Reach the repo-level brand package at one-pagers/morel.sty.
# Trailing colon keeps the default TEXINPUTS search path intact.
REPO_ROOT := $(realpath ../../../../..)
export TEXINPUTS := $(REPO_ROOT)/one-pagers/:

.PHONY: all clean watch

all: $(PDF)

$(PDF): $(TEX_SRC) $(REPO_ROOT)/one-pagers/morel.sty
	latexmk -xelatex -interaction=nonstopmode $(TEX_SRC)

watch:
	latexmk -xelatex -pvc -interaction=nonstopmode $(TEX_SRC)

clean:
	latexmk -C
