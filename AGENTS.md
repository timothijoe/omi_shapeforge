# OMI ShapeForge development

- Keep `main` empty. Code lives on `dev`; create feature branches from `dev` for subsequent iterations and keep development commits off `main`.
- This repository owns workflow orchestration, configuration, registration, evaluation and project documentation.
- FoundationStereo and BundleSDF are sibling Git repositories. Keep algorithm-specific edits in their corresponding forks and record the revisions used by ShapeForge.
- Keep raw data, checkpoints, environments and generated experiment outputs outside this Git repository. Current machine settings live in `configs/workspace.toml`; use ignored `configs/local.toml` for overrides.
- Preserve historical migration snapshots. Write new experiments to new output directories and retain their manifests and reports.
- The lightweight control environment is `.venv`. GPU workloads run in the separate environments selected by the workspace configuration.
- Run `.venv/bin/python -m unittest discover -s tests -v` for orchestration changes. Validate changes to backend invocation with the relevant smoke workflow when the environment is available.
- Keep `docs/current.md` aligned with actual validation. Distinguish official samples, component checks, frozen geometry replay and full reconstruction results.
