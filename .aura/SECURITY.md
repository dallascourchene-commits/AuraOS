# SECURITY

Hard constraints. Violating any of these is a failed response.

- **No new dependencies.** Do not add `import` statements for packages that are
  not already present in the provided context, unless the packet contains
  `[CONSTRAINT:ALLOW_NEW_DEPS]`.
- **No fabricated files or paths.** Reference only files/symbols that appear in
  the provided context or packet. Never invent a filename.
- **No secret exfiltration.** Never emit API keys, tokens, or the contents of
  `aura_secrets.json`. Never read environment secrets into the output.
- **No destructive shell.** Do not propose `rm -rf`, history rewrites, force
  pushes, or database drops.
- **No network side effects.** Do not add code that phones home or posts data
  to external endpoints that were not already in the file.
- **Stay in scope.** Only modify the target named in the packet.
