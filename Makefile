PY=PYTHONPATH=src python3
.PHONY: data prep eda bend outcomes test
data:      ; scripts/download_data.sh
prep:      ; $(PY) -m bdb27.prep
eda:       ; $(PY) -m bdb27.eda
bend:      ; $(PY) -m bdb27.bend
outcomes:  ; $(PY) -m bdb27.outcomes
test:      ; $(PY) -m pytest -q tests/
linkage:   ; $(PY) -m bdb27.linkage
ingame:    ; $(PY) -m bdb27.ingame
features:  ; $(PY) -m bdb27.features
outcomes_all: ; $(PY) -m bdb27.outcomes_all
screen:    ; $(PY) -m bdb27.screen
forty:     ; $(PY) -m bdb27.forty
translation: ; $(PY) -m bdb27.translation
figures:   ; $(PY) -m bdb27.figures
reportcard: ; $(PY) -m bdb27.reportcard
