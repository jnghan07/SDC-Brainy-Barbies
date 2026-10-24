---
name: Workspace Python package setup
description: Side effects from installing a Python dependency in the workspace root.
---

Installing a Python package through the workspace package installer from the repository root may run `uv init`, add a root `pyproject.toml` and lockfile, and append Nix configuration to `.replit`, even when the dependency belongs to a nested Python component.

**Why:** This workspace includes multiple artifacts and a standalone Python component whose requirements are already declared outside the root; package setup can create unrelated tracked changes.

**How to apply:** Before installing, check whether the package belongs to a nested project. After installation, inspect workspace status, remove unrelated generated files, and restore configuration only through its validated replacement flow.
