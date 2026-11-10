# Nikto Module (Scaffold)

## Current state

- Runs the public image `frapsoft/nikto` (no local Dockerfile currently).
- Runtime code is in `modules/tools/nikto/scripts/nikto_scan.py`.
- Emits the combined payload (`aegis.v1`) and uses the legacy Nikto consumer for persistence.

## Future target

- Add a module service (container or library) that implements the core scanner contract.
