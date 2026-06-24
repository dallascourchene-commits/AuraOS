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

- **file_count**: 201
- **total_bytes**: 142694
- **text_tokens_est**: 880985
- **role_counts**: {'binary_artifact': 11, 'interface_surface': 1, 'knowledge_artifact': 28, 'native_accelerator': 6, 'operator_script': 4, 'python_module': 129, 'schema_or_lexicon': 9, 'support_file': 13}
- **topology_nodes**: 0
- **topology_edges**: 0
- **topology_source**: disabled
- **elapsed_ms**: 7610.86
- **last_incremental_refresh_unix**: 1782312173

## Coverage

- **included_file_count**: 201
- **policy**: all files under root except skipped runtime/cache dirs and generated CODEMAP outputs
- **excluded_generated_map_files**: `.aura/CODEMAP.json`, `.aura/CODEMAP.md`
- **skipped_dir_file_counts**: `.git`=84, `.pytest_cache`=5, `Aura_Memory`=3, `__pycache__`=91

## Command Index

- `!Aura_Sandbox` -> `.gitignore:42`
- `!CORE_AXIOM_VALID` -> `aura_nesy_sat_reasoner.py:280`
- `!DOCTYPE` -> `aura_savings_dashboard.py:50`, `index.html:1`
- `!ai_route` -> `USER_GUIDE.md:169`, `aura_ai_router.py:22`, `aura_node.py:6716`
- `!ai_router_regen` -> `USER_GUIDE.md:178`, `aura_node.py:6731`
- `!approve` -> `AURA_FINAL_REPORT.md:151`, `USER_GUIDE.md:213`, `aura_node.py:5413`
- `!ar_server_start` -> `USER_GUIDE.md:414`, `aura_node.py:6185`
- `!ar_server_stop` -> `USER_GUIDE.md:415`, `aura_node.py:6201`
- `!ar_start` -> `AURA_FINAL_REPORT.md:168`, `USER_GUIDE.md:414`, `aura_node.py:6185`, `refactored-auraos-upgrades.md:2572`
- `!ar_stop` -> `AURA_FINAL_REPORT.md:169`, `USER_GUIDE.md:415`, `aura_node.py:6201`, `refactored-auraos-upgrades.md:2572`
- `!attention` -> `USER_GUIDE.md:185`, `aura_node.py:5476`
- `!audit` -> `USER_GUIDE.md:200`, `aura_node.py:5980`
- `!backtrack` -> `AURA_FINAL_REPORT.md:143`, `README.md:82`, `USER_GUIDE.md:314`, `arxiv_forager.py:599`
- `!benchmark` -> `README.md:26`, `USER_GUIDE.md:199`, `aura_node.py:2982`, `daily_digest_2026-06-06.md:14`
- `!c` -> `arch_reasoner_accel.rs:14`
- `!calibrate` -> `AURA_FINAL_REPORT.md:163`, `README.md:81`, `USER_GUIDE.md:220`, `aura_node.py:7046`
- `!canvas` -> `aura_savings_dashboard.py:175`
- `!catalyze` -> `AURA_FINAL_REPORT.md:156`, `USER_GUIDE.md:181`, `aura_node.py:6753`, `generate_ai_router.py:357`
- `!cognitive_search` -> `USER_GUIDE.md:184`, `aura_node.py:5445`
- `!commands` -> `USER_GUIDE.md:130`
- `!contingency_spawn` -> `USER_GUIDE.md:225`, `aura_node.py:6520`
- `!converse` -> `AURA_FINAL_REPORT.md:161`, `USER_GUIDE.md:224`, `aura_node.py:7161`
- `!coordinated_reason` -> `USER_GUIDE.md:192`, `aura_node.py:6963`
- `!crystallize` -> `AURA_FINAL_REPORT.md:141`, `USER_GUIDE.md:321`, `aura_node.py:6820`
- `!curiosity_tree` -> `AURA_FINAL_REPORT.md:174`, `USER_GUIDE.md:317`, `aura_node.py:6242`
- `!db_repair` -> `USER_GUIDE.md:418`, `aura_node.py:2982`
- `!evolve_reasoning` -> `AURA_FINAL_REPORT.md:157`, `USER_GUIDE.md:194`, `aura_node.py:6815`
- `!export` -> `USER_GUIDE.md:416`, `aura_node.py:5803`
- `!fast_path` -> `AURA_FINAL_REPORT.md:173`, `USER_GUIDE.md:183`, `aura_node.py:6905`, `test_aura_functions.py:900`
- `!forage` -> `USER_GUIDE.md:313`, `aura_node.py:5986`, `refactored-auraos-upgrades.md:2573`
- `!forage_off` -> `USER_GUIDE.md:319`, `aura_node.py:6179`
- `!forage_on` -> `USER_GUIDE.md:318`, `aura_node.py:6173`
- `!forager_off` -> `USER_GUIDE.md:319`, `aura_node.py:6179`
- `!forager_on` -> `USER_GUIDE.md:318`, `aura_node.py:6173`
- `!fusion` -> `AURA_FINAL_REPORT.md:31`, `USER_GUIDE.md:222`, `aura_node.py:7032`
- `!heal` -> `aura_node.py:5133`
- `!help` -> `AURA_FINAL_REPORT.md:48`, `USER_GUIDE.md:166`, `aura_node.py:7171`
- `!important` -> `index.html:9`
- `!indus_decrypt` -> `AURA_FINAL_REPORT.md:175`, `USER_GUIDE.md:323`, `aura_node.py:6827`
- `!manifest` -> `AURA_FINAL_REPORT.md:138`, `USER_GUIDE.md:166`, `aura_node.py:7171`
- `!markov` -> `AURA_FINAL_REPORT.md:144`, `USER_GUIDE.md:419`, `aura_node.py:7018`
- `!mesh_status` -> `AURA_FINAL_REPORT.md:167`, `USER_GUIDE.md:413`, `aura_node.py:5439`
- `!meta_analyze` -> `USER_GUIDE.md:195`, `aura_node.py:6866`
- `!meta_reason` -> `AURA_FINAL_REPORT.md:155`, `USER_GUIDE.md:196`, `aura_arch_reasoner.py:91`, `aura_node.py:6891`
- `!optimize` -> `AURA_FINAL_REPORT.md:172`, `USER_GUIDE.md:209`, `aura_node.py:5726`
- `!ping_mesh` -> `AURA_FINAL_REPORT.md:166`, `USER_GUIDE.md:412`, `aura_node.py:5434`
- `!plan` -> `aura_node.py:5377`
- `!push` -> `USER_GUIDE.md:417`, `aura_node.py:5090`, `test_aura_functions.py:208`
- `!r` -> `aura_hv_cache.py:373`, `aura_savings_dashboard.py:229`, `aura_substrate.py:134`, `aura_topology_ws_bridge.py:658`
- `!reason` -> `AURA_FINAL_REPORT.md:154`, `USER_GUIDE.md:191`, `aura_node.py:7006`
- `!repair_db` -> `USER_GUIDE.md:418`, `aura_node.py:6493`
- `!research` -> `AURA_FINAL_REPORT.md:142`, `README.md:83`, `USER_GUIDE.md:315`, `aura_node.py:6012`
- `!review` -> `USER_GUIDE.md:210`, `aura_node.py:6306`, `mistral_gate.py:78`
- `!rollback` -> `USER_GUIDE.md:214`, `aura_node.py:6291`
- `!route` -> `AURA_FINAL_REPORT.md:28`, `AURA_ROUTER.md:213`, `README.md:84`, `USER_GUIDE.md:221`
- `!saturn` -> `AURA_FINAL_REPORT.md:147`, `AuraOS.tex:212`, `USER_GUIDE.md:197`, `aura_node.py:5526`
- `!saturn_heal` -> `AURA_FINAL_REPORT.md:148`, `USER_GUIDE.md:198`, `aura_holographic_manifest.py:248`, `aura_node.py:5117`
- `!savings` -> `AURA_FINAL_REPORT.md:162`, `AuraOS.tex:185`, `USER_GUIDE.md:223`, `aura_node.py:7070`
- `!scan_topology` -> `USER_GUIDE.md:179`, `aura_node.py:6662`
- `!search_similar` -> `USER_GUIDE.md:316`, `aura_node.py:6215`, `refactored-auraos-upgrades.md:2573`
- `!self_optimize` -> `USER_GUIDE.md:209`, `aura_dynamic_attention.py:210`, `aura_node.py:5726`, `refactored-auraos-upgrades.md:826`
- `!self_reflect` -> `DAILY_DIGEST_Jun7-8_2026.md:19`, `DAILY_DIGEST_Jun7_2026.md:30`, `USER_GUIDE.md:208`, `aura_arch_reasoner.py:228`
- `!settings` -> `README.md:78`, `USER_GUIDE.md:166`, `aura_node.py:7171`, `daily_digest_2026-06-06.md:14`
- `!simulate` -> `USER_GUIDE.md:182`, `aura_node.py:6656`, `cognitive_router.py:220`
- `!something` -> `aura_node.py:4893`
- `!srcPos` -> `index.html:120`
- `!stage` -> `AURA_FINAL_REPORT.md:149`, `USER_GUIDE.md:210`, `aura_node.py:6306`
- `!stage_merge` -> `AURA_FINAL_REPORT.md:150`, `USER_GUIDE.md:211`, `aura_node.py:6328`, `mistral_gate.py:78`
- `!stage_purge` -> `USER_GUIDE.md:212`, `aura_node.py:6380`
- `!stage_review` -> `USER_GUIDE.md:210`, `aura_node.py:6306`
- `!status` -> `AURA_FINAL_REPORT.md:136`, `aura_node.py:5090`
- `!strategy_buffer_stats` -> `USER_GUIDE.md:193`, `aura_coordinated_solver.py:66`, `aura_node.py:6990`
- `!synthesize` -> `USER_GUIDE.md:322`, `aura_associative_core.py:138`, `aura_node.py:6410`, `test_aura_functions.py:886`
- `!system_audit` -> `USER_GUIDE.md:200`, `aura_node.py:5980`
- `!target_bytes` -> `cognitive_search.rs:72`
- `!test` -> `AuraOS.tex:533`
- `!test_airlock` -> `USER_GUIDE.md:201`, `aura_node.py:5389`
- `!tgtPos` -> `index.html:120`
- `!timeline` -> `USER_GUIDE.md:320`, `aura_node.py:6254`
- `!topology` -> `AURA_FINAL_REPORT.md:48`, `README.md:41`, `USER_GUIDE.md:179`, `aura_ai_router.py:143`
- `!topology_deep` -> `USER_GUIDE.md:180`, `aura_node.py:6745`
- `!total` -> `aura_savings_dashboard.py:224`
- `!voice` -> `USER_GUIDE.md:420`, `aura_node.py:7227`

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
- `aura_paper_memory.py`
- ... 9 more; query CODEMAP.json for exact file cards

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
- `aura_model_probe_ledger.py`
- `aura_router.py`
- ... 6 more; query CODEMAP.json for exact file cards

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
- ... 128 more; query CODEMAP.json for exact file cards

## Hubs

- `aura_node.py` (python_module): 80 symbols, degree 0, ~96568 tokens
- `test_aura_functions.py` (python_module): 80 symbols, degree 0, ~9398 tokens
- `test_synthesis_upgrades.py` (python_module): 51 symbols, degree 0, ~4864 tokens
- `liquid_kernel.py` (python_module): 41 symbols, degree 0, ~4089 tokens
- `arxiv_forager.py` (python_module): 37 symbols, degree 0, ~17900 tokens
- `async_palace.py` (python_module): 36 symbols, degree 0, ~9606 tokens
- `aura_topology_ws_bridge.py` (python_module): 36 symbols, degree 0, ~8086 tokens
- `aura_context_crusher.py` (python_module): 36 symbols, degree 0, ~4964 tokens
- `liquid_attractor_control_plane.py` (python_module): 34 symbols, degree 0, ~9969 tokens
- `aura_paper_memory.py` (python_module): 32 symbols, degree 0, ~4562 tokens
- `aura_codebase_navigator.py` (python_module): 31 symbols, degree 0, ~8761 tokens
- `aura_mesh.py` (python_module): 30 symbols, degree 0, ~14759 tokens

## Topology Integration

- **source**: disabled
- **nodes**: 0
- **edges**: 0

## High-Value Symbols

- `AccountState` -> `aura_blockchain/node.py:26`
- `AdaptiveLiquidTimeConstant` -> `liquid_kernel.py:56`, `liquid_math_reference.py:35`
- `AnthropicRouter` -> `aura_anthropic_router.py:271`
- `ArXivForager` -> `arxiv_forager.py:82`
- `ArxivPaper` -> `arxiv_forager.py:956`
- `AsyncMemoryPalace` -> `async_palace.py:378`, `aura_attention_palace.py:44`
- `AthabaskanPositionalParser` -> `aura_positional_parser.py:15`
- `AttentionConfig` -> `aura_dynamic_attention.py:37`
- `AttentionResult` -> `aura_dynamic_attention.py:47`
- `AuraARWebSocketServer` -> `aura_topology_ws_bridge.py:361`
- `AuraArchReasoner` -> `aura_arch_reasoner.py:29`
- `AuraAssociativeCore` -> `aura_associative_core.py:27`
- `AuraCognitiveSynthesizer` -> `aura_cognitive_synthesizer.py:19`
- `AuraCompilerParser` -> `aura_node.py:715`
- `AuraConsensus` -> `aura_blockchain/consensus.py:106`
- `AuraContextCrusher` -> `aura_context_crusher.py:214`
- `AuraDependencyScanner` -> `aura_node.py:1086`
- `AuraDreamEngine` -> `aura_dream_engine.py:54`
- `AuraEpistemicIngestGateway` -> `aura_epistemic_ingest.py:27`
- `AuraFusionAgent` -> `aura_fusion.py:85`
- `AuraFusionCoordinator` -> `aura_fusion.py:272`
- `AuraFusionResult` -> `aura_fusion.py:122`
- `AuraGraftOrchestrator` -> `liquid_attractor_control_plane.py:746`
- `AuraHolographicManifest` -> `aura_holographic_manifest.py:24`
- `AuraHyperdimensionalCore` -> `aura_core.py:190`, `aura_node.py:909`
- `AuraMeshSwarm` -> `aura_mesh.py:505`
- `AuraMitosisEngine` -> `aura_mitosis.py:16`
- `AuraModelProbeLedger` -> `aura_model_probe_ledger.py:110`
- `AuraNativePFST` -> `aura_node.py:733`
- `AuraNeuroSymbolicReasoner` -> `aura_nesy_sat_reasoner.py:50`
- `AuraNode` -> `aura_blockchain/node.py:31`
- `AuraOntologyCircuit` -> `aura_ontology_circuit.py:51`
- `AuraOrchestrationLobe` -> `aura_core.py:166`
- `AuraPanelOutput` -> `aura_fusion.py:108`
- `AuraPhaseCapsule` -> `aura_phase_capsule.py:25`
- `AuraPrivacyIOOrchestrator` -> `aura_privacy_io.py:17`
- `AuraResonanceEgressGate` -> `aura_paper_memory.py:396`
- `AuraSafetySentinel` -> `aura_node.py:1103`
- `AuraSandbox` -> `aura_node.py:1025`
- `AuraSkill` -> `aura_skillweaver.py:49`
- `AuraSkillWeaver` -> `aura_skillweaver.py:595`
- `AuraSovereignPatcher` -> `aura_patcher.py:14`
- `AuraSpectralMemoryOrchestrator` -> `aura_spectral_memory.py:14`
- `AuraSpikingGovernor` -> `aura_governor.py:18`, `aura_node.py:795`
- `AuraSubstrate` -> `aura_substrate.py:504`
- `AuraSuperpositionEngine` -> `aura_node.py:1268`
- `AuraThermodynamicPUF` -> `aura_crypto_puf.py:16`
- `AuraVisualCortex` -> `aura_background_auditor.py:16`
- `AuraWasmHypervisor` -> `gateway.py:506`
- `AuraWebForager` -> `aura_node.py:1065`
- `AuraZeroDiskIOCache` -> `aura_node.py:220`
- `AutoRouter` -> `aura_router.py:223`
- `BatchWriterConfig` -> `async_palace.py:110`
- `BenchmarkSandbox` -> `aura_benchmark_sandbox.py:118`
- `Block` -> `aura_blockchain/block.py:51`
- `BoundedKnowledgeEngine` -> `aura_forager.py:18`
- `CachePrefixReport` -> `aura_context_crusher.py:52`
- `CalibrationLedger` -> `aura_router.py:127`
- `ChangeLogStore` -> `aura_hv_cache.py:107`
- `CircuitVerdict` -> `aura_ontology_circuit.py:41`
- `ClosedFormContinuousCore` -> `liquid_kernel.py:151`
- `CodeTopologyMapper` -> `spatial_mapper.py:55`
- `CognitiveGateway` -> `gateway.py:30`
- `CognitiveRouter` -> `cognitive_router.py:18`
- `CommProfile` -> `aura_converse.py:60`
- `ConsensusError` -> `aura_blockchain/consensus.py:348`
- `ConsensusState` -> `aura_blockchain/consensus.py:91`
- `ContextBundle` -> `aura_substrate.py:422`
- `ContextCrushBatch` -> `aura_context_crusher.py:106`
- `ContextCrushResult` -> `aura_context_crusher.py:73`
- `ContextSelector` -> `aura_substrate.py:429`
- `ConversationLog` -> `aura_converse.py:190`
- `Conversationalist` -> `aura_converse.py:218`
- `CoordinatedSolver` -> `aura_coordinated_solver.py:76`
- `DashboardHandler` -> `aura_savings_dashboard.py:329`
- `DepGraph` -> `pvm_arch_checker.py:43`
- `DirectoryCache` -> `spatial_mapper.py:24`
- `DynamicContextCompiler` -> `gateway.py:369`
- `DynamicConvolutionAttention` -> `aura_dynamic_attention.py:266`
- `DynamicConvolutionKernel` -> `aura_dynamic_attention.py:61`
