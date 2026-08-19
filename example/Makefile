# Example paper using the technical-writing library.

MAIN = main

# Location of the technical-writing library (this repository's root).
AIWRITING = ..

LATEXMK = latexmk
LATEXMK_FLAGS = -pdf -interaction=nonstopmode -halt-on-error

# Let LaTeX find aiwriting.sty in the library's latex/ directory.
# The trailing colon tells TeX to also search its default paths.
export TEXINPUTS := .:$(AIWRITING)/latex:$(TEXINPUTS)

BUILD_DIR = build
IMAGES_DIR = $(BUILD_DIR)/images
DPI = 300

.PHONY: all pdf draft clean distclean watch images

all: pdf

pdf:
	$(LATEXMK) $(LATEXMK_FLAGS) $(MAIN)

# Build with review comments visible. If your latexmk is too old for
# -usepretex, just change main.tex to \usepackage[showreviews]{aiwriting}.
draft:
	$(LATEXMK) $(LATEXMK_FLAGS) -usepretex='\PassOptionsToPackage{showreviews}{aiwriting}' $(MAIN)

watch:
	$(LATEXMK) $(LATEXMK_FLAGS) -pvc $(MAIN)

images: pdf
	@mkdir -p $(IMAGES_DIR)
	pdftoppm -png -r $(DPI) $(MAIN).pdf $(IMAGES_DIR)/page
	@echo "Generated images in $(IMAGES_DIR)/"

clean:
	$(LATEXMK) -c

distclean:
	$(LATEXMK) -C
	rm -f *.bbl *.aiguidelines
	rm -rf $(BUILD_DIR)

# verify / verify-update / verify-list / verify-diff
include $(AIWRITING)/make/aiwriting.mk
