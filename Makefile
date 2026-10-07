PY=PYTHONPATH=src python3
.PHONY: data prep eda bend outcomes test
data:      ; scripts/download_data.sh
prep:      ; $(PY) -m bdb27.prep
eda:       ; $(PY) -m bdb27.eda
bend:      ; $(PY) -m bdb27.bend
outcomes:  ; $(PY) -m bdb27.outcomes
test:      ; $(PY) -m pytest -q tests/
