.PHONY: help lint interrogate

UV ?= uv

# Interrogate measures docstring presence in the Python files under
# INTERROGATE_TARGETS; add a new Python directory there. No `--python` pin: a
# managed interpreter would be downloaded.
INTERROGATE_VERSION ?= 1.7.0
INTERROGATE_TARGETS ?= nc_prompt_tools tests
INTERROGATE = $(UV) tool run --from 'interrogate==$(INTERROGATE_VERSION)' interrogate --fail-under 100

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?##' $(MAKEFILE_LIST) | \
	awk 'BEGIN {FS=":"; printf "Available targets:\n"} {printf "  %-20s %s\n", $$1, $$2}'

# To list each undocumented definition, run
# `make interrogate INTERROGATE_TARGETS="-vv nc_prompt_tools tests"`.
interrogate: ## Enforce complete Python docstring coverage
	$(INTERROGATE) $(INTERROGATE_TARGETS)

lint: ## Run the docstring-coverage gate
	$(MAKE) interrogate
