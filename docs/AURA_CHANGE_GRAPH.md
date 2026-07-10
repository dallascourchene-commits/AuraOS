# Aura Change Graph

## What This Is

Represents a proposed coding change as a graph of files, symbols, tests, risks, dependencies, and agent actions.

## Functions

- `build_change_graph(objective, localization_packet)` — build from objective
- `change_graph_to_act_capsules(graph)` — convert to act capsules
- `change_graph_to_review_packet(graph)` — convert to review packet
- `change_graph_to_token_report(graph)` — token cost comparison

## Safety

Change graph requires topology health. Blocks if topology is degraded.
