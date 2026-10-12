---
name: Python package environment
description: Handling missing project Python dependencies when the workspace points uv at the read-only Nix interpreter.
---

The workspace's default `.pythonlibs` interpreter can resolve to a read-only Nix store path. A package can be declared in `pyproject.toml` and `uv.lock` yet still be unavailable to that interpreter, and attempts to install there fail with a permissions error.

**Why:** A project script needed PyMuPDF, and the configured Python also lacked an already-declared backend dependency. Installing into a local uv-managed `.venv` worked without changing the locked project dependencies.

**How to apply:** If the default Python cannot import a declared dependency and uv reports a Nix store permission error, create `.venv` with `uv venv`, install into it with `uv pip install --python .venv/bin/python`, and run the affected script with that interpreter.
