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

- **file_count**: 604
- **total_bytes**: 187944421
- **text_tokens_est**: 5392853
- **role_counts**: {'binary_artifact': 13, 'interface_surface': 5, 'knowledge_artifact': 86, 'native_accelerator': 8, 'operator_script': 5, 'python_module': 430, 'schema_or_lexicon': 27, 'support_file': 30}
- **topology_nodes**: 5880
- **topology_edges**: 12155
- **topology_source**: compiled_deep_topology
- **elapsed_ms**: 35255.09

## Coverage

- **included_file_count**: 604
- **policy**: all files under root except skipped runtime/cache dirs and generated CODEMAP outputs
- **excluded_generated_map_files**: `.aura/CODEMAP.json`, `.aura/CODEMAP.md`
- **skipped_dir_file_counts**: `.git`=408, `.pytest_cache`=5, `Aura_Memory`=8, `__pycache__`=146

## Command Index

- `!Aura_Sandbox` -> `.gitignore:42`
- `!CORE_AXIOM_VALID` -> `aura_nesy_sat_reasoner.py:280`
- `!DOCTYPE` -> `aura_savings_dashboard.py:49`, `index.html:1`
- `!ai_route` -> `USER_GUIDE.md:174`, `aura_ai_router.py:22`, `aura_node.py:7202`
- `!ai_router_regen` -> `USER_GUIDE.md:183`, `aura_node.py:7217`
- `!approve` -> `AURA_FINAL_REPORT.md:151`, `USER_GUIDE.md:220`, `aura_node.py:5638`
- `!ar_server_start` -> `USER_GUIDE.md:509`, `aura_node.py:6588`
- `!ar_server_stop` -> `USER_GUIDE.md:510`, `aura_node.py:6604`
- `!ar_start` -> `AURA_FINAL_REPORT.md:168`, `USER_GUIDE.md:509`, `aura_node.py:6588`, `refactored-auraos-upgrades.md:2572`
- `!ar_stop` -> `AURA_FINAL_REPORT.md:169`, `USER_GUIDE.md:510`, `aura_node.py:6604`, `refactored-auraos-upgrades.md:2572`
- `!attention` -> `USER_GUIDE.md:190`, `aura_node.py:5686`
- `!audit` -> `USER_GUIDE.md:205`, `aura_node.py:6184`
- `!backtrack` -> `AURA_FINAL_REPORT.md:143`, `README.md:31`, `USER_GUIDE.md:409`, `arxiv_forager.py:657`
- `!benchmark` -> `README.md:56`, `USER_GUIDE.md:204`, `aura_node.py:2991`, `daily_digest_2026-06-06.md:14`
- `!c` -> `arch_reasoner_accel.rs:14`
- `!calibrate` -> `AURA_FINAL_REPORT.md:163`, `README.md:215`, `USER_GUIDE.md:227`, `aura_node.py:7532`
- `!canvas` -> `aura_savings_dashboard.py:174`
- `!catalyze` -> `AURA_FINAL_REPORT.md:156`, `USER_GUIDE.md:186`, `aura_node.py:7239`, `generate_ai_router.py:356`
- `!codeExts` -> `CODEMAP_TOOL_INTEGRATION_GUIDE.md:506`
- `!cognitive_search` -> `USER_GUIDE.md:189`, `aura_node.py:5655`
- `!commands` -> `USER_GUIDE.md:135`
- `!contingency_spawn` -> `USER_GUIDE.md:232`, `aura_node.py:7006`
- `!converse` -> `AURA_FINAL_REPORT.md:161`, `USER_GUIDE.md:231`, `aura_node.py:7649`
- `!coordinated_reason` -> `USER_GUIDE.md:197`, `aura_node.py:7449`
- `!crystallize` -> `AURA_FINAL_REPORT.md:141`, `USER_GUIDE.md:416`, `aura_node.py:7306`
- `!curiosity_tree` -> `AURA_FINAL_REPORT.md:174`, `USER_GUIDE.md:412`, `aura_node.py:6645`
- `!db_repair` -> `USER_GUIDE.md:513`, `aura_node.py:2991`
- `!doctype` -> `aura_coding_arena/index.html:1`, `aura_efficiency_report.py:124`, `aura_human_agent_arena/index.html:1`
- `!empirical_lab` -> `USER_GUIDE.md:214`, `aura_node.py:6230`
- `!evolve_reasoning` -> `AURA_FINAL_REPORT.md:157`, `USER_GUIDE.md:199`, `aura_node.py:7301`
- `!export` -> `USER_GUIDE.md:511`, `aura_node.py:6008`
- `!fast_path` -> `AURA_FINAL_REPORT.md:173`, `USER_GUIDE.md:188`, `aura_node.py:7391`, `test_aura_functions.py:927`
- `!forage` -> `USER_GUIDE.md:408`, `aura_affordance_directory.py:461`, `aura_capability_lane_registry.py:120`, `aura_node.py:6190`
- `!forage_off` -> `USER_GUIDE.md:414`, `aura_node.py:6582`
- `!forage_on` -> `USER_GUIDE.md:413`, `aura_node.py:6576`
- `!forager_off` -> `USER_GUIDE.md:414`, `aura_node.py:6582`
- `!forager_on` -> `USER_GUIDE.md:413`, `aura_node.py:6576`
- `!fusion` -> `AURA_FINAL_REPORT.md:31`, `USER_GUIDE.md:229`, `aura_fusion.py:384`, `aura_node.py:7518`
- `!heal` -> `aura_node.py:5209`
- `!help` -> `AURA_FINAL_REPORT.md:48`, `SYNTAX_FIXES_APPLIED.md:107`, `USER_GUIDE.md:171`, `aura_node.py:7668`
- `!important` -> `index.html:9`
- `!indus_decrypt` -> `AURA_FINAL_REPORT.md:175`, `USER_GUIDE.md:418`, `aura_node.py:7313`
- `!invalid_base64` -> `test_scientific_memory.py:972`
- `!manifest` -> `AURA_FINAL_REPORT.md:138`, `USER_GUIDE.md:171`, `aura_node.py:7668`
- `!markov` -> `AURA_FINAL_REPORT.md:144`, `USER_GUIDE.md:514`, `aura_node.py:7504`
- `!mesh_status` -> `AURA_FINAL_REPORT.md:167`, `USER_GUIDE.md:508`, `aura_capability_lane_registry.py:158`, `aura_node.py:5649`
- `!meta_analyze` -> `USER_GUIDE.md:200`, `aura_node.py:7352`
- `!meta_reason` -> `AURA_FINAL_REPORT.md:155`, `USER_GUIDE.md:201`, `aura_arch_reasoner.py:93`, `aura_node.py:7377`
- `!optimize` -> `AURA_FINAL_REPORT.md:172`, `USER_GUIDE.md:216`, `aura_node.py:5931`
- `!ping_mesh` -> `AURA_FINAL_REPORT.md:166`, `USER_GUIDE.md:507`, `aura_capability_lane_registry.py:158`, `aura_node.py:5644`
- `!plan` -> `aura_affordance_directory.py:440`, `aura_node.py:5602`
- `!push` -> `USER_GUIDE.md:512`, `aura_node.py:5166`, `test_aura_functions.py:207`
- `!qdkt` -> `aura_affordance_directory.py:356`
- `!r` -> `aura_ephemeral_adapter_registry.py:134`, `aura_graphify_schema.py:160`, `aura_hv_cache.py:373`, `aura_language_data_governance.py:119`
- `!reason` -> `AURA_FINAL_REPORT.md:154`, `USER_GUIDE.md:196`, `aura_node.py:7492`
- `!repair_db` -> `USER_GUIDE.md:513`, `aura_node.py:6979`
- `!research` -> `AURA_FINAL_REPORT.md:142`, `README.md:217`, `USER_GUIDE.md:410`, `aura_affordance_directory.py:461`
- `!review` -> `USER_GUIDE.md:217`, `aura_node.py:6709`, `mistral_gate.py:93`
- `!rollback` -> `USER_GUIDE.md:221`, `aura_node.py:6694`
- `!route` -> `AURA_FINAL_REPORT.md:28`, `AURA_ROUTER.md:213`, `README.md:218`, `USER_GUIDE.md:228`
- `!s` -> `async_palace.py:163`, `aura_mitosis.py:196`, `aura_node.py:1167`, `aura_spvm.py:134`
- `!saturn` -> `AURA_FINAL_REPORT.md:147`, `AuraOS.tex:212`, `Second_Paper_extracted.txt:74`, `USER_GUIDE.md:202`
- `!saturn_heal` -> `AURA_FINAL_REPORT.md:148`, `AURA_REFACTORING_ANALYSIS.md:136`, `AuraOS__A_Polysynthetic_Cognitive_Substrate_for_High-Dimensional_Edge_Orchestration_and_Visual_Code_Topology_extracted.txt:257`, `HOLOGRAPHIC_HEADER_IMPLEMENTATION.md:121`
- `!savings` -> `AURA_FINAL_REPORT.md:162`, `AuraOS.tex:185`, `AuraOS__A_Polysynthetic_Cognitive_Substrate_for_High-Dimensional_Edge_Orchestration_and_Visual_Code_Topology_extracted.txt:220`, `USER_GUIDE.md:230`
- `!scan_topology` -> `USER_GUIDE.md:184`, `aura_node.py:7148`
- `!search_similar` -> `USER_GUIDE.md:411`, `aura_node.py:6618`, `refactored-auraos-upgrades.md:2573`
- `!self_optimize` -> `USER_GUIDE.md:216`, `aura_dynamic_attention.py:209`, `aura_node.py:5931`, `refactored-auraos-upgrades.md:826`
- `!self_reflect` -> `DAILY_DIGEST_Jun7-8_2026.md:19`, `DAILY_DIGEST_Jun7_2026.md:30`, `USER_GUIDE.md:215`, `aura_arch_reasoner.py:223`
- `!settings` -> `README.md:212`, `USER_GUIDE.md:171`, `aura_node.py:7668`, `daily_digest_2026-06-06.md:14`
- `!show` -> `docs/AURA_HUMAN_AGENT_ARENA.md:267`, `tests/test_aura_human_agent_concepts.py:86`
- `!simulate` -> `USER_GUIDE.md:187`, `aura_node.py:7142`, `cognitive_router.py:224`
- `!something` -> `aura_node.py:4969`
- `!srcPos` -> `index.html:122`
- `!stage` -> `AURA_FINAL_REPORT.md:149`, `USER_GUIDE.md:217`, `aura_capability_lane_registry.py:229`, `aura_live_architect.py:2159`
- `!stage_merge` -> `AURA_FINAL_REPORT.md:150`, `USER_GUIDE.md:218`, `aura_capability_lane_registry.py:229`, `aura_live_architect.py:2160`
- `!stage_purge` -> `USER_GUIDE.md:219`, `aura_capability_lane_registry.py:229`, `aura_node.py:6774`
- `!stage_review` -> `USER_GUIDE.md:217`, `aura_capability_lane_registry.py:229`, `aura_node.py:6709`
- `!status` -> `AURA_FINAL_REPORT.md:136`, `SYNTAX_FIXES_APPLIED.md:107`, `aura_node.py:5166`
- `!strategy_buffer_stats` -> `USER_GUIDE.md:198`, `aura_coordinated_solver.py:69`, `aura_node.py:7476`
- `!synthesize` -> `USER_GUIDE.md:417`, `aura_associative_core.py:141`, `aura_node.py:6896`, `test_aura_functions.py:913`
- `!system_audit` -> `USER_GUIDE.md:205`, `aura_node.py:6184`
- `!target_bytes` -> `cognitive_search.rs:72`
- `!test` -> `AuraOS.tex:533`
- `!test_airlock` -> `USER_GUIDE.md:207`, `aura_node.py:5614`
- `!tgtPos` -> `index.html:122`
- `!timeline` -> `USER_GUIDE.md:415`, `aura_node.py:6657`
- `!topology` -> `AURA_FINAL_REPORT.md:48`, `README.md:164`, `SYNTAX_FIXES_APPLIED.md:107`, `USER_GUIDE.md:184`
- `!topology_deep` -> `USER_GUIDE.md:185`, `aura_affordance_directory.py:146`, `aura_node.py:7231`
- `!total` -> `aura_savings_dashboard.py:223`
- `!voice` -> `USER_GUIDE.md:515`, `aura_node.py:7731`

## Navigation Rings

### substrate_core
- `AuraOS__A_Polysynthetic_Cognitive_Substrate_for_High-Dimensional_Edge_Orchestration_and_Visual_Code_Topology.pdf`
- `AuraOS__A_Polysynthetic_Cognitive_Substrate_for_High-Dimensional_Edge_Orchestration_and_Visual_Code_Topology_extracted.txt`
- `aura_core.py`
- `aura_node.py`
- `aura_substrate.py`
- `gateway.py`
- `test_aura_substrate.py`

### cognition_and_memory
- `.mempalace/aura_memory.db.corrupt.bak`
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
- `AURA_ROUTER.md`
- `FRACTAL_LEDGER_IMPLEMENTATION.md`
- `LIQUID_INTERNET_IMPLEMENTATION.md`
- `aura_ai_router.py`
- `aura_anthropic_router.py`
- `aura_blockchain/__init__.py`
- `aura_blockchain/block.py`
- `aura_blockchain/consensus.py`
- `aura_blockchain/demo.py`
- `aura_blockchain/node.py`
- `aura_blockchain/phasor_ledger.py`
- ... 23 more; query CODEMAP.json for exact file cards

### topology_and_navigation
- `aura_codebase_navigator.py`
- `aura_topological_context_anchor.py`
- `aura_topological_scanner.py`
- `aura_topological_scanner.py.bak`
- `aura_topology_analyzer.py`
- `aura_topology_cli.py`
- `aura_topology_density_controller.py`
- `aura_topology_health.py`
- `aura_topology_manager.py`
- `aura_topology_snapshot_builder.py`
- `aura_topology_state_machine.py`
- `aura_topology_sync.py`
- ... 6 more; query CODEMAP.json for exact file cards

### security_and_validation
- `.aura/SECURITY.md`
- `DEEP_AUDIT_REPORT.md`
- `aura_background_auditor.py`
- `aura_cockpit_audit_trail.py`
- `aura_crypto_puf.py`
- `aura_emergent_capability_auditor.py`
- `aura_heal.py`
- `aura_metaharness_audit.py`
- `aura_ojibwe_translation_guard.py`
- `aura_tokenizer_guard.py`
- `aura_validation.py`
- `docs/AURA_EPHEMERAL_SECURITY_MODEL.md`
- ... 7 more; query CODEMAP.json for exact file cards

### interfaces_and_docs
- `.aura/AFFORDANCE_MAP.json`
- `.aura/ARCHITECTURE.md`
- `.aura/AURA.md`
- `.aura/CONVERSE.md`
- `.aura/HERMES_AURA_RULES.md`
- `.aura/MODULE_MANIFEST.json`
- `.aura/OUTPUT_FORMATS.md`
- `.aura/RESEARCH_MANIFEST.json`
- `.aura/ROLES.md`
- `.aura/civic_arena.lexc`
- `.aura/civic_snapshots/federal_acts.json`
- `.aura/civic_snapshots/manitoba_acts.json`
- ... 484 more; query CODEMAP.json for exact file cards

## Hubs

- `aura_node.py` (python_module): 222 symbols, degree 869, ~104110 tokens
- `aura_agent_arena_cli.py` (python_module): 94 symbols, degree 533, ~16059 tokens
- `aura_live_architect.py` (python_module): 84 symbols, degree 531, ~30294 tokens
- `test_scientific_memory.py` (python_module): 126 symbols, degree 517, ~13607 tokens
- `aura_architect_loop.py` (python_module): 72 symbols, degree 489, ~18332 tokens
- `aura_fst_routing.py` (python_module): 35 symbols, degree 422, ~8991 tokens
- `test_aura_functions.py` (python_module): 86 symbols, degree 358, ~9340 tokens
- `aura_scientific_memory.py` (python_module): 45 symbols, degree 341, ~9915 tokens
- `aura_human_agent_arena.py` (python_module): 72 symbols, degree 327, ~22286 tokens
- `aura_music_coding_arena.py` (python_module): 48 symbols, degree 306, ~11812 tokens
- `aura_topological_context_anchor.py` (python_module): 71 symbols, degree 279, ~10851 tokens
- `aura_understand_graph_bridge.py` (python_module): 64 symbols, degree 269, ~9078 tokens

## Topology Integration

- **source**: compiled_deep_topology
- **nodes**: 5880
- **edges**: 12155
- **top_files_by_degree**:
  - `aura_node.py` degree=869 nodes=221 neighbors=`arxiv_forager.py`, `async_palace.py`, `aura_ai_router.py`, `aura_api_rotator.py`
  - `aura_agent_arena_cli.py` degree=533 nodes=95 neighbors=`aura_agent_arena_bridge.py`, `aura_agent_arena_fireworks.py`
  - `aura_live_architect.py` degree=531 nodes=85 neighbors=`aura_architect_loop.py`, `aura_builder_context.py`, `aura_coding_arena_grounding.py`, `aura_coding_arena_workflow.py`
  - `test_scientific_memory.py` degree=517 nodes=120 neighbors=`arxiv_forager.py`, `aura_paper_memory.py`, `aura_scientific_memory.py`, `travel_price_sidecar.py`
  - `aura_architect_loop.py` degree=489 nodes=73 neighbors=`aura_arena_st3gg_codec.py`, `aura_background_workers.py`, `aura_civic_session_store.py`, `aura_codebase_navigator.py`
  - `aura_fst_routing.py` degree=422 nodes=36 neighbors=`aura_architect_loop.py`, `aura_fusion.py`, `aura_graphify_schema.py`, `aura_harness_evolver.py`
  - `test_aura_functions.py` degree=358 nodes=87 neighbors=`arch_reasoner_accel.py`, `async_palace.py`, `aura_arch_reasoner.py`, `aura_associative_core.py`
  - `aura_scientific_memory.py` degree=341 nodes=46 neighbors=`arxiv_forager.py`, `aura_fst_routing.py`, `aura_node.py`, `aura_ojibwe_lexicon_sidecar.py`
  - `aura_human_agent_arena.py` degree=327 nodes=73 neighbors=`aura_affordance_directory.py`, `aura_agent_arena_bridge.py`, `aura_api_rotator.py`, `aura_coding_arena_3d.py`
  - `aura_music_coding_arena.py` degree=306 nodes=49 neighbors=`aura_fst_routing.py`, `aura_lexc.py`, `aura_live_architect.py`, `aura_music_inversion.py`
  - `aura_topological_context_anchor.py` degree=279 nodes=72 neighbors=`aura_coding_arena_grounding.py`, `aura_emergent_capability_auditor.py`, `aura_emergent_potential_repl.py`, `aura_fst_routing.py`
  - `aura_understand_graph_bridge.py` degree=269 nodes=65 neighbors=`aura_cost_telemetry_events.py`, `aura_fst_routing.py`, `aura_ojibwe_dialect_conflict_resolver.py`, `aura_qdkt.py`

## High-Value Symbols

- `ATTTransducer` -> `aura_att_fst_runtime.py:41`
- `AbilityAtom` -> `aura_emergent_potential_repl.py:173`
- `AccountState` -> `aura_blockchain/node.py:27`
- `ActCapsule` -> `aura_architect_loop.py:84`
- `ActionCapsule` -> `aura_liquid_planning_arena.py:112`
- `AdapterMetadata` -> `aura_ephemeral_adapter_registry.py:19`
- `AdaptiveLiquidTimeConstant` -> `liquid_kernel.py:60`, `liquid_math_reference.py:39`
- `AgentIRCompiler` -> `aura_agent_ir_compiler.py:17`
- `AgentIRNode` -> `aura_agent_ir.py:37`
- `AnimacyClass` -> `aura_ojibwe_morph_bridge.py:84`
- `AnthropicRouter` -> `aura_anthropic_router.py:268`
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
- `ArenaBridgeError` -> `aura_agent_arena_errors.py:93`
- `ArenaLease` -> `aura_liquid_planning_arena.py:170`
- `ArenaLink` -> `aura_coding_arena_3d.py:83`
- `ArenaNode` -> `aura_coding_arena_3d.py:62`
- `ArenaPatch` -> `aura_architect_loop.py:207`
- `ArenaResearchIdea` -> `aura_music_coding_arena.py:81`
- `ArenaST3GGCapsule` -> `aura_arena_st3gg_codec.py:55`
- `ArenaST3GGDecision` -> `aura_arena_st3gg_codec.py:43`
- `ArxivPaper` -> `arxiv_forager.py:1186`
- `AssetProperties` -> `aura_vsa_rendering.py:44`
- `AsyncExpertQuantizationEngine` -> `aura_timestep_svd_quantizer.py:337`
- `AsyncMemoryPalace` -> `async_palace.py:380`, `aura_attention_palace.py:43`
- `AthabaskanPositionalParser` -> `aura_positional_parser.py:20`
- `AttentionConfig` -> `aura_dynamic_attention.py:36`
- `AttentionResult` -> `aura_dynamic_attention.py:46`
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
- `AuraFederation` -> `aura_federation.py:100`
- `AuraFusionAgent` -> `aura_fusion.py:89`
- `AuraFusionCoordinator` -> `aura_fusion.py:481`
- `AuraFusionResult` -> `aura_fusion.py:126`
- `AuraGOAPPlanner` -> `aura_goal_planner.py:163`
- `AuraGraftOrchestrator` -> `liquid_attractor_control_plane.py:725`
- `AuraGraphRetrievalPolicy` -> `aura_graph_retrieval_policy.py:17`
- `AuraHardwareProfileRouter` -> `aura_hardware_profile_router.py:17`
- `AuraHolographicManifest` -> `aura_holographic_manifest.py:25`
- `AuraHyperdimensionalCore` -> `aura_core.py:217`, `aura_node.py:928`
- `AuraHyperdimensionalProbeBridge` -> `aura_hyperdimensional_probe_bridge.py:17`
- `AuraJPacket` -> `aura_jspace_codec.py:166`
- `AuraJState` -> `aura_jspace_codec.py:188`
- `AuraLexc` -> `aura_lexc.py:127`
- `AuraMCPGateway` -> `aura_mcp_gateway.py:129`
- `AuraMCPTool` -> `aura_mcp_gateway.py:66`
- `AuraMCPToolResult` -> `aura_mcp_gateway.py:91`
- `AuraMeshSwarm` -> `aura_mesh.py:475`
- `AuraMetaHarnessAuditor` -> `aura_metaharness_audit.py:118`
- `AuraMitosisEngine` -> `aura_mitosis.py:21`
- `AuraModelProbeLedger` -> `aura_model_probe_ledger.py:109`
- `AuraNativeCockpit` -> `aura_native_cockpit.py:39`
- `AuraNativePFST` -> `aura_node.py:752`
- `AuraNeuroSymbolicReasoner` -> `aura_nesy_sat_reasoner.py:50`
- `AuraNode` -> `aura_blockchain/node.py:32`
- `AuraOntologyCircuit` -> `aura_ontology_circuit.py:54`
