# Phase C2 Migration Notes

- Arena grammar schema remains `AURA_ARENA_GRAMMAR_MANIFEST_V1`.
- `ArenaTransition` gains optional paired capsule references.
- Existing manifests without capsule references remain valid.
- Coding Workbench uses a version-pinned overlay so its compact manifest is not reformatted.
- Route capsules default to disabled unless explicitly enabled by policy or environment.
- Arena experience storage migrates from schema version 2 to 3 by adding two capsule-observation columns and an index.
- Existing experience rows remain readable and are not assigned invented capsule observations.
