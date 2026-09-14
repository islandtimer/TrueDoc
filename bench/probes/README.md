# Probes

One-off investigation scripts. Each was written to answer one question, and the docs (`docs/PROGRESS_LOG.md`,
`docs/STATUS.md`, `docs/MODEL_CHOICE.md`, `docs/GPU_PLAN.md`, `docs/DECISIONS.md`) cite it by name as the evidence
for a finding. They are kept so a finding can be checked, not maintained as tools: some expect a run folder or a
saved cache that has since moved, some import PyMuPDF (installed with the `bench` extra), and the code they probe may
have changed since. Run them from the repository root. `wave3_measure.sh` is kept as it ran on 7 September, and its
paths still name that session's scratch folder.

The measuring instruments the work still depends on are in `bench/tools/`, described in `bench/README.md`.
