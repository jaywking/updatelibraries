# Future Development Parking Lot

These are worthwhile follow-ups that are intentionally outside the current safety-flow change.

- Add a direct-requirements-only update mode, with the current all-installed-packages behavior retained as an explicit option.
- Move dependency-managed package rules into a documented configuration/policy file so future coupled packages do not require code changes.
- Read installed versions after updates and distinguish planned, resolver-selected, unchanged, failed, and policy-skipped packages in the summary.
- Terminate and reap active pip child processes cleanly when the updater is interrupted.
- Add non-interactive LocalVenv selection flags and a consolidated pre-run plan for multi-environment updates.
- Expand automated coverage for batch fallback, combined exclusions, malformed pip output, dependency-check failures, retries, snapshots, and LocalVenv exit-code aggregation.
