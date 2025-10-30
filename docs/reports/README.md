# reports/

Ephemeral machine-generated artifacts produced by local runs or CI jobs.

Included categories (may be created on demand):

- openapi coverage JSON / Cobertura (e.g. `openapi_coverage.json`)
- markdown summaries (e.g. `openapi_summary.md`)
- future: lint outputs, test coverage (`coverage.xml`), security scan results

Git ignore rules keep everything here untracked except this README (and an optional `.gitkeep`).
If you need to persist or diff a report across commits, relocate it outside `reports/` or explicitly
remove the ignore rule.

Best practice: treat these as disposable build artifacts; upload to CI artifacts store if you need history.
