# aiwriting.mk -- reusable Make targets for protected-content verification.
#
# Usage from a paper's Makefile:
#
#     AIWRITING := ../technical-writing        # or wherever this repo lives
#     include $(AIWRITING)/make/aiwriting.mk
#
# Provides: verify, verify-update, verify-list, verify-diff
#
# Override AIKEEP_MANIFEST or AIKEEP_ROOT if the defaults do not fit:
#
#     AIKEEP_ROOT := sections
#     include $(AIWRITING)/make/aiwriting.mk

# Directory containing this .mk file, with the trailing slash stripped.
AIWRITING_MK_DIR := $(patsubst %/,%,$(dir $(lastword $(MAKEFILE_LIST))))

PYTHON          ?= python3
VERIFY_AIKEEP   ?= $(PYTHON) $(AIWRITING_MK_DIR)/../scripts/verify_aikeep.py
AIKEEP_MANIFEST ?= .aikeep-manifest.json
AIKEEP_ROOT     ?= .

AIKEEP_ARGS = --manifest $(AIKEEP_MANIFEST) --root $(AIKEEP_ROOT)

.PHONY: verify verify-update verify-list verify-diff

# Verify \aikeep{} and \aianchor{} protected content has not been modified.
# REQUIRED after editing any .tex file.
verify:
	@$(VERIFY_AIKEEP) verify $(AIKEEP_ARGS)

# Update the manifest (run only after human-approved intentional changes).
verify-update:
	@$(VERIFY_AIKEEP) generate $(AIKEEP_ARGS)

# List all protected blocks in the project.
verify-list:
	@$(VERIFY_AIKEEP) list $(AIKEEP_ARGS)

# Show what changed since the manifest was generated.
verify-diff:
	@$(VERIFY_AIKEEP) diff $(AIKEEP_ARGS)
