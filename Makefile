.PHONY: help lint interrogate

# Every uv call goes through the vendored helper, which cleans the environment,
# uses the global uv cache, runs offline first and goes online at most once. See
# https://github.com/leynos/shared-actions/tree/main/uv_gate for the contract.
# `scripts/uv_gate.py` is the shared-actions helper, vendored byte for byte, so
# update it by copying the canonical file, never by editing it here. The helper
# finds uv on PATH (outside ~/.lody, which it removes), so there is no UV
# override: put the uv you want first. It needs python3 3.9 or newer. A uv
# that reports only `Git operation failed` for a Git source missing from the
# cache is not retried online: warm the cache once with `uv tool run`.
UV_GATE ?= python3 scripts/uv_gate.py

# Interrogate measures docstring presence in the Python files under
# INTERROGATE_TARGETS; add a new Python directory there. No `--python` pin: a
# managed interpreter would be downloaded.
INTERROGATE_VERSION ?= 1.7.0
INTERROGATE_TARGETS ?= nc_prompt_tools scripts tests
INTERROGATE = $(UV_GATE) tool --from 'interrogate==$(INTERROGATE_VERSION)' -- interrogate --fail-under 100

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?##' $(MAKEFILE_LIST) | \
	awk 'BEGIN {FS=":"; printf "Available targets:\n"} {printf "  %-20s %s\n", $$1, $$2}'

# To list each undocumented definition, run
# `make interrogate INTERROGATE_TARGETS="-vv nc_prompt_tools tests"`.
interrogate: ## Enforce complete Python docstring coverage
	$(INTERROGATE) $(INTERROGATE_TARGETS)

lint: ## Run the docstring-coverage gate
	$(MAKE) interrogate
