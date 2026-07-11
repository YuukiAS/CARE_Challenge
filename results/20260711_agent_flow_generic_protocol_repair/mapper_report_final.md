# Mapper Report Final

Final mapping:

- `wiki/current_state.yaml` now records current review source/token.
- `validate_care_architecture_wiki.py` reads current review source dynamically.
- `generate_care_architecture_wiki.py` reads history annotations and computes
  predecessor deltas generically.
- Active policy files no longer contain concrete milestone-number control-flow
  triggers in the scanned active set.
