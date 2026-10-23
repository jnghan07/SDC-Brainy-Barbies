---
name: Pending merge persistence
description: Rechecking Git merge preparation across user-approval boundaries in this workspace.
---

Do not assume a prepared, uncommitted merge survives an approval-turn boundary.

**Why:** A prepared merge lost its pending merge metadata and staged-only
documentation corrections between turns. An intervening single-parent
checkpoint left the branches diverged despite a clean working tree.

**How to apply:** Recheck the pending merge parent, current files, and commit
parents before finalizing an approved merge. A clean working tree or a new
checkpoint is not proof of reconciliation. Once authorized, complete the
reviewed resolution and its merge commit together; never infer permission to
push from permission to commit.
