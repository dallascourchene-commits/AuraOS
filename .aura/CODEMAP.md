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

- **file_count**: 180
- **total_bytes**: 164384
- **text_tokens_est**: 804766
- **role_counts**: {'binary_artifact': 11, 'interface_surface': 1, 'knowledge_artifact': 27, 'native_accelerator': 6, 'operator_script': 4, 'python_module': 109, 'schema_or_lexicon': 9, 'support_file': 13}
- **topology_nodes**: 0
- **topology_edges**: 0
- **topology_source**: unknown
- **elapsed_ms**: 7610.86
- **last_incremental_refresh_unix**: 1781717073

## Coverage

- **included_file_count**: 180
- **policy**: all files under root except skipped runtime/cache dirs and generated CODEMAP outputs
- **excluded_generated_map_files**: `.aura/CODEMAP.json`, `.aura/CODEMAP.md`
- **skipped_dir_file_counts**: `.git`=40, `.pytest_cache`=4, `__pycache__`=15

## Command Index

- `!CORE_AXIOM_VALID` -> `aura_nesy_sat_reasoner.py:280`
- `!DOCTYPE` -> `aura_savings_dashboard.py:50`, `index.html:1`
- `!ai_route` -> `aura_ai_router.py:22`, `aura_node.py:6642`
- `!ai_router_regen` -> `aura_node.py:6657`
- `!approve` -> `USER_GUIDE.md:164`, `aura_node.py:5400`
- `!ar_server_start` -> `USER_GUIDE.md:709`, `aura_node.py:6113`
- `!ar_server_stop` -> `aura_node.py:6129`
- `!ar_start` -> `USER_GUIDE.md:219`, `aura_node.py:6113`, `refactored-auraos-upgrades.md:2572`
- `!ar_stop` -> `USER_GUIDE.md:220`, `aura_node.py:6129`, `refactored-auraos-upgrades.md:2572`
- `!attention` -> `aura_node.py:5463`
- `!audit` -> `aura_node.py:5965`
- `!backtrack` -> `USER_GUIDE.md:184`, `aura_node.py:5985`
- `!benchmark` -> `USER_GUIDE.md:206`, `aura_node.py:2984`, `daily_digest_2026-06-06.md:14`
- `!c` -> `arch_reasoner_accel.rs:14`
- `!calibrate` -> `USER_GUIDE.md:173`, `aura_node.py:6958`
- `!canvas` -> `aura_savings_dashboard.py:175`
- `!catalyze` -> `USER_GUIDE.md:148`, `aura_node.py:6679`, `generate_ai_router.py:357`, `test_aura_functions.py:893`
- `!cognitive_search` -> `aura_node.py:5432`
- `!commands` -> `USER_GUIDE.md:107`
- `!contingency_spawn` -> `USER_GUIDE.md:177`, `aura_node.py:6446`
- `!converse` -> `USER_GUIDE.md:176`, `aura_node.py:7073`
- `!coordinated_reason` -> `aura_node.py:6889`
- `!crystallize` -> `aura_node.py:6746`
- `!curiosity_tree` -> `USER_GUIDE.md:186`, `aura_node.py:6168`
- `!db_repair` -> `USER_GUIDE.md:209`, `aura_node.py:2984`
- `!evolve_reasoning` -> `USER_GUIDE.md:149`, `aura_node.py:6741`
- `!export` -> `USER_GUIDE.md:198`, `aura_node.py:5788`
- `!fast_path` -> `USER_GUIDE.md:153`, `aura_node.py:6831`, `test_aura_functions.py:900`
- `!forage` -> `USER_GUIDE.md:183`, `aura_node.py:5971`, `refactored-auraos-upgrades.md:2573`
- `!forage_off` -> `USER_GUIDE.md:188`, `aura_node.py:6107`
- `!forage_on` -> `USER_GUIDE.md:187`, `aura_node.py:6101`
- `!forager_off` -> `aura_node.py:6107`
- `!forager_on` -> `aura_node.py:6101`
- `!heal` -> `aura_node.py:5120`
- `!help` -> `README.md:154`, `aura_node.py:7083`
- `!indus_decrypt` -> `USER_GUIDE.md:190`, `aura_node.py:6753`
- `!manifest` -> `aura_node.py:7083`
- `!markov` -> `USER_GUIDE.md:210`, `aura_node.py:6944`
- `!mesh_status` -> `USER_GUIDE.md:197`, `aura_node.py:5426`
- `!meta_analyze` -> `USER_GUIDE.md:150`, `aura_node.py:6792`
- `!meta_reason` -> `USER_GUIDE.md:151`, `aura_arch_reasoner.py:91`, `aura_node.py:6817`
- `!optimize` -> `aura_node.py:5711`
- `!ping_mesh` -> `USER_GUIDE.md:196`, `aura_node.py:5421`
- `!plan` -> `aura_node.py:5364`
- `!push` -> `USER_GUIDE.md:199`, `aura_node.py:5077`, `test_aura_functions.py:208`
- `!r` -> `aura_hv_cache.py:373`, `aura_savings_dashboard.py:229`, `aura_substrate.py:123`, `aura_topology_ws_bridge.py:587`
- `!reason` -> `USER_GUIDE.md:152`, `aura_node.py:6932`
- `!repair_db` -> `aura_node.py:6419`
- `!research` -> `USER_GUIDE.md:185`, `aura_node.py:5997`, `systems_check.py:250`
- `!review` -> `aura_node.py:6232`, `mistral_gate.py:78`
- `!rollback` -> `USER_GUIDE.md:211`, `aura_node.py:6217`
- `!route` -> `USER_GUIDE.md:174`, `aura_node.py:6967`, `test_aura_substrate.py:323`
- `!saturn` -> `AuraOS.tex:212`, `USER_GUIDE.md:165`, `aura_node.py:5513`, `aura_topology_analyzer.py:122`
- `!saturn_heal` -> `README.md:76`, `USER_GUIDE.md:166`, `aura_holographic_manifest.py:248`, `aura_node.py:5104`
- `!savings` -> `AuraOS.tex:185`, `USER_GUIDE.md:175`, `aura_node.py:6982`, `test_aura_substrate.py:314`
- `!scan_topology` -> `aura_node.py:6588`
- `!search_similar` -> `aura_node.py:6143`, `refactored-auraos-upgrades.md:2573`
- `!self_optimize` -> `USER_GUIDE.md:160`, `aura_dynamic_attention.py:210`, `aura_node.py:5711`, `refactored-auraos-upgrades.md:826`
- `!self_reflect` -> `DAILY_DIGEST_Jun7-8_2026.md:19`, `DAILY_DIGEST_Jun7_2026.md:30`, `USER_GUIDE.md:159`, `aura_arch_reasoner.py:228`
- `!settings` -> `USER_GUIDE.md:205`, `aura_node.py:7083`, `daily_digest_2026-06-06.md:14`
- `!simulate` -> `aura_node.py:6582`, `cognitive_router.py:220`
- `!something` -> `aura_node.py:4895`
- `!stage` -> `USER_GUIDE.md:161`, `aura_node.py:6232`
- `!stage_merge` -> `USER_GUIDE.md:162`, `aura_node.py:6254`, `mistral_gate.py:78`
- `!stage_purge` -> `USER_GUIDE.md:163`, `aura_node.py:6306`
- `!stage_review` -> `aura_node.py:6232`
- `!status` -> `aura_node.py:5077`
- `!strategy_buffer_stats` -> `aura_coordinated_solver.py:66`, `aura_node.py:6916`
- `!synthesize` -> `USER_GUIDE.md:189`, `aura_associative_core.py:138`, `aura_node.py:6336`, `test_aura_functions.py:886`
- `!system_audit` -> `USER_GUIDE.md:207`, `aura_node.py:5965`
- `!target_bytes` -> `cognitive_search.rs:72`
- `!test` -> `AuraOS.tex:533`
- `!test_airlock` -> `aura_node.py:5376`
- `!timeline` -> `aura_node.py:6180`
- `!topology` -> `USER_GUIDE.md:146`, `aura_ai_router.py:143`, `aura_codebase_navigator.py:196`, `aura_node.py:6671`
- `!topology_deep` -> `aura_node.py:6671`
- `!total` -> `aura_savings_dashboard.py:224`
- `!voice` -> `USER_GUIDE.md:208`, `aura_node.py:7134`

## Navigation Rings

### substrate_core
- `AuraOS__A_Polysynthetic_Cognitive_Substrate_for_High-Dimensional_Edge_Orchestration_and_Visual_Code_Topology.pdf`
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
- `aura_dynamic_attention.py`
- `aura_rosetta_memory.py`
- ... 5 more; query CODEMAP.json for exact file cards

### mesh_and_routing
- `AURA_ROUTER.md`
- `aura_ai_router.py`
- `aura_anthropic_router.py`
- `aura_blockchain/__init__.py`
- `aura_blockchain/block.py`
- `aura_blockchain/consensus.py`
- `aura_blockchain/demo.py`
- `aura_blockchain/node.py`
- `aura_blockchain/phasor_ledger.py`
- `aura_mesh.py`
- `aura_router.py`
- `generate_ai_router.py`
- ... 4 more; query CODEMAP.json for exact file cards

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
- `aura_validation.py`
- `forged_roots_audit.md`
- `symbolic_shield.py`

### interfaces_and_docs
- `.aura/ARCHITECTURE.md`
- `.aura/AURA.md`
- `.aura/CONVERSE.md`
- `.aura/OUTPUT_FORMATS.md`
- `.aura/ROLES.md`
- `.aura_backup.bak`
- `.aura_forager_backup.bak`
- `.aura_hdc_backup.bak`
- `.aura_node_backup.bak`
- `.aura_pfst_backup.bak`
- `.gitignore`
- `.termux/colors.properties`
- ... 113 more; query CODEMAP.json for exact file cards

## Hubs

- `aura_node.py` (python_module): 80 symbols, degree 0, ~95249 tokens
- `test_aura_functions.py` (python_module): 80 symbols, degree 0, ~9398 tokens
- `test_synthesis_upgrades.py` (python_module): 51 symbols, degree 0, ~4864 tokens
- `liquid_kernel.py` (python_module): 41 symbols, degree 0, ~4089 tokens
- `async_palace.py` (python_module): 36 symbols, degree 0, ~9606 tokens
- `aura_topology_ws_bridge.py` (python_module): 35 symbols, degree 0, ~6408 tokens
- `liquid_attractor_control_plane.py` (python_module): 34 symbols, degree 0, ~9969 tokens
- `aura_mesh.py` (python_module): 30 symbols, degree 0, ~14759 tokens
- `aura_codebase_navigator.py` (python_module): 30 symbols, degree 0, ~8632 tokens
- `liquid_math_reference.py` (python_module): 30 symbols, degree 0, ~2356 tokens
- `aura_router.py` (python_module): 28 symbols, degree 0, ~7404 tokens
- `aura_proxy_benchmark.py` (python_module): 27 symbols, degree 0, ~7827 tokens

## Topology Integration

- **source**: unknown
- **nodes**: 0
- **edges**: 0

## High-Value Symbols

- `AccountState` -> `aura_blockchain/node.py:26`
- `AdaptiveLiquidTimeConstant` -> `liquid_kernel.py:56`, `liquid_math_reference.py:35`
- `ArXivForager` -> `arxiv_forager.py:24`
- `ArxivPaper` -> `arxiv_forager.py:219`
- `AsyncMemoryPalace` -> `async_palace.py:378`, `aura_attention_palace.py:44`
- `AthabaskanPositionalParser` -> `aura_positional_parser.py:15`
- `AttentionConfig` -> `aura_dynamic_attention.py:37`
- `AttentionResult` -> `aura_dynamic_attention.py:47`
- `AuraARWebSocketServer` -> `aura_topology_ws_bridge.py:343`
- `AuraArchReasoner` -> `aura_arch_reasoner.py:29`
- `AuraAssociativeCore` -> `aura_associative_core.py:27`
- `AuraCognitiveSynthesizer` -> `aura_cognitive_synthesizer.py:19`
- `AuraCompilerParser` -> `aura_node.py:679`
- `AuraConsensus` -> `aura_blockchain/consensus.py:106`
- `AuraDependencyScanner` -> `aura_node.py:1088`
- `AuraDreamEngine` -> `aura_dream_engine.py:54`
- `AuraEpistemicIngestGateway` -> `aura_epistemic_ingest.py:27`
- `AuraGraftOrchestrator` -> `liquid_attractor_control_plane.py:746`
- `AuraHolographicManifest` -> `aura_holographic_manifest.py:24`
- `AuraHyperdimensionalCore` -> `aura_core.py:190`, `aura_node.py:911`
- `AuraMeshSwarm` -> `aura_mesh.py:505`
- `AuraMitosisEngine` -> `aura_mitosis.py:16`
- `AuraNativePFST` -> `aura_node.py:697`
- `AuraNeuroSymbolicReasoner` -> `aura_nesy_sat_reasoner.py:50`
- `AuraNode` -> `aura_blockchain/node.py:31`
- `AuraOntologyCircuit` -> `aura_ontology_circuit.py:51`
- `AuraOrchestrationLobe` -> `aura_core.py:166`
- `AuraPrivacyIOOrchestrator` -> `aura_privacy_io.py:17`
- `AuraSafetySentinel` -> `aura_node.py:1105`
- `AuraSandbox` -> `aura_node.py:1027`
- `AuraSovereignPatcher` -> `aura_patcher.py:14`
- `AuraSpectralMemoryOrchestrator` -> `aura_spectral_memory.py:14`
- `AuraSpikingGovernor` -> `aura_governor.py:18`, `aura_node.py:797`
- `AuraSubstrate` -> `aura_substrate.py:317`
- `AuraSuperpositionEngine` -> `aura_node.py:1270`
- `AuraThermodynamicPUF` -> `aura_crypto_puf.py:16`
- `AuraVisualCortex` -> `aura_background_auditor.py:16`
- `AuraWasmHypervisor` -> `gateway.py:506`
- `AuraWebForager` -> `aura_node.py:1067`
- `AuraZeroDiskIOCache` -> `aura_node.py:186`
- `AutoRouter` -> `aura_router.py:222`
- `BatchWriterConfig` -> `async_palace.py:110`
- `BenchmarkSandbox` -> `aura_benchmark_sandbox.py:118`
- `Block` -> `aura_blockchain/block.py:51`
- `BoundedKnowledgeEngine` -> `aura_forager.py:18`
- `CalibrationLedger` -> `aura_router.py:126`
- `ChangeLogStore` -> `aura_hv_cache.py:107`
- `CircuitVerdict` -> `aura_ontology_circuit.py:41`
- `ClosedFormContinuousCore` -> `liquid_kernel.py:151`
- `CodeTopologyMapper` -> `spatial_mapper.py:55`
- `CognitiveGateway` -> `gateway.py:30`
- `CognitiveRouter` -> `cognitive_router.py:18`
- `CommProfile` -> `aura_converse.py:60`
- `ConsensusError` -> `aura_blockchain/consensus.py:348`
- `ConsensusState` -> `aura_blockchain/consensus.py:91`
- `ContextBundle` -> `aura_substrate.py:235`
- `ContextSelector` -> `aura_substrate.py:242`
- `ConversationLog` -> `aura_converse.py:190`
- `Conversationalist` -> `aura_converse.py:218`
- `CoordinatedSolver` -> `aura_coordinated_solver.py:76`
- `DashboardHandler` -> `aura_savings_dashboard.py:328`
- `DepGraph` -> `pvm_arch_checker.py:43`
- `DirectoryCache` -> `spatial_mapper.py:24`
- `DynamicContextCompiler` -> `gateway.py:369`
- `DynamicConvolutionAttention` -> `aura_dynamic_attention.py:266`
- `DynamicConvolutionKernel` -> `aura_dynamic_attention.py:61`
- `Ed25519KeyPair` -> `aura_blockchain/consensus.py:42`
- `EdgeAuditRecord` -> `aura_nesy_unit_interval.py:69`
- `EdgeZone` -> `aura_nesy_unit_interval.py:62`
- `EnhancedArxivForager` -> `arxiv_forager.py:288`
- `ExecutionLog` -> `aura_router.py:194`
- `ExternalLLM` -> `aura_llm_egress.py:219`
- `FederatedHDCResult` -> `aura_federated_hdc.py:67`
- `ForagerConfig` -> `arxiv_forager.py:246`
- `ForagerStats` -> `arxiv_forager.py:258`
- `GeminiKeyRotator` -> `aura_api_rotator.py:118`
- `HDCSubModel` -> `aura_federated_hdc.py:38`
- `HVCacheSubstrate` -> `aura_hv_cache.py:437`
- `HeightBoundedVPTTokenizer` -> `aura_vpt_tokenizer.py:18`
- `HybridLinguisticCortex` -> `aura_hybrid_linguistic_cortex.py:18`
