# Aura Compact Code Map

Status: `AURA_CODEMAP_ACTIVE`
Intent packet: `[OP:NAVIGATE][DOMAIN:TOPOLOGY][TARGET:CODEMAP][ENV:PYTHON][CONSTRAINT:TOKEN_SPARING]`

## Navigation Protocol

- Read .aura/CODEMAP.md first.
- Use command_index for bang commands before opening the REPL monolith.
- Use symbol_index semantic_id/signature_hash entries first, then current line ranges.
- Open only the top query hits plus their topology.neighbor_files.
- After any successful file write, run --refresh on touched paths instead of rebuilding the whole map.

## Summary

- **file_count**: 832
- **total_bytes**: 63965549
- **text_tokens_est**: 6595329
- **role_counts**: {'binary_artifact': 2, 'interface_surface': 13, 'knowledge_artifact': 111, 'native_accelerator': 8, 'operator_script': 5, 'python_module': 584, 'schema_or_lexicon': 68, 'support_file': 41}
- **topology_nodes**: 7263
- **topology_edges**: 15213
- **topology_source**: compiled_deep_topology
- **elapsed_ms**: 19794.24

## Coverage

- **included_file_count**: 832
- **policy**: all files under root except skipped runtime/cache dirs and generated CODEMAP outputs
- **excluded_generated_map_files**: `.aura/CODEMAP.json`, `.aura/CODEMAP.md`
- **skipped_dir_file_counts**: `.git`=53, `Aura_Memory`=1, `Aura_Sandbox`=1, `__pycache__`=8

## Command Index

- `!Aura_Sandbox` -> `.gitignore:46`
- `!CORE_AXIOM_VALID` -> `aura_nesy_sat_reasoner.py:280`
- `!DOCTYPE` -> `aura_savings_dashboard.py:49`, `index.html:1`
- `!ai_route` -> `USER_GUIDE.md:918`, `aura_ai_router.py:628`, `aura_node.py:7202`
- `!ai_router_regen` -> `USER_GUIDE.md:919`, `aura_node.py:7217`
- `!approve` -> `AURA_FINAL_REPORT.md:151`, `USER_GUIDE.md:956`, `aura_node.py:5638`
- `!ar_server_start` -> `USER_GUIDE.md:989`, `aura_node.py:6588`
- `!ar_server_stop` -> `USER_GUIDE.md:990`, `aura_node.py:6604`
- `!ar_start` -> `AURA_FINAL_REPORT.md:168`, `USER_GUIDE.md:989`, `aura_node.py:6588`, `refactored-auraos-upgrades.md:2572`
- `!ar_stop` -> `AURA_FINAL_REPORT.md:169`, `USER_GUIDE.md:990`, `aura_node.py:6604`, `refactored-auraos-upgrades.md:2572`
- `!attention` -> `USER_GUIDE.md:925`, `aura_node.py:5686`
- `!audit` -> `USER_GUIDE.md:940`, `aura_node.py:6184`
- `!backtrack` -> `AURA_FINAL_REPORT.md:143`, `USER_GUIDE.md:964`, `arxiv_forager.py:657`, `aura_node.py:6204`
- `!benchmark` -> `USER_GUIDE.md:939`, `aura_node.py:2991`
- `!c` -> `arch_reasoner_accel.rs:14`
- `!calibrate` -> `AURA_FINAL_REPORT.md:163`, `USER_GUIDE.md:979`, `aura_node.py:7532`
- `!canvas` -> `aura_savings_dashboard.py:174`
- `!catalyze` -> `AURA_FINAL_REPORT.md:156`, `USER_GUIDE.md:957`, `aura_node.py:7239`, `generate_ai_router.py:356`
- `!codeExts` -> `CODEMAP_TOOL_INTEGRATION_GUIDE.md:506`
- `!cognitive_search` -> `USER_GUIDE.md:924`, `aura_node.py:5655`
- `!commands` -> `USER_GUIDE.md:207`
- `!contingency_spawn` -> `aura_node.py:7006`
- `!converse` -> `AURA_FINAL_REPORT.md:161`, `USER_GUIDE.md:980`, `aura_node.py:7649`
- `!coordinated_reason` -> `USER_GUIDE.md:932`, `aura_node.py:7449`
- `!crystallize` -> `AURA_FINAL_REPORT.md:141`, `USER_GUIDE.md:970`, `aura_node.py:7306`
- `!curiosity_tree` -> `AURA_FINAL_REPORT.md:174`, `USER_GUIDE.md:968`, `aura_node.py:6645`
- `!db_repair` -> `USER_GUIDE.md:993`, `aura_node.py:2991`
- `!doctype` -> `aura_amd_track3_cli.py:187`, `aura_coding_arena/index.html:1`, `aura_efficiency_report.py:124`, `aura_human_agent_arena/index.html:1`
- `!empirical_lab` -> `USER_GUIDE.md:949`, `aura_node.py:6230`
- `!evolve_reasoning` -> `AURA_FINAL_REPORT.md:157`, `USER_GUIDE.md:934`, `aura_node.py:7301`
- `!export` -> `USER_GUIDE.md:991`, `aura_node.py:6008`
- `!fast_path` -> `AURA_FINAL_REPORT.md:173`, `USER_GUIDE.md:923`, `aura_node.py:7391`, `test_aura_functions.py:927`
- `!forage` -> `USER_GUIDE.md:963`, `aura_affordance_directory.py:461`, `aura_capability_lane_registry.py:120`, `aura_node.py:6190`
- `!forage_off` -> `USER_GUIDE.md:969`, `aura_node.py:6582`
- `!forage_on` -> `USER_GUIDE.md:969`, `aura_node.py:6576`
- `!forager_off` -> `aura_node.py:6582`
- `!forager_on` -> `aura_node.py:6576`
- `!fusion` -> `AURA_FINAL_REPORT.md:31`, `USER_GUIDE.md:978`, `aura_fusion.py:384`, `aura_node.py:7518`
- `!heal` -> `aura_node.py:5209`
- `!help` -> `AURA_FINAL_REPORT.md:48`, `SYNTAX_FIXES_APPLIED.md:107`, `USER_GUIDE.md:917`, `aura_node.py:7668`
- `!important` -> `aura_human_agent_arena/jarvis.css:107`, `index.html:9`
- `!indus_decrypt` -> `AURA_FINAL_REPORT.md:175`, `aura_node.py:7313`
- `!invalid_base64` -> `test_scientific_memory.py:972`
- `!manifest` -> `AURA_FINAL_REPORT.md:138`, `USER_GUIDE.md:917`, `aura_node.py:7668`
- `!markov` -> `AURA_FINAL_REPORT.md:144`, `USER_GUIDE.md:994`, `aura_node.py:7504`
- `!mesh_status` -> `AURA_FINAL_REPORT.md:167`, `USER_GUIDE.md:982`, `aura_capability_lane_registry.py:158`, `aura_node.py:5649`
- `!meta_analyze` -> `USER_GUIDE.md:935`, `aura_node.py:7352`
- `!meta_reason` -> `AURA_FINAL_REPORT.md:155`, `USER_GUIDE.md:936`, `aura_arch_reasoner.py:93`, `aura_node.py:7377`
- `!optimize` -> `AURA_FINAL_REPORT.md:172`, `USER_GUIDE.md:951`, `aura_node.py:5931`
- `!ping_mesh` -> `AURA_FINAL_REPORT.md:166`, `USER_GUIDE.md:983`, `aura_capability_lane_registry.py:158`, `aura_node.py:5644`
- `!plan` -> `aura_affordance_directory.py:440`, `aura_node.py:5602`
- `!push` -> `USER_GUIDE.md:992`, `aura_node.py:5166`, `test_aura_functions.py:207`
- `!qdkt` -> `aura_affordance_directory.py:356`
- `!r` -> `aura_arena_wfst_compiler.py:181`, `aura_capsule_trial_types.py:50`, `aura_ephemeral_adapter_registry.py:134`, `aura_graphify_schema.py:160`
- `!reason` -> `AURA_FINAL_REPORT.md:154`, `USER_GUIDE.md:931`, `aura_node.py:7492`
- `!repair_db` -> `USER_GUIDE.md:993`, `aura_node.py:6979`
- `!research` -> `AURA_FINAL_REPORT.md:142`, `USER_GUIDE.md:965`, `aura_affordance_directory.py:461`, `aura_capability_lane_registry.py:120`
- `!review` -> `USER_GUIDE.md:952`, `aura_node.py:6709`, `mistral_gate.py:93`
- `!rollback` -> `USER_GUIDE.md:955`, `aura_node.py:6694`
- `!route` -> `AURA_FINAL_REPORT.md:28`, `AURA_ROUTER.md:213`, `USER_GUIDE.md:977`, `aura_affordance_directory.py:230`
- `!s` -> `async_palace.py:163`, `aura_mitosis.py:196`, `aura_node.py:1167`, `aura_spvm.py:134`
- `!saturn` -> `AURA_FINAL_REPORT.md:147`, `AuraOS.tex:212`, `Second_Paper_extracted.txt:74`, `USER_GUIDE.md:937`
- `!saturn_heal` -> `AURA_FINAL_REPORT.md:148`, `AURA_REFACTORING_ANALYSIS.md:136`, `HOLOGRAPHIC_HEADER_IMPLEMENTATION.md:121`, `USER_GUIDE.md:938`
- `!savings` -> `AURA_FINAL_REPORT.md:162`, `AuraOS.tex:185`, `USER_GUIDE.md:981`, `aura_node.py:7556`
- `!scan_topology` -> `USER_GUIDE.md:920`, `aura_node.py:7148`
- `!search_similar` -> `USER_GUIDE.md:966`, `aura_node.py:6618`, `refactored-auraos-upgrades.md:2573`
- `!self_optimize` -> `USER_GUIDE.md:951`, `aura_dynamic_attention.py:209`, `aura_node.py:5931`, `refactored-auraos-upgrades.md:826`
- `!self_reflect` -> `USER_GUIDE.md:950`, `aura_arch_reasoner.py:223`, `aura_hv_cache.py:36`, `aura_node.py:5749`
- `!settings` -> `USER_GUIDE.md:917`, `aura_node.py:7668`
- `!show` -> `docs/AURA_HUMAN_AGENT_ARENA.md:267`, `tests/test_aura_human_agent_concepts.py:86`
- `!simulate` -> `USER_GUIDE.md:922`, `aura_node.py:7142`, `cognitive_router.py:224`
- `!something` -> `aura_node.py:4969`
- `!srcPos` -> `index.html:122`
- `!stage` -> `AURA_FINAL_REPORT.md:149`, `USER_GUIDE.md:952`, `aura_capability_lane_registry.py:229`, `aura_live_architect.py:2159`
- `!stage_merge` -> `AURA_FINAL_REPORT.md:150`, `USER_GUIDE.md:953`, `aura_capability_lane_registry.py:229`, `aura_live_architect.py:2160`
- `!stage_purge` -> `USER_GUIDE.md:954`, `aura_capability_lane_registry.py:229`, `aura_node.py:6774`
- `!stage_review` -> `USER_GUIDE.md:952`, `aura_capability_lane_registry.py:229`, `aura_node.py:6709`
- `!status` -> `AURA_FINAL_REPORT.md:136`, `SYNTAX_FIXES_APPLIED.md:107`, `aura_node.py:5166`
- `!strategy_buffer_stats` -> `USER_GUIDE.md:933`, `aura_coordinated_solver.py:69`, `aura_node.py:7476`
- `!synthesize` -> `USER_GUIDE.md:971`, `aura_associative_core.py:141`, `aura_node.py:6896`, `test_aura_functions.py:913`
- `!system_audit` -> `USER_GUIDE.md:940`, `aura_node.py:6184`
- `!target_bytes` -> `cognitive_search.rs:72`
- `!test` -> `AuraOS.tex:533`, `tests/test_aura_codemap_verify.py:57`
- `!test_airlock` -> `USER_GUIDE.md:942`, `aura_node.py:5614`
- `!tgtPos` -> `index.html:122`
- `!timeline` -> `USER_GUIDE.md:967`, `aura_node.py:6657`
- `!topology` -> `AURA_FINAL_REPORT.md:48`, `SYNTAX_FIXES_APPLIED.md:107`, `USER_GUIDE.md:920`, `aura_affordance_directory.py:146`
- `!topology_deep` -> `USER_GUIDE.md:921`, `aura_affordance_directory.py:146`, `aura_node.py:7231`
- `!total` -> `aura_savings_dashboard.py:223`
- `!voice` -> `USER_GUIDE.md:995`, `aura_node.py:7731`

## Navigation Rings

### substrate_core
- `AuraOS__A_Polysynthetic_Cognitive_Substrate_for_High-Dimensional_Edge_Orchestration_and_Visual_Code_Topology.pdf`
- `aura_core.py`
- `aura_node.py`
- `aura_substrate.py`
- `gateway.py`
- `test_aura_substrate.py`

### cognition_and_memory
- `.aura/memory_apertures/coding_localize.v1.json`
- `.mempalace/aura_thought.txt`
- `.mempalace/lexicon.json`
- `.mempalace/nexus.json`
- `.mempalace/temp_prompt.txt`
- `async_palace.py`
- `aura_attention_palace.py`
- `aura_blockchain/memory_staking.py`
- `aura_civic_memory.py`
- `aura_cognitive_synthesizer.py`
- `aura_dream_engine.py`
- `aura_dream_retrieval.py`
- ... 17 more; query CODEMAP.json for exact file cards

### mesh_and_routing
- `.aura/civic_completion_ledger.json`
- `.github/workflows/model-cognome-adaptive-router.yml`
- `.github/workflows/model-cognome-governed-routing.yml`
- `AURA_ROUTER.md`
- `FRACTAL_LEDGER_IMPLEMENTATION.md`
- `LIQUID_INTERNET_IMPLEMENTATION.md`
- `aura_adaptive_model_router.py`
- `aura_ai_router.py`
- `aura_anthropic_router.py`
- `aura_arena_experience_ledger.py`
- `aura_blockchain/__init__.py`
- `aura_blockchain/block.py`
- ... 37 more; query CODEMAP.json for exact file cards

### topology_and_navigation
- `.aura/topology_baseline.json`
- `aura_codebase_navigator.py`
- `aura_showcase/topology.css`
- `aura_showcase/topology.js`
- `aura_showcase_intent_topology.py`
- `aura_topological_context_anchor.py`
- `aura_topological_scanner.py`
- `aura_topology_analyzer.py`
- `aura_topology_cli.py`
- `aura_topology_density_controller.py`
- `aura_topology_health.py`
- `aura_topology_manager.py`
- ... 9 more; query CODEMAP.json for exact file cards

### security_and_validation
- `.aura/SECURITY.md`
- `DEEP_AUDIT_REPORT.md`
- `aura_background_auditor.py`
- `aura_cockpit_audit_trail.py`
- `aura_crucible_validation.py`
- `aura_crypto_puf.py`
- `aura_emergent_capability_auditor.py`
- `aura_heal.py`
- `aura_metaharness_audit.py`
- `aura_ojibwe_translation_guard.py`
- `aura_tokenizer_guard.py`
- `aura_validation.py`
- ... 11 more; query CODEMAP.json for exact file cards

### interfaces_and_docs
- `.aura/AFFORDANCE_MAP.json`
- `.aura/ARCHITECTURE.md`
- `.aura/AURA.md`
- `.aura/CONVERSE.md`
- `.aura/HERMES_AURA_RULES.md`
- `.aura/OUTPUT_FORMATS.md`
- `.aura/RESEARCH_MANIFEST.json`
- `.aura/ROLES.md`
- `.aura/amd_track3_demo_tasks.json`
- `.aura/arena_routes/coding.v1.json`
- `.aura/arena_routes/human_agent.v1.json`
- `.aura/arena_routes/meta.v1.json`
- ... 692 more; query CODEMAP.json for exact file cards

## Hubs

- `aura_node.py` (python_module): 194 symbols, degree 870, ~104110 tokens
- `aura_agent_arena_cli.py` (python_module): 100 symbols, degree 575, ~17235 tokens
- `aura_live_architect.py` (python_module): 74 symbols, degree 569, ~30294 tokens
- `test_scientific_memory.py` (python_module): 111 symbols, degree 517, ~13607 tokens
- `aura_relational_authority.py` (python_module): 58 symbols, degree 477, ~19006 tokens
- `aura_architect_loop.py` (python_module): 70 symbols, degree 457, ~18332 tokens
- `aura_fst_routing.py` (python_module): 35 symbols, degree 453, ~8991 tokens
- `test_aura_functions.py` (python_module): 80 symbols, degree 358, ~9340 tokens
- `aura_scientific_memory.py` (python_module): 44 symbols, degree 341, ~9915 tokens
- `aura_human_agent_arena.py` (python_module): 72 symbols, degree 326, ~22286 tokens
- `aura_music_coding_arena.py` (python_module): 46 symbols, degree 303, ~11812 tokens
- `aura_planning_board.py` (python_module): 51 symbols, degree 286, ~7678 tokens

## Topology Integration

- **source**: compiled_deep_topology
- **nodes**: 7263
- **edges**: 15213
- **top_files_by_degree**:
  - `aura_node.py` degree=870 nodes=221 neighbors=`arxiv_forager.py`, `async_palace.py`, `aura_ai_router.py`, `aura_api_rotator.py`
  - `aura_agent_arena_cli.py` degree=575 nodes=101 neighbors=`aura_agent_arena_bridge.py`, `aura_agent_arena_fireworks.py`
  - `aura_live_architect.py` degree=569 nodes=85 neighbors=`aura_architect_loop.py`, `aura_builder_context.py`, `aura_coding_arena_grounding.py`, `aura_coding_arena_workflow.py`
  - `test_scientific_memory.py` degree=517 nodes=120 neighbors=`arxiv_forager.py`, `aura_paper_memory.py`, `aura_scientific_memory.py`, `travel_price_sidecar.py`
  - `aura_relational_authority.py` degree=477 nodes=59 neighbors=`aura_graphify_schema.py`, `aura_workflow_gates.py`, `liquid_attractor_control_plane.py`
  - `aura_architect_loop.py` degree=457 nodes=73 neighbors=`aura_arena_st3gg_codec.py`, `aura_codebase_navigator.py`, `aura_dream_retrieval.py`, `aura_fst_routing.py`
  - `aura_fst_routing.py` degree=453 nodes=36 neighbors=`aura_architect_loop.py`, `aura_fusion.py`, `aura_graphify_schema.py`, `aura_harness_evolver.py`
  - `test_aura_functions.py` degree=358 nodes=87 neighbors=`arch_reasoner_accel.py`, `async_palace.py`, `aura_arch_reasoner.py`, `aura_associative_core.py`
  - `aura_scientific_memory.py` degree=341 nodes=46 neighbors=`arxiv_forager.py`, `aura_fst_routing.py`, `aura_node.py`, `aura_ojibwe_lexicon_sidecar.py`
  - `aura_human_agent_arena.py` degree=326 nodes=73 neighbors=`aura_affordance_directory.py`, `aura_agent_arena_bridge.py`, `aura_api_rotator.py`, `aura_coding_arena_3d.py`
  - `aura_music_coding_arena.py` degree=303 nodes=49 neighbors=`aura_fst_routing.py`, `aura_live_architect.py`, `aura_music_inversion.py`, `aura_proxy_benchmark.py`
  - `aura_planning_board.py` degree=286 nodes=52 neighbors=`aura_event_contracts.py`, `aura_planning_events.py`, `aura_planning_frontier.py`, `aura_planning_regression.py`

## High-Value Symbols

- `AStarQuantumStateCompressor` -> `aura_node.py:1362`
- `ATTTransducer` -> `aura_att_fst_runtime.py:41`
- `AbilityAtom` -> `aura_emergent_potential_repl.py:173`
- `AccountState` -> `aura_blockchain/node.py:27`
- `ActCapsule` -> `aura_architect_loop.py:84`
- `ActionCapsule` -> `aura_liquid_planning_arena.py:112`
- `ActionContinuityEvidence` -> `aura_planning_board.py:433`
- `ActionSpec` -> `aura_planning_board.py:308`
- `ActorType` -> `aura_event_contracts.py:131`
- `AdapterMetadata` -> `aura_ephemeral_adapter_registry.py:19`
- `AdaptiveFusionPanelExecutor` -> `aura_adaptive_fusion.py:77`
- `AdaptiveLiquidTimeConstant` -> `liquid_kernel.py:60`, `liquid_math_reference.py:39`
- `AdaptiveModelExecutor` -> `aura_adaptive_model_executor.py:50`
- `AdaptiveModelRouter` -> `aura_adaptive_model_router.py:151`
- `AgentIRCompiler` -> `aura_agent_ir_compiler.py:17`
- `AgentIRNode` -> `aura_agent_ir.py:37`
- `AnimacyClass` -> `aura_ojibwe_morph_bridge.py:84`
- `AnthropicRouter` -> `aura_anthropic_router.py:268`
- `AppendOnlyEventStore` -> `aura_event_contracts.py:634`
- `ApprovalAttestation` -> `aura_relational_authority.py:451`
- `ArXivForager` -> `arxiv_forager.py:84`
- `ArchitectBuilderBridge` -> `aura_live_architect.py:1370`
- `ArchitectCouncilDecision` -> `aura_live_architect.py:140`
- `ArchitectExecutionResult` -> `aura_architect_loop.py:287`
- `ArchitectFusionCouncil` -> `aura_live_architect.py:996`
- `ArchitectFusionLoop` -> `aura_architect_loop.py:1746`
- `ArchitectLedgerRecord` -> `aura_architect_loop.py:254`
- `ArchitectLoopResult` -> `aura_architect_loop.py:269`
- `ArchitectModelProfile` -> `aura_live_architect.py:115`
- `ArchitectModelRouter` -> `aura_live_architect.py:672`
- `ArenaAttemptArchive` -> `aura_arena_attempt_archive.py:217`
- `ArenaBridgeError` -> `aura_agent_arena_errors.py:93`
- `ArenaCrucibleService` -> `aura_arena_crucible.py:31`
- `ArenaExperience` -> `aura_arena_experience.py:143`
- `ArenaExperienceLedger` -> `aura_arena_experience_ledger.py:75`
- `ArenaGateDialogueService` -> `aura_arena_gate_dialogue.py:165`
- `ArenaGrammarCompileResult` -> `aura_arena_wfst_compiler.py:64`
- `ArenaGrammarRegistry` -> `aura_arena_wfst_registry.py:17`
- `ArenaLease` -> `aura_liquid_planning_arena.py:170`
- `ArenaLink` -> `aura_coding_arena_3d.py:83`
- `ArenaNode` -> `aura_coding_arena_3d.py:62`
- `ArenaPatch` -> `aura_architect_loop.py:207`
- `ArenaResearchIdea` -> `aura_music_coding_arena.py:81`
- `ArenaST3GGCapsule` -> `aura_arena_st3gg_codec.py:55`
- `ArenaST3GGDecision` -> `aura_arena_st3gg_codec.py:43`
- `ArenaStatePacket` -> `aura_arena_state_packet.py:21`
- `ArenaToolRuntime` -> `aura_arena_tool_runtime.py:169`
- `ArenaTransition` -> `aura_arena_wfst_types.py:70`
- `ArenaWFSTRuntime` -> `aura_arena_wfst_runtime.py:35`
- `ArxivPaper` -> `arxiv_forager.py:1186`
- `AssetProperties` -> `aura_vsa_rendering.py:44`
- `AsyncExpertQuantizationEngine` -> `aura_timestep_svd_quantizer.py:337`
- `AsyncMemoryPalace` -> `async_palace.py:380`, `aura_attention_palace.py:43`
- `AthabaskanPositionalParser` -> `aura_positional_parser.py:20`
- `AttentionConfig` -> `aura_dynamic_attention.py:36`
- `AttentionResult` -> `aura_dynamic_attention.py:46`
- `AttestationDecision` -> `aura_relational_authority.py:35`
- `AttributionLedger` -> `aura_cost_attribution.py:108`
- `AudioAccessDecision` -> `aura_ojibwe_audio_consent_registry.py:78`
- `AudioConsentRecord` -> `aura_ojibwe_audio_consent_registry.py:48`
- `AudioConsentRegistry` -> `aura_ojibwe_audio_consent_registry.py:87`
- `AudioLevel` -> `aura_ojibwe_audio_consent_registry.py:35`
- `AuraARWebSocketServer` -> `aura_topology_ws_bridge.py:360`
- `AuraAffordance` -> `aura_affordance_directory.py:37`
- `AuraAgentArenaBridge` -> `aura_agent_arena_bridge.py:182`
- `AuraArchReasoner` -> `aura_arch_reasoner.py:31`
- `AuraAssociativeCore` -> `aura_associative_core.py:30`
- `AuraCodingArenaRouter` -> `aura_fst_routing.py:399`
- `AuraCognitiveSynthesizer` -> `aura_cognitive_synthesizer.py:24`
- `AuraCompilerParser` -> `aura_node.py:734`
- `AuraConsensus` -> `aura_blockchain/consensus.py:105`
- `AuraContextCrusher` -> `aura_context_crusher.py:231`
- `AuraDependencyScanner` -> `aura_node.py:1105`
- `AuraDreamEngine` -> `aura_dream_engine.py:55`
- `AuraEpistemicIngestGateway` -> `aura_epistemic_ingest.py:27`
- `AuraEventEnvelope` -> `aura_event_contracts.py:382`
- `AuraFederation` -> `aura_federation.py:100`
- `AuraFusionAgent` -> `aura_fusion.py:89`
- `AuraFusionCoordinator` -> `aura_fusion.py:481`
- `AuraFusionResult` -> `aura_fusion.py:126`
