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

- **file_count**: 293
- **total_bytes**: 66729310
- **text_tokens_est**: 2394920
- **role_counts**: {'binary_artifact': 11, 'interface_surface': 1, 'knowledge_artifact': 51, 'native_accelerator': 8, 'operator_script': 5, 'python_module': 184, 'schema_or_lexicon': 11, 'support_file': 22}
- **topology_nodes**: 2948
- **topology_edges**: 6230
- **topology_source**: compiled_deep_topology
- **elapsed_ms**: 6340.13

## Coverage

- **included_file_count**: 293
- **policy**: all files under root except skipped runtime/cache dirs and generated CODEMAP outputs
- **excluded_generated_map_files**: `.aura/CODEMAP.json`, `.aura/CODEMAP.md`
- **skipped_dir_file_counts**: `.git`=114, `.pytest_cache`=5, `Aura_Memory`=6, `__pycache__`=386

## Command Index

- `!Aura_Sandbox` -> `.gitignore:42`
- `!CORE_AXIOM_VALID` -> `aura_nesy_sat_reasoner.py:280`
- `!DOCTYPE` -> `aura_savings_dashboard.py:49`, `index.html:1`
- `!ai_route` -> `USER_GUIDE.md:173`, `aura_ai_router.py:22`, `aura_node.py:6886`
- `!ai_router_regen` -> `USER_GUIDE.md:182`, `aura_node.py:6901`
- `!approve` -> `AURA_FINAL_REPORT.md:151`, `USER_GUIDE.md:217`, `aura_node.py:5515`
- `!ar_server_start` -> `USER_GUIDE.md:482`, `aura_node.py:6273`
- `!ar_server_stop` -> `USER_GUIDE.md:483`, `aura_node.py:6289`
- `!ar_start` -> `AURA_FINAL_REPORT.md:168`, `USER_GUIDE.md:482`, `aura_node.py:6273`, `refactored-auraos-upgrades.md:2572`
- `!ar_stop` -> `AURA_FINAL_REPORT.md:169`, `USER_GUIDE.md:483`, `aura_node.py:6289`, `refactored-auraos-upgrades.md:2572`
- `!attention` -> `USER_GUIDE.md:189`, `aura_node.py:5563`
- `!audit` -> `USER_GUIDE.md:204`, `aura_node.py:6070`
- `!backtrack` -> `AURA_FINAL_REPORT.md:143`, `README.md:98`, `USER_GUIDE.md:382`, `arxiv_forager.py:584`
- `!benchmark` -> `README.md:26`, `USER_GUIDE.md:203`, `aura_node.py:2988`, `daily_digest_2026-06-06.md:14`
- `!c` -> `arch_reasoner_accel.rs:14`
- `!calibrate` -> `AURA_FINAL_REPORT.md:163`, `README.md:97`, `USER_GUIDE.md:224`, `aura_node.py:7216`
- `!canvas` -> `aura_savings_dashboard.py:174`
- `!catalyze` -> `AURA_FINAL_REPORT.md:156`, `USER_GUIDE.md:185`, `aura_node.py:6923`, `generate_ai_router.py:356`
- `!codeExts` -> `CODEMAP_TOOL_INTEGRATION_GUIDE.md:506`
- `!cognitive_search` -> `USER_GUIDE.md:188`, `aura_node.py:5532`
- `!commands` -> `USER_GUIDE.md:134`
- `!contingency_spawn` -> `USER_GUIDE.md:229`, `aura_node.py:6690`
- `!converse` -> `AURA_FINAL_REPORT.md:161`, `USER_GUIDE.md:228`, `aura_node.py:7333`
- `!coordinated_reason` -> `USER_GUIDE.md:196`, `aura_node.py:7133`
- `!crystallize` -> `AURA_FINAL_REPORT.md:141`, `USER_GUIDE.md:389`, `aura_node.py:6990`
- `!curiosity_tree` -> `AURA_FINAL_REPORT.md:174`, `USER_GUIDE.md:385`, `aura_node.py:6330`
- `!db_repair` -> `USER_GUIDE.md:486`, `aura_node.py:2988`
- `!evolve_reasoning` -> `AURA_FINAL_REPORT.md:157`, `USER_GUIDE.md:198`, `aura_node.py:6985`
- `!export` -> `USER_GUIDE.md:484`, `aura_node.py:5890`
- `!fast_path` -> `AURA_FINAL_REPORT.md:173`, `USER_GUIDE.md:187`, `aura_node.py:7075`, `test_aura_functions.py:927`
- `!forage` -> `USER_GUIDE.md:381`, `aura_node.py:6076`, `refactored-auraos-upgrades.md:2573`
- `!forage_off` -> `USER_GUIDE.md:387`, `aura_node.py:6267`
- `!forage_on` -> `USER_GUIDE.md:386`, `aura_node.py:6261`
- `!forager_off` -> `USER_GUIDE.md:387`, `aura_node.py:6267`
- `!forager_on` -> `USER_GUIDE.md:386`, `aura_node.py:6261`
- `!fusion` -> `AURA_FINAL_REPORT.md:31`, `USER_GUIDE.md:226`, `aura_fusion.py:384`, `aura_node.py:7202`
- `!heal` -> `aura_node.py:5139`
- `!help` -> `AURA_FINAL_REPORT.md:48`, `SYNTAX_FIXES_APPLIED.md:107`, `USER_GUIDE.md:170`, `aura_node.py:7343`
- `!important` -> `index.html:9`
- `!indus_decrypt` -> `AURA_FINAL_REPORT.md:175`, `USER_GUIDE.md:391`, `aura_node.py:6997`
- `!invalid_base64` -> `test_scientific_memory.py:941`
- `!manifest` -> `AURA_FINAL_REPORT.md:138`, `USER_GUIDE.md:170`, `aura_node.py:7343`
- `!markov` -> `AURA_FINAL_REPORT.md:144`, `USER_GUIDE.md:487`, `aura_node.py:7188`
- `!mesh_status` -> `AURA_FINAL_REPORT.md:167`, `USER_GUIDE.md:481`, `aura_node.py:5526`
- `!meta_analyze` -> `USER_GUIDE.md:199`, `aura_node.py:7036`
- `!meta_reason` -> `AURA_FINAL_REPORT.md:155`, `USER_GUIDE.md:200`, `aura_arch_reasoner.py:90`, `aura_node.py:7061`
- `!optimize` -> `AURA_FINAL_REPORT.md:172`, `USER_GUIDE.md:213`, `aura_node.py:5813`
- `!ping_mesh` -> `AURA_FINAL_REPORT.md:166`, `USER_GUIDE.md:480`, `aura_node.py:5521`
- `!plan` -> `aura_node.py:5479`
- `!push` -> `USER_GUIDE.md:485`, `aura_node.py:5096`, `test_aura_functions.py:207`
- `!r` -> `aura_hv_cache.py:373`, `aura_lexc.py:94`, `aura_savings_dashboard.py:228`, `aura_substrate.py:134`
- `!reason` -> `AURA_FINAL_REPORT.md:154`, `USER_GUIDE.md:195`, `aura_node.py:7176`
- `!repair_db` -> `USER_GUIDE.md:486`, `aura_node.py:6663`
- `!research` -> `AURA_FINAL_REPORT.md:142`, `README.md:99`, `USER_GUIDE.md:383`, `aura_node.py:6102`
- `!review` -> `USER_GUIDE.md:214`, `aura_node.py:6394`, `mistral_gate.py:80`
- `!rollback` -> `USER_GUIDE.md:218`, `aura_node.py:6379`
- `!route` -> `AURA_FINAL_REPORT.md:28`, `AURA_ROUTER.md:213`, `README.md:100`, `USER_GUIDE.md:225`
- `!s` -> `async_palace.py:162`, `aura_mitosis.py:204`, `aura_node.py:1154`, `aura_spvm.py:131`
- `!saturn` -> `AURA_FINAL_REPORT.md:147`, `AuraOS.tex:212`, `Second_Paper_extracted.txt:74`, `USER_GUIDE.md:201`
- `!saturn_heal` -> `AURA_FINAL_REPORT.md:148`, `AURA_REFACTORING_ANALYSIS.md:136`, `AuraOS__A_Polysynthetic_Cognitive_Substrate_for_High-Dimensional_Edge_Orchestration_and_Visual_Code_Topology_extracted.txt:257`, `HOLOGRAPHIC_HEADER_IMPLEMENTATION.md:121`
- `!savings` -> `AURA_FINAL_REPORT.md:162`, `AuraOS.tex:185`, `AuraOS__A_Polysynthetic_Cognitive_Substrate_for_High-Dimensional_Edge_Orchestration_and_Visual_Code_Topology_extracted.txt:220`, `USER_GUIDE.md:227`
- `!scan_topology` -> `USER_GUIDE.md:183`, `aura_node.py:6832`
- `!search_similar` -> `USER_GUIDE.md:384`, `aura_node.py:6303`, `refactored-auraos-upgrades.md:2573`
- `!self_optimize` -> `USER_GUIDE.md:213`, `aura_dynamic_attention.py:210`, `aura_node.py:5813`, `refactored-auraos-upgrades.md:826`
- `!self_reflect` -> `DAILY_DIGEST_Jun7-8_2026.md:19`, `DAILY_DIGEST_Jun7_2026.md:30`, `USER_GUIDE.md:212`, `aura_arch_reasoner.py:227`
- `!settings` -> `README.md:94`, `USER_GUIDE.md:170`, `aura_node.py:7343`, `daily_digest_2026-06-06.md:14`
- `!simulate` -> `USER_GUIDE.md:186`, `aura_node.py:6826`, `cognitive_router.py:221`
- `!something` -> `aura_node.py:4899`
- `!srcPos` -> `index.html:120`
- `!stage` -> `AURA_FINAL_REPORT.md:149`, `USER_GUIDE.md:214`, `aura_live_architect.py:1129`, `aura_node.py:6394`
- `!stage_merge` -> `AURA_FINAL_REPORT.md:150`, `USER_GUIDE.md:215`, `aura_live_architect.py:1130`, `aura_node.py:6424`
- `!stage_purge` -> `USER_GUIDE.md:216`, `aura_node.py:6424`
- `!stage_review` -> `USER_GUIDE.md:214`, `aura_node.py:6394`
- `!status` -> `AURA_FINAL_REPORT.md:136`, `SYNTAX_FIXES_APPLIED.md:107`, `aura_node.py:5096`
- `!strategy_buffer_stats` -> `USER_GUIDE.md:197`, `aura_coordinated_solver.py:64`, `aura_node.py:7160`
- `!synthesize` -> `USER_GUIDE.md:390`, `aura_associative_core.py:138`, `aura_node.py:6580`, `test_aura_functions.py:913`
- `!system_audit` -> `USER_GUIDE.md:204`, `aura_node.py:6070`
- `!target_bytes` -> `cognitive_search.rs:72`
- `!test` -> `AuraOS.tex:533`
- `!test_airlock` -> `USER_GUIDE.md:205`, `aura_node.py:5491`
- `!tgtPos` -> `index.html:120`
- `!timeline` -> `USER_GUIDE.md:388`, `aura_node.py:6342`
- `!topology` -> `AURA_FINAL_REPORT.md:48`, `README.md:46`, `SYNTAX_FIXES_APPLIED.md:107`, `USER_GUIDE.md:183`
- `!topology_deep` -> `USER_GUIDE.md:184`, `aura_node.py:6915`
- `!total` -> `aura_savings_dashboard.py:223`
- `!voice` -> `USER_GUIDE.md:488`, `aura_node.py:7404`

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
- ... 15 more; query CODEMAP.json for exact file cards

### topology_and_navigation
- `aura_codebase_navigator.py`
- `aura_topological_scanner.py`
- `aura_topological_scanner.py.bak`
- `aura_topology_analyzer.py`
- `aura_topology_manager.py`
- `aura_topology_ws_bridge.py`
- `spatial_mapper.py`
- `topology_map.json`

### security_and_validation
- `.aura/SECURITY.md`
- `DEEP_AUDIT_REPORT.md`
- `aura_background_auditor.py`
- `aura_crypto_puf.py`
- `aura_heal.py`
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
- `.aura/pricing.json`
- `.aura_backup.bak`
- `.aura_forager_backup.bak`
- `.aura_hdc_backup.bak`
- `.aura_node_backup.bak`
- `.aura_pfst_backup.bak`
- `.gitignore`
- ... 204 more; query CODEMAP.json for exact file cards

## Hubs

- `aura_node.py` (python_module): 222 symbols, degree 891, ~98869 tokens
- `aura_architect_loop.py` (python_module): 67 symbols, degree 576, ~16676 tokens
- `test_scientific_memory.py` (python_module): 114 symbols, degree 474, ~11741 tokens
- `test_aura_functions.py` (python_module): 86 symbols, degree 363, ~9345 tokens
- `aura_live_architect.py` (python_module): 64 symbols, degree 362, ~13908 tokens
- `aura_scientific_memory.py` (python_module): 45 symbols, degree 357, ~9872 tokens
- `aura_st3gg_recall.py` (python_module): 32 symbols, degree 244, ~5314 tokens
- `aura_fusion.py` (python_module): 38 symbols, degree 217, ~8615 tokens
- `test_synthesis_upgrades.py` (python_module): 51 symbols, degree 190, ~4828 tokens
- `aura_paper_memory.py` (python_module): 32 symbols, degree 181, ~4617 tokens
- `test_aura_substrate.py` (python_module): 25 symbols, degree 180, ~6102 tokens
- `travel_price_sidecar.py` (python_module): 35 symbols, degree 175, ~7271 tokens

## Topology Integration

- **source**: compiled_deep_topology
- **nodes**: 2948
- **edges**: 6230
- **top_files_by_degree**:
  - `aura_node.py` degree=891 nodes=221 neighbors=`arxiv_forager.py`, `async_palace.py`, `aura_ai_router.py`, `aura_api_rotator.py`
  - `aura_architect_loop.py` degree=576 nodes=68 neighbors=`arxiv_forager.py`, `aura_codebase_navigator.py`, `aura_dream_engine.py`, `aura_dream_retrieval.py`
  - `test_scientific_memory.py` degree=474 nodes=112 neighbors=`arxiv_forager.py`, `aura_scientific_memory.py`, `travel_price_sidecar.py`, `travel_scraper_core.py`
  - `test_aura_functions.py` degree=363 nodes=87 neighbors=`arch_reasoner_accel.py`, `async_palace.py`, `aura_arch_reasoner.py`, `aura_associative_core.py`
  - `aura_live_architect.py` degree=362 nodes=65 neighbors=`aura_architect_loop.py`, `aura_fst_routing.py`, `aura_fusion.py`, `aura_lexc.py`
  - `aura_scientific_memory.py` degree=357 nodes=46 neighbors=`arxiv_forager.py`, `aura_fst_routing.py`, `aura_live_architect.py`, `aura_node.py`
  - `aura_st3gg_recall.py` degree=244 nodes=33 neighbors=`aura_api_rotator.py`, `aura_architect_loop.py`, `aura_context_crusher.py`, `aura_dream_retrieval.py`
  - `aura_fusion.py` degree=217 nodes=39 neighbors=`aura_api_rotator.py`, `aura_architect_loop.py`, `aura_codebase_navigator.py`, `aura_fst_routing.py`
  - `test_synthesis_upgrades.py` degree=190 nodes=52 neighbors=`aura_arch_reasoner.py`, `aura_associative_core.py`, `aura_heal.py`, `aura_node.py`
  - `aura_paper_memory.py` degree=181 nodes=33 neighbors=`arxiv_forager.py`, `aura_fst_routing.py`, `aura_live_architect.py`, `aura_llm_egress.py`
  - `test_aura_substrate.py` degree=180 nodes=26 neighbors=`aura_codebase_navigator.py`, `aura_converse.py`, `aura_fst_routing.py`, `aura_llm_egress.py`
  - `travel_price_sidecar.py` degree=175 nodes=36 neighbors=`aura_fst_routing.py`, `test_scientific_memory.py`, `test_travel_sidecar_stack.py`, `travel_media_assets.py`

## High-Value Symbols

- `AccountState` -> `aura_blockchain/node.py:27`
- `ActCapsule` -> `aura_architect_loop.py:80`
- `ActionCapsule` -> `aura_liquid_planning_arena.py:108`
- `AdaptiveLiquidTimeConstant` -> `liquid_kernel.py:57`, `liquid_math_reference.py:36`
- `AnthropicRouter` -> `aura_anthropic_router.py:268`
- `ArXivForager` -> `arxiv_forager.py:81`
- `ArchitectBuilderBridge` -> `aura_live_architect.py:1001`
- `ArchitectCouncilDecision` -> `aura_live_architect.py:78`
- `ArchitectExecutionResult` -> `aura_architect_loop.py:281`
- `ArchitectFusionCouncil` -> `aura_live_architect.py:806`
- `ArchitectFusionLoop` -> `aura_architect_loop.py:1596`
- `ArchitectLedgerRecord` -> `aura_architect_loop.py:248`
- `ArchitectLoopResult` -> `aura_architect_loop.py:263`
- `ArchitectModelProfile` -> `aura_live_architect.py:53`
- `ArchitectModelRouter` -> `aura_live_architect.py:594`
- `ArenaLease` -> `aura_liquid_planning_arena.py:166`
- `ArenaPatch` -> `aura_architect_loop.py:201`
- `ArxivPaper` -> `arxiv_forager.py:938`
- `AssetProperties` -> `aura_vsa_rendering.py:31`
- `AsyncExpertQuantizationEngine` -> `aura_timestep_svd_quantizer.py:337`
- `AsyncMemoryPalace` -> `async_palace.py:379`, `aura_attention_palace.py:43`
- `AthabaskanPositionalParser` -> `aura_positional_parser.py:17`
- `AttentionConfig` -> `aura_dynamic_attention.py:37`
- `AttentionResult` -> `aura_dynamic_attention.py:47`
- `AuraARWebSocketServer` -> `aura_topology_ws_bridge.py:361`
- `AuraArchReasoner` -> `aura_arch_reasoner.py:28`
- `AuraAssociativeCore` -> `aura_associative_core.py:27`
- `AuraCognitiveSynthesizer` -> `aura_cognitive_synthesizer.py:21`
- `AuraCompilerParser` -> `aura_node.py:721`
- `AuraConsensus` -> `aura_blockchain/consensus.py:105`
- `AuraContextCrusher` -> `aura_context_crusher.py:228`
- `AuraDependencyScanner` -> `aura_node.py:1092`
- `AuraDreamEngine` -> `aura_dream_engine.py:54`
- `AuraEpistemicIngestGateway` -> `aura_epistemic_ingest.py:27`
- `AuraFusionAgent` -> `aura_fusion.py:89`
- `AuraFusionCoordinator` -> `aura_fusion.py:481`
- `AuraFusionResult` -> `aura_fusion.py:126`
- `AuraGraftOrchestrator` -> `liquid_attractor_control_plane.py:777`
- `AuraHolographicManifest` -> `aura_holographic_manifest.py:24`
- `AuraHyperdimensionalCore` -> `aura_core.py:191`, `aura_node.py:915`
- `AuraLexc` -> `aura_lexc.py:104`
- `AuraMeshSwarm` -> `aura_mesh.py:504`
- `AuraMitosisEngine` -> `aura_mitosis.py:16`
- `AuraModelProbeLedger` -> `aura_model_probe_ledger.py:109`
- `AuraNativePFST` -> `aura_node.py:739`
- `AuraNeuroSymbolicReasoner` -> `aura_nesy_sat_reasoner.py:50`
- `AuraNode` -> `aura_blockchain/node.py:32`
- `AuraOntologyCircuit` -> `aura_ontology_circuit.py:51`
- `AuraOrchestrationLobe` -> `aura_core.py:167`
- `AuraPanelOutput` -> `aura_fusion.py:112`
- `AuraPhaseCapsule` -> `aura_phase_capsule.py:24`
- `AuraPrivacyIOOrchestrator` -> `aura_privacy_io.py:19`
- `AuraResonanceEgressGate` -> `aura_paper_memory.py:396`
- `AuraRustWasmBridge` -> `aura_wasm_bridge.py:58`
- `AuraSafetySentinel` -> `aura_node.py:1109`
- `AuraSandbox` -> `aura_node.py:1031`
- `AuraSkill` -> `aura_skillweaver.py:47`
- `AuraSkillWeaver` -> `aura_skillweaver.py:593`
- `AuraSovereignPatcher` -> `aura_patcher.py:13`
- `AuraSpectralMemoryOrchestrator` -> `aura_spectral_memory.py:16`
- `AuraSpikingGovernor` -> `aura_governor.py:18`, `aura_node.py:801`
- `AuraSubstrate` -> `aura_substrate.py:504`
- `AuraSuperpositionEngine` -> `aura_node.py:1274`
- `AuraThermodynamicPUF` -> `aura_crypto_puf.py:18`
- `AuraVisualCortex` -> `aura_background_auditor.py:17`
- `AuraWasmHypervisor` -> `gateway.py:506`
- `AuraWebForager` -> `aura_node.py:1071`
- `AuraZeroDiskIOCache` -> `aura_node.py:226`
- `AutoRouter` -> `aura_router.py:222`
- `BaseArenaAdapter` -> `aura_liquid_planning_arena.py:301`
- `BatchWriterConfig` -> `async_palace.py:111`
- `BenchmarkSandbox` -> `aura_benchmark_sandbox.py:117`
- `Block` -> `aura_blockchain/block.py:53`
- `BoundaryContract` -> `aura_liquid_planning_arena.py:45`
- `BoundedKnowledgeEngine` -> `aura_forager.py:20`
- `CachePrefixReport` -> `aura_context_crusher.py:60`
- `CalibrationLedger` -> `aura_router.py:126`
- `ChangeLogStore` -> `aura_hv_cache.py:107`
- `CircuitVerdict` -> `aura_ontology_circuit.py:41`
- `CivicArenaAdapter` -> `aura_liquid_planning_arena.py:461`
