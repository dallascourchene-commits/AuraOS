#![forbid(unsafe_code)]

//! Bind post-edit profiled-scope currentness to the canonical definition owner->target relation.
//!
//! PR515 proves one candidate profiled scope is current only after fresh candidate source,
//! SyntaxGraph/profile, typed SourceGeneration, canonical scope reselection and clean full reparse
//! converge. PR508 proves that a definition is declared in one owner scope and targets a distinct
//! nested scope. This membrane joins those consequences on the freshly generated candidate profile.
//!
//! Inventory-local scope IDs remain join witnesses only; they are not semantic identity. Runtime
//! name resolution, semantic correctness, review approval, commit authority and external effect
//! remain explicitly false.

use aura_k27_astge::NodeIndexRecordV1;
use aura_k27_astge_generation_domain::SourceGenerationV1;
use aura_k27_astge_materialize::AdmittedSourceCatalogV1;
use aura_k27_astge_post_edit_profiled_scope::{
    admit_post_edit_profiled_scope_current, CandidateProfiledScopeSelectorV1,
    PostEditProfiledScopeCurrentV1, PostEditProfiledScopeErrorV1,
};
use aura_k27_astge_scope::{AuthorizedSpanV1, ReplacementV1};
use aura_k27_astge_scopes::PythonLexicalScopeIndexV1;
use std::collections::HashMap;
use std::error::Error;
use std::fmt::{Display, Formatter};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CandidateDefinitionTargetRelationV1 {
    pub definition_name: String,
    pub definition_owner_scope_id: u64,
    pub definition_owner_scope_kind: String,
    pub definition_target_scope_id: u64,
    pub definition_target_scope_kind: String,
    pub duplicate_same_owner_name_count: usize,
    pub selected_current_scope_is_binding_target: bool,
    pub binding_owner_is_selected_parent: bool,
    pub local_scope_id_is_semantic_identity: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PostEditCanonicalDefinitionTargetCurrentV1 {
    pub post_edit_current: PostEditProfiledScopeCurrentV1,
    pub relation: CandidateDefinitionTargetRelationV1,
    pub post_edit_profiled_scope_current: bool,
    pub canonical_definition_target_current: bool,
    pub source_generation: SourceGenerationV1,
    pub runtime_name_resolution_proven: bool,
    pub call_graph_proven: bool,
    pub semantic_patch_correctness_proven: bool,
    pub b_minus_approved: bool,
    pub commit_authorized: bool,
    pub execution_authorized: bool,
    pub human_authority: bool,
    pub external_effect_authorized: bool,
}

#[derive(Debug)]
pub enum PostEditCanonicalScopeErrorV1 {
    PostEdit(PostEditProfiledScopeErrorV1),
    PostEditCurrentnessNotProven,
    SelectedScopeNotInCandidateProfile,
    SelectedScopeHasNoParent(u64),
    SelectedScopeHasNoSyntaxOrdinal(u64),
    SelectedScopeHasNoAstWitness(u64),
    SelectedScopeHasNoSemanticHandle(u64),
    DefinitionBindingMissing(u64),
    DefinitionBindingAmbiguous {
        selected_scope_id: u64,
        matches: usize,
    },
    BindingOwnerParentMismatch {
        binding_owner_scope_id: u64,
        selected_parent_scope_id: u64,
    },
    OwnerScopeMissing(u64),
}

impl Display for PostEditCanonicalScopeErrorV1 {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        write!(f, "{self:?}")
    }
}

impl Error for PostEditCanonicalScopeErrorV1 {}

impl From<PostEditProfiledScopeErrorV1> for PostEditCanonicalScopeErrorV1 {
    fn from(value: PostEditProfiledScopeErrorV1) -> Self {
        Self::PostEdit(value)
    }
}

/// Require the freshly current candidate scope to also be the exact target of one definition.
///
/// This function consumes only PR515's generated candidate profile. It does not reparse source and
/// does not create a second lexical-scope owner. `scope_id` is used only to join one selected scope
/// to one binding inside the *same* freshly generated profile; the canonical syntax/span/handle
/// witnesses must agree as well.
pub fn require_candidate_definition_target_relation(
    current: &PostEditProfiledScopeCurrentV1,
) -> Result<CandidateDefinitionTargetRelationV1, PostEditCanonicalScopeErrorV1> {
    if !current.post_edit_profiled_scope_current
        || !current.clean_full_reparse_profile_match
        || !current.candidate_scope_reselected_from_canonical_anchor
    {
        return Err(PostEditCanonicalScopeErrorV1::PostEditCurrentnessNotProven);
    }

    let selected = &current.selected_candidate_scope;
    let profile = &current.candidate_current.profiled_scopes;

    let selected_in_profile = profile
        .profiled_scopes
        .iter()
        .any(|scope| scope == selected);
    if !selected_in_profile {
        return Err(PostEditCanonicalScopeErrorV1::SelectedScopeNotInCandidateProfile);
    }

    let selected_parent_scope_id =
        selected
            .parent_scope_id
            .ok_or(PostEditCanonicalScopeErrorV1::SelectedScopeHasNoParent(
                selected.scope_id,
            ))?;
    let syntax_ordinal = selected
        .syntax_ordinal
        .ok_or(PostEditCanonicalScopeErrorV1::SelectedScopeHasNoSyntaxOrdinal(
            selected.scope_id,
        ))?;
    let ast_local_node_id = selected.ast_local_node_id.ok_or(
        PostEditCanonicalScopeErrorV1::SelectedScopeHasNoAstWitness(selected.scope_id),
    )?;
    let semantic_handle_digest = selected.semantic_handle_digest.ok_or(
        PostEditCanonicalScopeErrorV1::SelectedScopeHasNoSemanticHandle(selected.scope_id),
    )?;

    let matches: Vec<_> = profile
        .profiled_bindings
        .iter()
        .filter(|binding| {
            binding.target_scope_id == selected.scope_id
                && binding.syntax_ordinal == syntax_ordinal
                && binding.ast_local_node_id == ast_local_node_id
                && binding.file_id == selected.file_id
                && binding.byte_start == selected.byte_start
                && binding.byte_end == selected.byte_end
                && binding.semantic_handle_digest == semantic_handle_digest
        })
        .collect();

    let binding = match matches.as_slice() {
        [] => {
            return Err(PostEditCanonicalScopeErrorV1::DefinitionBindingMissing(
                selected.scope_id,
            ));
        }
        [binding] => *binding,
        _ => {
            return Err(PostEditCanonicalScopeErrorV1::DefinitionBindingAmbiguous {
                selected_scope_id: selected.scope_id,
                matches: matches.len(),
            });
        }
    };

    if binding.owner_scope_id != selected_parent_scope_id {
        return Err(PostEditCanonicalScopeErrorV1::BindingOwnerParentMismatch {
            binding_owner_scope_id: binding.owner_scope_id,
            selected_parent_scope_id,
        });
    }

    let owner = profile
        .profiled_scopes
        .iter()
        .find(|scope| scope.scope_id == binding.owner_scope_id)
        .ok_or(PostEditCanonicalScopeErrorV1::OwnerScopeMissing(
            binding.owner_scope_id,
        ))?;

    let duplicate_same_owner_name_count = profile
        .profiled_bindings
        .iter()
        .filter(|candidate| {
            candidate.owner_scope_id == binding.owner_scope_id && candidate.name == binding.name
        })
        .count();

    Ok(CandidateDefinitionTargetRelationV1 {
        definition_name: binding.name.clone(),
        definition_owner_scope_id: binding.owner_scope_id,
        definition_owner_scope_kind: owner.kind.clone(),
        definition_target_scope_id: selected.scope_id,
        definition_target_scope_kind: selected.kind.clone(),
        duplicate_same_owner_name_count,
        selected_current_scope_is_binding_target: true,
        binding_owner_is_selected_parent: true,
        local_scope_id_is_semantic_identity: false,
    })
}

/// Admit post-edit currentness and then bind that exact current scope to its definition edge.
#[allow(clippy::too_many_arguments)]
pub fn admit_post_edit_canonical_definition_target_current(
    pre_edit_scope_index: &PythonLexicalScopeIndexV1,
    pre_edit_selected_scope_id: u64,
    pre_edit_catalog: &AdmittedSourceCatalogV1,
    persisted_record: &NodeIndexRecordV1,
    expected_pre_edit_source_generation: SourceGenerationV1,
    original_source: &[u8],
    candidate_source: &[u8],
    authorized_spans: &[AuthorizedSpanV1],
    replacements: &[ReplacementV1],
    candidate_hydration_json: &str,
    candidate_anchor_id: &str,
    candidate_semantic_handles: &HashMap<u64, [u8; 32]>,
    expected_candidate_source_generation: SourceGenerationV1,
    candidate_selector: &CandidateProfiledScopeSelectorV1,
) -> Result<PostEditCanonicalDefinitionTargetCurrentV1, PostEditCanonicalScopeErrorV1> {
    let post_edit_current = admit_post_edit_profiled_scope_current(
        pre_edit_scope_index,
        pre_edit_selected_scope_id,
        pre_edit_catalog,
        persisted_record,
        expected_pre_edit_source_generation,
        original_source,
        candidate_source,
        authorized_spans,
        replacements,
        candidate_hydration_json,
        candidate_anchor_id,
        candidate_semantic_handles,
        expected_candidate_source_generation,
        candidate_selector,
    )?;
    let relation = require_candidate_definition_target_relation(&post_edit_current)?;
    let source_generation = post_edit_current.candidate_source_generation;

    Ok(PostEditCanonicalDefinitionTargetCurrentV1 {
        post_edit_current,
        relation,
        post_edit_profiled_scope_current: true,
        canonical_definition_target_current: true,
        source_generation,
        runtime_name_resolution_proven: false,
        call_graph_proven: false,
        semantic_patch_correctness_proven: false,
        b_minus_approved: false,
        commit_authorized: false,
        execution_authorized: false,
        human_authority: false,
        external_effect_authorized: false,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use aura_k27_astge_generation_domain::GenerationDomainV1;
    use aura_k27_astge_ingest::{encode_ast_to_splane, parse_python_named_ast};
    use aura_k27_astge_materialize::SourceLocatorV1;
    use aura_k27_astge_post_edit_profiled_scope::CandidateProfiledScopeSelectorV1;
    use aura_k27_astge_profiled_scopes::build_profiled_python_scopes;
    use aura_k27_astge_scopes::index_python_nested_scopes;
    use serde_json::{json, Value};
    use sha2::{Digest, Sha256};
    use std::fs;
    use std::path::PathBuf;
    use std::sync::atomic::{AtomicU64, Ordering};

    static COUNTER: AtomicU64 = AtomicU64::new(0);
    const SOURCE: &str = "def outer():\n    def inner():\n        return 1\n    return inner\n";

    struct Setup {
        root: PathBuf,
        file_id: u32,
        scope_index: PythonLexicalScopeIndexV1,
        selected_scope_id: u64,
        record: NodeIndexRecordV1,
        catalog: AdmittedSourceCatalogV1,
        edit_start: usize,
    }

    fn handles(source: &str, file_id: u32) -> HashMap<u64, [u8; 32]> {
        parse_python_named_ast(source, file_id)
            .unwrap()
            .nodes
            .into_iter()
            .map(|node| {
                let mut digest = [0u8; 32];
                digest[..8].copy_from_slice(&node.node_id.to_le_bytes());
                digest[8..12].copy_from_slice(&file_id.to_le_bytes());
                (node.node_id, digest)
            })
            .collect()
    }

    fn setup(label: &str, generation: u64) -> Setup {
        let n = COUNTER.fetch_add(1, Ordering::Relaxed);
        let root = std::env::temp_dir().join(format!(
            "aura-k27-post-edit-canonical-{label}-{}-{n}",
            std::process::id()
        ));
        fs::create_dir_all(root.join("src")).unwrap();
        fs::write(root.join("src/module.py"), SOURCE.as_bytes()).unwrap();
        let file_id = 177;
        let graph = parse_python_named_ast(SOURCE, file_id).unwrap();
        let old_handles = handles(SOURCE, file_id);
        let scope_index = index_python_nested_scopes(SOURCE, file_id, &old_handles).unwrap();
        let selected = scope_index
            .scopes
            .iter()
            .find(|scope| scope.name == "inner")
            .unwrap();
        let selected_scope_id = selected.scope_id;
        let selected_ast_node_id = selected.ast_node_id.unwrap();
        let encoded = encode_ast_to_splane(&graph, &old_handles, 0, 41, [0x91; 32]).unwrap();
        let record = encoded
            .records
            .iter()
            .find(|record| record.node_id == selected_ast_node_id)
            .unwrap()
            .clone();
        let catalog = AdmittedSourceCatalogV1::admit(
            &root,
            [SourceLocatorV1::bind(
                file_id,
                "src/module.py",
                generation,
                SOURCE.as_bytes(),
            )],
        )
        .unwrap();
        let edit_start = SOURCE.find("return 1").unwrap() + "return ".len();
        Setup {
            root,
            file_id,
            scope_index,
            selected_scope_id,
            record,
            catalog,
            edit_start,
        }
    }

    fn sha256_hex(source: &[u8]) -> String {
        Sha256::digest(source)
            .iter()
            .map(|byte| format!("{byte:02x}"))
            .collect()
    }

    fn hydration(source: &[u8], file_id: u32, generation: u64, status: &str) -> String {
        let admitted = status == "CURRENT";
        let sha = sha256_hex(source);
        let locator = if admitted {
            json!({
                "file_id": file_id,
                "relative_path": "src/module.py",
                "source_generation": generation,
                "byte_len": source.len(),
                "sha256": sha,
            })
        } else {
            Value::Null
        };
        json!({
            "version": "AURA_ASTGE_ANCHOR_HYDRATION_V1",
            "anchor_owner_reused": "source-owner://post-edit-profiled",
            "source_body_witness_required": true,
            "unknown_or_stale_hydration_admitted": false,
            "codemap_digest8_currentness_authority": false,
            "source_authority_minted": false,
            "project007_runtime_implemented": false,
            "anchor_receipts": [{
                "anchor_id": "anchor.post-edit",
                "path": "src/module.py",
                "semantic_id": "SEM:POSTEDIT",
                "signature_hash": "sig",
                "anchor_projection_resolved": true,
                "semantic_identity_minted_by_bridge": false,
                "source_authority_minted": false,
                "body_currentness_status": status,
                "hydration_admitted": admitted,
                "reason": if admitted { "EXACT_SOURCE_BODY_WITNESS_MATCH" } else { "SOURCE_BODY_DIGEST_DRIFT" },
                "witness_ref": if admitted { "witness://post-edit/body" } else { "" },
                "expected_byte_len": source.len(),
                "observed_byte_len": source.len(),
                "expected_body_sha256": sha,
                "observed_body_sha256": sha,
                "locator": locator,
            }],
            "source_locators_v1": [],
        })
        .to_string()
    }

    fn changed_candidate(setup: &Setup) -> (Vec<u8>, Vec<AuthorizedSpanV1>, Vec<ReplacementV1>) {
        let mut candidate = SOURCE.as_bytes().to_vec();
        candidate.splice(
            setup.edit_start..setup.edit_start + 1,
            b"100".iter().copied(),
        );
        let start = setup.edit_start as u64;
        (
            candidate,
            vec![AuthorizedSpanV1 {
                start,
                end: start + 1,
            }],
            vec![ReplacementV1 {
                start,
                end: start + 1,
                replacement: b"100".to_vec(),
            }],
        )
    }

    fn selector(
        source: &str,
        file_id: u32,
        supplied: &HashMap<u64, [u8; 32]>,
    ) -> CandidateProfiledScopeSelectorV1 {
        let profiled = build_profiled_python_scopes(
            source,
            file_id,
            "source-owner://post-edit-profiled",
            "candidate-generation",
            supplied,
        )
        .unwrap();
        let scope = profiled
            .profiled_scopes
            .iter()
            .find(|scope| scope.name == "inner")
            .unwrap();
        CandidateProfiledScopeSelectorV1 {
            syntax_ordinal: scope.syntax_ordinal.unwrap(),
            file_id: scope.file_id,
            byte_start: scope.byte_start,
            byte_end: scope.byte_end,
            semantic_handle_digest: scope.semantic_handle_digest.unwrap(),
        }
    }

    fn valid_post_edit(setup: &Setup) -> PostEditProfiledScopeCurrentV1 {
        let (candidate, spans, replacements) = changed_candidate(setup);
        let candidate_text = std::str::from_utf8(&candidate).unwrap();
        let candidate_handles = handles(candidate_text, setup.file_id);
        let selected = selector(candidate_text, setup.file_id, &candidate_handles);
        admit_post_edit_profiled_scope_current(
            &setup.scope_index,
            setup.selected_scope_id,
            &setup.catalog,
            &setup.record,
            SourceGenerationV1::new(12),
            SOURCE.as_bytes(),
            &candidate,
            &spans,
            &replacements,
            &hydration(&candidate, setup.file_id, 13, "CURRENT"),
            "anchor.post-edit",
            &candidate_handles,
            SourceGenerationV1::new(13),
            &selected,
        )
        .unwrap()
    }

    #[test]
    fn current_post_edit_scope_is_exact_canonical_definition_target() {
        let setup = setup("positive", 12);
        let current = valid_post_edit(&setup);
        let relation = require_candidate_definition_target_relation(&current).unwrap();
        assert_eq!(relation.definition_name, "inner");
        assert_eq!(
            relation.definition_target_scope_id,
            current.selected_candidate_scope.scope_id
        );
        assert_ne!(
            relation.definition_owner_scope_id,
            relation.definition_target_scope_id
        );
        assert!(relation.selected_current_scope_is_binding_target);
        assert!(relation.binding_owner_is_selected_parent);
        assert!(!relation.local_scope_id_is_semantic_identity);
        fs::remove_dir_all(setup.root).unwrap();
    }

    #[test]
    fn full_composition_retains_currentness_and_claim_ceiling() {
        let setup = setup("full", 12);
        let (candidate, spans, replacements) = changed_candidate(&setup);
        let candidate_text = std::str::from_utf8(&candidate).unwrap();
        let candidate_handles = handles(candidate_text, setup.file_id);
        let selected = selector(candidate_text, setup.file_id, &candidate_handles);
        let receipt = admit_post_edit_canonical_definition_target_current(
            &setup.scope_index,
            setup.selected_scope_id,
            &setup.catalog,
            &setup.record,
            SourceGenerationV1::new(12),
            SOURCE.as_bytes(),
            &candidate,
            &spans,
            &replacements,
            &hydration(&candidate, setup.file_id, 13, "CURRENT"),
            "anchor.post-edit",
            &candidate_handles,
            SourceGenerationV1::new(13),
            &selected,
        )
        .unwrap();
        assert!(receipt.post_edit_profiled_scope_current);
        assert!(receipt.canonical_definition_target_current);
        assert_eq!(receipt.source_generation.value(), 13);
        assert_eq!(
            receipt
                .post_edit_current
                .candidate_source_generation_coordinate
                .domain,
            GenerationDomainV1::Source
        );
        assert!(!receipt.runtime_name_resolution_proven);
        assert!(!receipt.call_graph_proven);
        assert!(!receipt.semantic_patch_correctness_proven);
        assert!(!receipt.b_minus_approved);
        assert!(!receipt.commit_authorized);
        assert!(!receipt.execution_authorized);
        assert!(!receipt.human_authority);
        assert!(!receipt.external_effect_authorized);
        fs::remove_dir_all(setup.root).unwrap();
    }

    #[test]
    fn tampered_binding_owner_cannot_be_relabelled_as_current_definition_target() {
        let setup = setup("owner-tamper", 12);
        let mut current = valid_post_edit(&setup);
        let selected = current.selected_candidate_scope.clone();
        let binding = current
            .candidate_current
            .profiled_scopes
            .profiled_bindings
            .iter_mut()
            .find(|binding| binding.target_scope_id == selected.scope_id)
            .unwrap();
        binding.owner_scope_id = selected.scope_id;
        let error = require_candidate_definition_target_relation(&current).unwrap_err();
        assert!(matches!(
            error,
            PostEditCanonicalScopeErrorV1::BindingOwnerParentMismatch { .. }
        ));
        fs::remove_dir_all(setup.root).unwrap();
    }

    #[test]
    fn detached_selected_scope_receipt_is_rejected() {
        let setup = setup("detached", 12);
        let mut current = valid_post_edit(&setup);
        current.selected_candidate_scope.name = "forged".to_string();
        let error = require_candidate_definition_target_relation(&current).unwrap_err();
        assert!(matches!(
            error,
            PostEditCanonicalScopeErrorV1::SelectedScopeNotInCandidateProfile
        ));
        fs::remove_dir_all(setup.root).unwrap();
    }

    #[test]
    fn target_binding_anchor_substitution_is_rejected() {
        let setup = setup("binding-anchor", 12);
        let mut current = valid_post_edit(&setup);
        let selected = current.selected_candidate_scope.clone();
        let binding = current
            .candidate_current
            .profiled_scopes
            .profiled_bindings
            .iter_mut()
            .find(|binding| binding.target_scope_id == selected.scope_id)
            .unwrap();
        binding.syntax_ordinal = binding.syntax_ordinal.saturating_add(1);
        let error = require_candidate_definition_target_relation(&current).unwrap_err();
        assert!(matches!(
            error,
            PostEditCanonicalScopeErrorV1::DefinitionBindingMissing(_)
        ));
        fs::remove_dir_all(setup.root).unwrap();
    }
}
