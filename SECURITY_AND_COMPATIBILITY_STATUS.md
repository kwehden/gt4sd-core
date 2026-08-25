# Security and Torch 2 Compatibility Status

This document records the status of the `deps/spike-torch2` branch relative to
`main`. It distinguishes changes committed in this repository from a validated
but not-yet-published upstream dependency patch.

## Committed changes in this branch

### Patched dev and documentation dependencies

`dev_requirements.txt` updates the following packages:

| Package | Change | Issue addressed |
| --- | --- | --- |
| Jinja2 | `<3.1.0` → `>=3.1.6` | CVE-2025-27516 (`attr` filter sandbox escape) |
| Flask | `1.1.2` → `3.1.3` | CVE-2026-27205 (session responses missing `Vary: Cookie`) |
| Flask-Login | `0.5.0` → `0.6.3` | Required for Flask 3 compatibility |
| pytest | `6.2.5` → `9.0.3` | CVE-2025-71176 (temporary-directory handling) |

Flask and Flask-Login are used by `docs/app.py`, the documentation server.
They are not imported by the packaged `src/gt4sd` library.

### Setuptools remediation

`requirements.txt` and all three Conda environment files update setuptools
from `69.5.1` to `78.1.1`. This addresses CVE-2025-47273.

Setuptools remains below `83.0.0`. The fix for CVE-2026-59890 requires that
version, but setuptools 82+ removes bundled `pkg_resources`, which is still
imported by the pinned legacy ML stack. Resolving that issue requires a
coordinated dependency upgrade; it is not safe to treat it as an isolated
setuptools bump.

### Torch 2.6 source compatibility spike

The branch adds two compatibility changes that are no-ops on Torch 1.12:

1. `src/gt4sd/training_pipelines/torchdrug/unpatch.py` recognizes the Torch 2
   public `LRScheduler` base class and restores both scheduler aliases when
   applying the TorchDrug compatibility patch.
2. `src/gt4sd/frameworks/torch/__init__.py` restores the historical
   `torch.load(..., weights_only=False)` default only when callers do not
   explicitly choose a value. This keeps existing trusted GT4SD checkpoint
   loading paths working on Torch 2.6.

The second change is a compatibility decision, not a security hardening: full
pickle loading must be limited to trusted checkpoint artifacts. Callers that
explicitly set `weights_only=True` retain the safer Torch 2.6 behavior.

The committed dependency manifests still pin Torch 1.12. This branch proves
source compatibility with Torch 2.6; it does **not** yet ship a production
Torch 2 migration or claim that Torch-related advisories are closed.

## Validated upstream Moses fix; not yet delivered

Torch 2 requires boolean masks for tensor indexing. The pinned Moses 0.2.0
source uses `torch.uint8` end-of-sequence masks, causing five failures under
Torch 2.6 in AAE/VAE generation and ORGAN training.

A minimal upstream patch changes those three masks to `torch.bool`:

- `moses/aae/model.py`
- `moses/vae/model.py`
- `moses/organ/model.py`

The patch is committed locally in the GT4SD Moses clone as
`07b087c` (`fix: use boolean sequence masks for torch 2.x`), based on the
pinned Moses `v0.2.0` source. It is not yet reachable from this repository's
`vcs_requirements.txt`: publishing it requires GitHub Git-write access to the
GT4SD organization repository (and any required organization SSO authorization),
then updating the GT4SD GuacaMol-baselines fork and this repository to pin the
published immutable commits.

## Verification

With a CPU Torch 2.6.0 environment, TorchVision 0.21.0, matching PyG CPU
wheels, and `pytorch-fast-transformers` rebuilt against Torch 2.6:

- Black: passed
- Flake8: passed
- CLI entry points: 6/6 passed
- Full pytest suite with the local Moses patch: **400 passed, 61 skipped**

The final run is recorded outside the repository in the local workspace test
log. It validates the source changes and Moses patch together; it does not
replace CI after the dependency pins are published.

## Remaining work

1. Publish the Moses boolean-mask patch and update the GuacaMol-baselines and
   GT4SD VCS dependency pins to immutable commits.
2. Re-run CI from a clean environment after those published pins are used.
3. Plan the production Torch migration separately. The current Torch 1.12
   cap still blocks upgrades to parts of the Transformers, Diffusers, and
   related ML stack.
4. Keep the TensorFlow/Keras/Protobuf upgrade work separate; it is constrained
   by the independent `tensorflow<2.11` runtime floor.
