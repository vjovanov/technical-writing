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

# The draft build uses a separate job name so that it never overwrites the
# print-ready PDF. Sharing one output file would be unsafe: latexmk decides
# what to rebuild from source timestamps and does not know the review-visibility
# option changed, so `make pdf' after `make draft' would report "nothing to do"
# and leave review comments in the file you are about to submit.
DRAFT = $(MAIN)-draft

.PHONY: all pdf draft clean distclean watch images draft-images

all: pdf

# Print-ready build: review comments hidden.
pdf:
	$(LATEXMK) $(LATEXMK_FLAGS) $(MAIN)

# Drafting build: review comments visible, written to $(DRAFT).pdf.
# If your latexmk is too old for -usepretex, set the option in main.tex
# instead: \usepackage[showreviews]{aiwriting}
draft:
	$(LATEXMK) $(LATEXMK_FLAGS) -jobname=$(DRAFT) \
		-usepretex='\PassOptionsToPackage{showreviews}{aiwriting}' $(MAIN)

watch:
	$(LATEXMK) $(LATEXMK_FLAGS) -pvc $(MAIN)

# Page images of the print-ready PDF (requires pdftoppm from poppler-utils).
images: pdf
	@mkdir -p $(IMAGES_DIR)
	pdftoppm -png -r $(DPI) $(MAIN).pdf $(IMAGES_DIR)/page
	@echo "Generated images in $(IMAGES_DIR)/"

# Page images of the draft PDF, including review comments.
draft-images: draft
	@mkdir -p $(IMAGES_DIR)
	pdftoppm -png -r $(DPI) $(DRAFT).pdf $(IMAGES_DIR)/draft-page
	@echo "Generated images in $(IMAGES_DIR)/"

clean:
	$(LATEXMK) -c $(MAIN)
	$(LATEXMK) -c -jobname=$(DRAFT) $(MAIN)

distclean:
	$(LATEXMK) -C $(MAIN)
	$(LATEXMK) -C -jobname=$(DRAFT) $(MAIN)
	rm -f *.bbl *.aiguidelines
	rm -rf $(BUILD_DIR)

# verify / verify-update / verify-list / verify-diff
include $(AIWRITING)/make/aiwriting.mk
