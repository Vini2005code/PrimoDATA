# TODO

- [x] Locate patient-context cap in `app/services/patients.py` (config-driven via `settings.max_patients_context`).
- [x] Increase `max_patients_context` to 1000 in `app/core/config.py`.
- [x] Increase chart max-points cap to 1000 in `app/core/config.py` (Pydantic validation uses `settings.chart_max_points`).
- [ ] Git PR: clean working tree, commit only the intended file(s), open PR.

