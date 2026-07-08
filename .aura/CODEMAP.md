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

- **file_count**: 314
- **total_bytes**: 71258017
- **text_tokens_est**: 3482074
- **role_counts**: {'binary_artifact': 13, 'interface_surface': 1, 'knowledge_artifact': 52, 'native_accelerator': 8, 'operator_script': 5, 'python_module': 200, 'schema_or_lexicon': 13, 'support_file': 22}
- **topology_nodes**: 2203
- **topology_edges**: 2197
- **topology_source**: existing_topology_json
- **elapsed_ms**: 31685.86
- **last_incremental_refresh_unix**: 1783549551

## Coverage

- **included_file_count**: 314
- **policy**: all files under root except skipped runtime/cache dirs and generated CODEMAP outputs
- **excluded_generated_map_files**: `.aura/CODEMAP.json`, `.aura/CODEMAP.md`
- **skipped_dir_file_counts**: `.git`=535, `.pytest_cache`=5, `Aura_Memory`=11, `__pycache__`=150

## Command Index

- `!Aura_Sandbox` -> `.gitignore:42`
- `!CORE_AXIOM_VALID` -> `aura_nesy_sat_reasoner.py:280`
- `!DOCTYPE` -> `aura_savings_dashboard.py:49`, `index.html:1`
- `!ai_route` -> `USER_GUIDE.md:173`, `aura_ai_router.py:22`, `aura_node.py:6868`
- `!ai_router_regen` -> `USER_GUIDE.md:182`, `aura_node.py:6883`
- `!approve` -> `AURA_FINAL_REPORT.md:151`, `USER_GUIDE.md:217`, `aura_node.py:5515`
- `!ar_server_start` -> `USER_GUIDE.md:482`, `aura_node.py:6289`
- `!ar_server_stop` -> `USER_GUIDE.md:483`, `aura_node.py:6305`
- `!ar_start` -> `AURA_FINAL_REPORT.md:168`, `USER_GUIDE.md:482`, `aura_node.py:6289`, `refactored-auraos-upgrades.md:2572`
- `!ar_stop` -> `AURA_FINAL_REPORT.md:169`, `USER_GUIDE.md:483`, `aura_node.py:6305`, `refactored-auraos-upgrades.md:2572`
- `!attention` -> `USER_GUIDE.md:189`, `aura_node.py:5563`
- `!audit` -> `USER_GUIDE.md:204`, `aura_node.py:6070`
- `!backtrack` -> `AURA_FINAL_REPORT.md:143`, `README.md:29`, `USER_GUIDE.md:382`, `arxiv_forager.py:626`
- `!benchmark` -> `README.md:37`, `USER_GUIDE.md:203`, `aura_node.py:2988`, `daily_digest_2026-06-06.md:14`
- `!c` -> `arch_reasoner_accel.rs:14`
- `!calibrate` -> `AURA_FINAL_REPORT.md:163`, `README.md:138`, `USER_GUIDE.md:224`, `aura_node.py:7198`
- `!canvas` -> `aura_savings_dashboard.py:174`
- `!catalyze` -> `AURA_FINAL_REPORT.md:156`, `USER_GUIDE.md:185`, `aura_node.py:6905`, `generate_ai_router.py:356`
- `!codeExts` -> `CODEMAP_TOOL_INTEGRATION_GUIDE.md:506`
- `!cognitive_search` -> `USER_GUIDE.md:188`, `aura_node.py:5532`
- `!commands` -> `USER_GUIDE.md:134`
- `!contingency_spawn` -> `USER_GUIDE.md:229`, `aura_node.py:6672`
- `!converse` -> `AURA_FINAL_REPORT.md:161`, `USER_GUIDE.md:228`, `aura_node.py:7315`
- `!coordinated_reason` -> `USER_GUIDE.md:196`, `aura_node.py:7115`
- `!crystallize` -> `AURA_FINAL_REPORT.md:141`, `USER_GUIDE.md:389`, `aura_node.py:6972`
- `!curiosity_tree` -> `AURA_FINAL_REPORT.md:174`, `USER_GUIDE.md:385`, `aura_node.py:6346`
- `!db_repair` -> `USER_GUIDE.md:486`, `aura_node.py:2988`
- `!evolve_reasoning` -> `AURA_FINAL_REPORT.md:157`, `USER_GUIDE.md:198`, `aura_node.py:6967`
- `!export` -> `USER_GUIDE.md:484`, `aura_node.py:5890`
- `!fast_path` -> `AURA_FINAL_REPORT.md:173`, `USER_GUIDE.md:187`, `aura_node.py:7057`, `test_aura_functions.py:927`
- `!forage` -> `USER_GUIDE.md:381`, `aura_node.py:6076`, `refactored-auraos-upgrades.md:2573`
- `!forage_off` -> `USER_GUIDE.md:387`, `aura_node.py:6283`
- `!forage_on` -> `USER_GUIDE.md:386`, `aura_node.py:6277`
- `!forager_off` -> `USER_GUIDE.md:387`, `aura_node.py:6283`
- `!forager_on` -> `USER_GUIDE.md:386`, `aura_node.py:6277`
- `!fusion` -> `AURA_FINAL_REPORT.md:31`, `USER_GUIDE.md:226`, `aura_fusion.py:384`, `aura_node.py:7184`
- `!heal` -> `aura_node.py:5139`
- `!help` -> `AURA_FINAL_REPORT.md:48`, `SYNTAX_FIXES_APPLIED.md:107`, `USER_GUIDE.md:170`, `aura_node.py:7325`
- `!important` -> `index.html:9`
- `!indus_decrypt` -> `AURA_FINAL_REPORT.md:175`, `USER_GUIDE.md:391`, `aura_node.py:6979`
- `!invalid_base64` -> `test_scientific_memory.py:941`
- `!manifest` -> `AURA_FINAL_REPORT.md:138`, `USER_GUIDE.md:170`, `aura_node.py:7325`
- `!markov` -> `AURA_FINAL_REPORT.md:144`, `USER_GUIDE.md:487`, `aura_node.py:7170`
- `!mesh_status` -> `AURA_FINAL_REPORT.md:167`, `USER_GUIDE.md:481`, `aura_node.py:5526`
- `!meta_analyze` -> `USER_GUIDE.md:199`, `aura_node.py:7018`
- `!meta_reason` -> `AURA_FINAL_REPORT.md:155`, `USER_GUIDE.md:200`, `aura_arch_reasoner.py:93`, `aura_node.py:7043`
- `!optimize` -> `AURA_FINAL_REPORT.md:172`, `USER_GUIDE.md:213`, `aura_node.py:5813`
- `!ping_mesh` -> `AURA_FINAL_REPORT.md:166`, `USER_GUIDE.md:480`, `aura_node.py:5521`
- `!plan` -> `aura_node.py:5479`
- `!push` -> `USER_GUIDE.md:485`, `aura_node.py:5096`, `test_aura_functions.py:207`
- `!r` -> `aura_graphify_schema.py:160`, `aura_hv_cache.py:373`, `aura_lexc.py:100`, `aura_savings_dashboard.py:228`
- `!reason` -> `AURA_FINAL_REPORT.md:154`, `USER_GUIDE.md:195`, `aura_node.py:7158`
- `!repair_db` -> `USER_GUIDE.md:486`, `aura_node.py:6645`
- `!research` -> `AURA_FINAL_REPORT.md:142`, `README.md:140`, `USER_GUIDE.md:383`, `aura_node.py:6102`
- `!review` -> `USER_GUIDE.md:214`, `aura_node.py:6410`, `mistral_gate.py:93`
- `!rollback` -> `USER_GUIDE.md:218`, `aura_node.py:6395`
- `!route` -> `AURA_FINAL_REPORT.md:28`, `AURA_ROUTER.md:213`, `README.md:141`, `USER_GUIDE.md:225`
- `!s` -> `async_palace.py:162`, `aura_mitosis.py:207`, `aura_node.py:1154`, `aura_spvm.py:134`
- `!saturn` -> `AURA_FINAL_REPORT.md:147`, `AuraOS.tex:212`, `Second_Paper_extracted.txt:74`, `USER_GUIDE.md:201`
- `!saturn_heal` -> `AURA_FINAL_REPORT.md:148`, `AURA_REFACTORING_ANALYSIS.md:136`, `AuraOS__A_Polysynthetic_Cognitive_Substrate_for_High-Dimensional_Edge_Orchestration_and_Visual_Code_Topology_extracted.txt:257`, `HOLOGRAPHIC_HEADER_IMPLEMENTATION.md:121`
- `!savings` -> `AURA_FINAL_REPORT.md:162`, `AuraOS.tex:185`, `AuraOS__A_Polysynthetic_Cognitive_Substrate_for_High-Dimensional_Edge_Orchestration_and_Visual_Code_Topology_extracted.txt:220`, `USER_GUIDE.md:227`
- `!scan_topology` -> `USER_GUIDE.md:183`, `aura_node.py:6814`
- `!search_similar` -> `USER_GUIDE.md:384`, `aura_node.py:6319`, `refactored-auraos-upgrades.md:2573`
- `!self_optimize` -> `USER_GUIDE.md:213`, `aura_dynamic_attention.py:209`, `aura_node.py:5813`, `refactored-auraos-upgrades.md:826`
- `!self_reflect` -> `DAILY_DIGEST_Jun7-8_2026.md:19`, `DAILY_DIGEST_Jun7_2026.md:30`, `USER_GUIDE.md:212`, `aura_arch_reasoner.py:230`
- `!settings` -> `README.md:135`, `USER_GUIDE.md:170`, `aura_node.py:7325`, `daily_digest_2026-06-06.md:14`
- `!simulate` -> `USER_GUIDE.md:186`, `aura_node.py:6808`, `cognitive_router.py:224`
- `!something` -> `aura_node.py:4899`
- `!srcPos` -> `index.html:120`
- `!stage` -> `AURA_FINAL_REPORT.md:149`, `USER_GUIDE.md:214`, `aura_live_architect.py:1131`, `aura_node.py:6410`
- `!stage_merge` -> `AURA_FINAL_REPORT.md:150`, `USER_GUIDE.md:215`, `aura_live_architect.py:1132`, `aura_node.py:6440`
- `!stage_purge` -> `USER_GUIDE.md:216`, `aura_node.py:6440`
- `!stage_review` -> `USER_GUIDE.md:214`, `aura_node.py:6410`
- `!status` -> `AURA_FINAL_REPORT.md:136`, `SYNTAX_FIXES_APPLIED.md:107`, `aura_node.py:5096`
- `!strategy_buffer_stats` -> `USER_GUIDE.md:197`, `aura_coordinated_solver.py:67`, `aura_node.py:7142`
- `!synthesize` -> `USER_GUIDE.md:390`, `aura_associative_core.py:141`, `aura_node.py:6562`, `test_aura_functions.py:913`
- `!system_audit` -> `USER_GUIDE.md:204`, `aura_node.py:6070`
- `!target_bytes` -> `cognitive_search.rs:72`
- `!test` -> `AuraOS.tex:533`
- `!test_airlock` -> `USER_GUIDE.md:205`, `aura_node.py:5491`
- `!tgtPos` -> `index.html:120`
- `!timeline` -> `USER_GUIDE.md:388`, `aura_node.py:6358`
- `!topology` -> `AURA_FINAL_REPORT.md:48`, `README.md:87`, `SYNTAX_FIXES_APPLIED.md:107`, `USER_GUIDE.md:183`
- `!topology_deep` -> `USER_GUIDE.md:184`, `aura_node.py:6897`
- `!total` -> `aura_savings_dashboard.py:223`
- `!voice` -> `USER_GUIDE.md:488`, `aura_node.py:7386`

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
- `aura_cognitive_synthesizer.py`
- `aura_dream_engine.py`
- `aura_dream_retrieval.py`
- `aura_dynamic_attention.py`
- ... 13 more; query CODEMAP.json for exact file cards

### mesh_and_routing
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
- `aura_fractal_ledger.py`
- ... 16 more; query CODEMAP.json for exact file cards

### topology_and_navigation
- `aura_codebase_navigator.py`
- `aura_topological_scanner.py`
- `aura_topological_scanner.py.bak`
- `aura_topology_analyzer.py`
- `aura_topology_manager.py`
- `aura_topology_sync.py`
- `aura_topology_ws_bridge.py`
- `spatial_mapper.py`
- `topology_map.json`

### security_and_validation
- `.aura/SECURITY.md`
- `DEEP_AUDIT_REPORT.md`
- `aura_background_auditor.py`
- `aura_crypto_puf.py`
- `aura_heal.py`
- `aura_metaharness_audit.py`
- `aura_tokenizer_guard.py`
- `aura_validation.py`
- `forged_roots_audit.md`
- `symbolic_shield.py`
- `test_aura_tokenizer_guard.py`

### interfaces_and_docs
- `.aura/ARCHITECTURE.md`
- `.aura/AURA.md`
- `.aura/CONVERSE.md`
- `.aura/OUTPUT_FORMATS.md`
- `.aura/ROLES.md`
- `.aura/understand_graph.json`
- `.aura/understand_graph_diff.json`
- `.aura/understand_graph_tour.json`
- `.aura_backup.bak`
- `.aura_forager_backup.bak`
- `.aura_hdc_backup.bak`
- `.aura_node_backup.bak`
- ... 222 more; query CODEMAP.json for exact file cards

## Hubs

- `aura_node.py` (python_module): 80 symbols, degree 432, ~98530 tokens
- `aura_scientific_memory.py` (python_module): 45 symbols, degree 265, ~9915 tokens
- `test_scientific_memory.py` (python_module): 80 symbols, degree 217, ~12292 tokens
- `test_aura_functions.py` (python_module): 80 symbols, degree 184, ~9340 tokens
- `aura_substrate.py` (python_module): 27 symbols, degree 116, ~6261 tokens
- `aura_codebase_navigator.py` (python_module): 34 symbols, degree 103, ~9528 tokens
- `aura_router.py` (python_module): 29 symbols, degree 94, ~7815 tokens
- `aura_resonant_test_oracle.py` (python_module): 21 symbols, degree 91, ~3594 tokens
- `aura_skillweaver.py` (python_module): 27 symbols, degree 90, ~9349 tokens
- `aura_proxy_benchmark.py` (python_module): 27 symbols, degree 85, ~7830 tokens
- `aura_api_rotator.py` (python_module): 24 symbols, degree 85, ~3881 tokens
- `test_synthesis_upgrades.py` (python_module): 51 symbols, degree 84, ~4829 tokens

## Topology Integration

- **source**: existing_topology_json
- **nodes**: 2203
- **edges**: 2197
- **top_files_by_degree**:
  - `aura_node.py` degree=432 nodes=219 neighbors=`arxiv_forager.py`, `async_palace.py`, `aura_api_rotator.py`, `aura_arch_reasoner.py`
  - `aura_scientific_memory.py` degree=265 nodes=46 neighbors=`arxiv_forager.py`, `aura_fst_routing.py`, `aura_nesy_unit_interval.py`, `aura_node.py`
  - `test_scientific_memory.py` degree=217 nodes=82 neighbors=`arxiv_forager.py`, `aura_scientific_memory.py`, `vsa_resonator.py`
  - `test_aura_functions.py` degree=184 nodes=87 neighbors=`arch_reasoner_accel.py`, `async_palace.py`, `aura_arch_reasoner.py`, `aura_associative_core.py`
  - `aura_substrate.py` degree=116 nodes=28 neighbors=`aura_codebase_navigator.py`, `aura_converse.py`, `aura_fst_routing.py`, `aura_llm_egress.py`
  - `aura_codebase_navigator.py` degree=103 nodes=31 neighbors=`aura_api_rotator.py`, `aura_codemap_auto_refresh.py`, `aura_fst_routing.py`, `aura_savings_db.py`
  - `aura_router.py` degree=94 nodes=29 neighbors=`aura_converse.py`, `aura_llm_egress.py`, `aura_matrix_benchmark.py`, `aura_pricing.py`
  - `aura_resonant_test_oracle.py` degree=91 nodes=24 neighbors=`aura_api_rotator.py`, `aura_node.py`, `aura_skillweaver.py`, `test_resonant_oracle.py`
  - `aura_skillweaver.py` degree=90 nodes=25 neighbors=`aura_api_rotator.py`, `aura_fst_routing.py`, `aura_node.py`, `aura_qdkt.py`
  - `aura_proxy_benchmark.py` degree=85 nodes=28 neighbors=`aura_api_rotator.py`, `aura_llm_egress.py`, `aura_matrix_benchmark.py`, `aura_router.py`
  - `aura_api_rotator.py` degree=85 nodes=22 neighbors=`aura_ai_router.py`, `aura_anthropic_router.py`, `aura_benchmark_sandbox.py`, `aura_codebase_navigator.py`
  - `test_synthesis_upgrades.py` degree=84 nodes=52 neighbors=`aura_arch_reasoner.py`, `aura_associative_core.py`, `aura_heal.py`, `aura_node.py`

## High-Value Symbols

- `AccountState` -> `aura_blockchain/node.py:27`
- `ActCapsule` -> `aura_architect_loop.py:84`
- `ActionCapsule` -> `aura_liquid_planning_arena.py:112`
- `AdaptiveLiquidTimeConstant` -> `liquid_kernel.py:60`, `liquid_math_reference.py:39`
- `AnthropicRouter` -> `aura_anthropic_router.py:268`
- `ArXivForager` -> `arxiv_forager.py:81`
- `ArchitectBuilderBridge` -> `aura_live_architect.py:1003`
- `ArchitectCouncilDecision` -> `aura_live_architect.py:81`
- `ArchitectExecutionResult` -> `aura_architect_loop.py:286`
- `ArchitectFusionCouncil` -> `aura_live_architect.py:808`
- `ArchitectFusionLoop` -> `aura_architect_loop.py:1741`
- `ArchitectLedgerRecord` -> `aura_architect_loop.py:253`
- `ArchitectLoopResult` -> `aura_architect_loop.py:268`
- `ArchitectModelProfile` -> `aura_live_architect.py:56`
- `ArchitectModelRouter` -> `aura_live_architect.py:596`
- `ArenaLease` -> `aura_liquid_planning_arena.py:170`
- `ArenaPatch` -> `aura_architect_loop.py:206`
- `ArxivPaper` -> `arxiv_forager.py:988`
- `AssetProperties` -> `aura_vsa_rendering.py:44`
- `AsyncExpertQuantizationEngine` -> `aura_timestep_svd_quantizer.py:337`
- `AsyncMemoryPalace` -> `async_palace.py:379`, `aura_attention_palace.py:43`
- `AthabaskanPositionalParser` -> `aura_positional_parser.py:20`
- `AttentionConfig` -> `aura_dynamic_attention.py:36`
- `AttentionResult` -> `aura_dynamic_attention.py:46`
- `AuraARWebSocketServer` -> `aura_topology_ws_bridge.py:360`
- `AuraArchReasoner` -> `aura_arch_reasoner.py:31`
- `AuraAssociativeCore` -> `aura_associative_core.py:30`
- `AuraCodingArenaRouter` -> `aura_fst_routing.py:399`
- `AuraCognitiveSynthesizer` -> `aura_cognitive_synthesizer.py:24`
- `AuraCompilerParser` -> `aura_node.py:721`
- `AuraConsensus` -> `aura_blockchain/consensus.py:105`
- `AuraContextCrusher` -> `aura_context_crusher.py:231`
- `AuraDependencyScanner` -> `aura_node.py:1092`
- `AuraDreamEngine` -> `aura_dream_engine.py:54`
- `AuraEpistemicIngestGateway` -> `aura_epistemic_ingest.py:27`
- `AuraFederation` -> `aura_federation.py:100`
- `AuraFusionAgent` -> `aura_fusion.py:89`
- `AuraFusionCoordinator` -> `aura_fusion.py:481`
- `AuraFusionResult` -> `aura_fusion.py:126`
- `AuraGOAPPlanner` -> `aura_goal_planner.py:163`
- `AuraGraftOrchestrator` -> `liquid_attractor_control_plane.py:725`
- `AuraHolographicManifest` -> `aura_holographic_manifest.py:25`
- `AuraHyperdimensionalCore` -> `aura_core.py:194`, `aura_node.py:915`
- `AuraLexc` -> `aura_lexc.py:110`
- `AuraMCPGateway` -> `aura_mcp_gateway.py:129`
- `AuraMCPTool` -> `aura_mcp_gateway.py:66`
- `AuraMCPToolResult` -> `aura_mcp_gateway.py:91`
- `AuraMeshSwarm` -> `aura_mesh.py:473`
- `AuraMetaHarnessAuditor` -> `aura_metaharness_audit.py:118`
- `AuraMitosisEngine` -> `aura_mitosis.py:19`
- `AuraModelProbeLedger` -> `aura_model_probe_ledger.py:109`
- `AuraNativePFST` -> `aura_node.py:739`
- `AuraNeuroSymbolicReasoner` -> `aura_nesy_sat_reasoner.py:50`
- `AuraNode` -> `aura_blockchain/node.py:32`
- `AuraOntologyCircuit` -> `aura_ontology_circuit.py:54`
- `AuraOrchestrationLobe` -> `aura_core.py:170`
- `AuraPanelOutput` -> `aura_fusion.py:112`
- `AuraPhaseCapsule` -> `aura_phase_capsule.py:27`
- `AuraPluginManifest` -> `aura_plugin_registry.py:60`
- `AuraPluginRegistry` -> `aura_plugin_registry.py:104`
- `AuraPrivacyIOOrchestrator` -> `aura_privacy_io.py:19`
- `AuraResonanceEgressGate` -> `aura_paper_memory.py:399`
- `AuraRustWasmBridge` -> `aura_wasm_bridge.py:61`
- `AuraSafetySentinel` -> `aura_node.py:1109`
- `AuraSandbox` -> `aura_node.py:1031`
- `AuraSkill` -> `aura_skillweaver.py:47`
- `AuraSkillWeaver` -> `aura_skillweaver.py:593`
- `AuraSovereignPatcher` -> `aura_patcher.py:13`
- `AuraSpectralMemoryOrchestrator` -> `aura_spectral_memory.py:16`
- `AuraSpikingGovernor` -> `aura_governor.py:21`, `aura_node.py:801`
- `AuraSubstrate` -> `aura_substrate.py:504`
- `AuraSuperpositionEngine` -> `aura_node.py:1274`
- `AuraThermodynamicPUF` -> `aura_crypto_puf.py:21`
- `AuraUnderstandGraph` -> `aura_understand_graph_bridge.py:201`
- `AuraVisualCortex` -> `aura_background_auditor.py:20`
- `AuraWasmHypervisor` -> `gateway.py:509`
- `AuraWebForager` -> `aura_node.py:1071`
- `AuraZeroDiskIOCache` -> `aura_node.py:226`
- `AutoRouter` -> `aura_router.py:222`
- `BackgroundWorker` -> `aura_background_workers.py:67`
