PY ?= python3
ID := $(shell $(PY) -c "import json;print(json.load(open('pack-meta.json'))['id'])")
ZIP := dist/$(ID).zip

.PHONY: all build check check-official preview gallery test dist clean

all: check test

build:
	$(PY) tools/build_pack.py

check: build
	$(PY) tools/validate_pack.py pack --zip $(ZIP) --compat-reactions --market

# Needs network: downloads the app's official checker at a pinned commit.
check-official: build
	bash tools/fetch-official-checker.sh
	$(PY) .cache/pet_pack_check.py pack --compat-reactions

preview: build
	$(PY) tools/preview.py

# Per-animation GIFs + contact sheet (README gallery).
gallery: build
	$(PY) tools/gallery.py

test:
	$(PY) -m pytest -q

dist: check preview gallery test
	@echo "release artifact: $(ZIP)"

clean:
	rm -rf dist .cache .pytest_cache
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
