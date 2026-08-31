#![forbid(unsafe_code)]

use aura_k27_astge_syntax_profile::{
    admit_syntax_graph, NormalizationProfileV1, ParserGrammarBindingV1, SourceBindingV1,
    SyntaxEdgeProjectionV1, SyntaxGraphAdmissionError, SyntaxGraphIdentityV1,
    SyntaxNodeProjectionV1,
};
use serde_json::Value;
use std::error::Error;
use std::fmt::{Display, Formatter};

const HYDRATION_VERSION: &str = "AURA_ASTGE_ANCHOR_HYDRATION_V1";
const CURRENT: &str = "CURRENT";
const CURRENT_REASON: &str = "EXACT_SOURCE_BODY_WITNESS_MATCH";
const GENERATION_REF_PREFIX: &str = "AURA_SOURCE_BODY_GENERATION_V1:";

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CurrentSyntaxHydrationIdentityV1 {
    pub syntax_graph: SyntaxGraphIdentityV1,
    pub anchor_id: String,
    pub relative_path: String,
    pub file_id: u64,
    pub source_generation: u64,
    pub source_generation_ref: String,
    pub source_sha256: [u8; 32],
    pub source_byte_len: u64,
    pub anchor_owner_ref: String,
    pub witness_ref: String,
    pub body_currentness_status: String,
    pub hydration_admitted: bool,
    pub source_authority_minted: bool,
    pub semantic_authority_minted: bool,
    pub review_authority_minted: bool,
    pub external_effect: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CurrentSyntaxHydrationError {
    InvalidJson,
    WrongHydrationVersion,
    HydrationContractInvalid(&'static str),
    AnchorMissing,
    AnchorAmbiguous,
    BodyUnknown,
    BodyStale,
    HydrationNotAdmitted,
    MissingLocator,
    InvalidLocator(&'static str),
    CurrentReceiptInconsistent(&'static str),
    SyntaxSpanOutsideCurrentBody { end_byte: u64, body_len: u64 },
    Syntax(SyntaxGraphAdmissionError),
}

impl Display for CurrentSyntaxHydrationError {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        write!(f, "{self:?}")
    }
}

impl Error for CurrentSyntaxHydrationError {}

impl From<SyntaxGraphAdmissionError> for CurrentSyntaxHydrationError {
    fn from(value: SyntaxGraphAdmissionError) -> Self {
        Self::Syntax(value)
    }
}

pub fn canonical_source_generation_ref(source_generation: u64) -> String {
    format!("{GENERATION_REF_PREFIX}{source_generation}")
}

/// Bind PR486 syntax identity to one PR488 CURRENT body receipt.
///
/// Callers supply parser/grammar/profile and syntax projections, but cannot supply
/// a separate source binding. File ID, source generation and full-body SHA-256 are
/// derived from the independently witnessed hydration receipt. This prevents a
/// currentness receipt from being pasted onto a graph identity generated for a
/// different source body.
pub fn admit_current_syntax_hydration(
    hydration_json: &str,
    anchor_id: &str,
    grammar: &ParserGrammarBindingV1,
    profile: &NormalizationProfileV1,
    ordered_nodes: &[SyntaxNodeProjectionV1],
    ordered_edges: &[SyntaxEdgeProjectionV1],
) -> Result<CurrentSyntaxHydrationIdentityV1, CurrentSyntaxHydrationError> {
    let root: Value = serde_json::from_str(hydration_json)
        .map_err(|_| CurrentSyntaxHydrationError::InvalidJson)?;
    let object = root
        .as_object()
        .ok_or(CurrentSyntaxHydrationError::InvalidJson)?;

    if string_field(object.get("version"))? != HYDRATION_VERSION {
        return Err(CurrentSyntaxHydrationError::WrongHydrationVersion);
    }
    if exact_bool(object.get("source_body_witness_required"))? != true {
        return Err(CurrentSyntaxHydrationError::HydrationContractInvalid(
            "source_body_witness_required",
        ));
    }
    if exact_bool(object.get("unknown_or_stale_hydration_admitted"))? != false {
        return Err(CurrentSyntaxHydrationError::HydrationContractInvalid(
            "unknown_or_stale_hydration_admitted",
        ));
    }
    if exact_bool(object.get("source_authority_minted"))? != false {
        return Err(CurrentSyntaxHydrationError::HydrationContractInvalid(
            "source_authority_minted",
        ));
    }
    let anchor_owner_ref = string_field(object.get("anchor_owner_reused"))?.to_owned();
    if anchor_owner_ref.trim().is_empty() {
        return Err(CurrentSyntaxHydrationError::HydrationContractInvalid(
            "anchor_owner_reused",
        ));
    }

    let receipts = object
        .get("anchor_receipts")
        .and_then(Value::as_array)
        .ok_or(CurrentSyntaxHydrationError::HydrationContractInvalid(
            "anchor_receipts",
        ))?;
    let matches: Vec<_> = receipts
        .iter()
        .filter(|receipt| {
            receipt
                .get("anchor_id")
                .and_then(Value::as_str)
                .is_some_and(|candidate| candidate == anchor_id)
        })
        .collect();
    if matches.is_empty() {
        return Err(CurrentSyntaxHydrationError::AnchorMissing);
    }
    if matches.len() != 1 {
        return Err(CurrentSyntaxHydrationError::AnchorAmbiguous);
    }
    let receipt =
        matches[0]
            .as_object()
            .ok_or(CurrentSyntaxHydrationError::HydrationContractInvalid(
                "anchor_receipt",
            ))?;

    let currentness = string_field(receipt.get("body_currentness_status"))?;
    match currentness {
        "UNKNOWN" => return Err(CurrentSyntaxHydrationError::BodyUnknown),
        "STALE" => return Err(CurrentSyntaxHydrationError::BodyStale),
        CURRENT => {}
        _ => {
            return Err(CurrentSyntaxHydrationError::HydrationContractInvalid(
                "body_currentness_status",
            ))
        }
    }
    if exact_bool(receipt.get("hydration_admitted"))? != true {
        return Err(CurrentSyntaxHydrationError::HydrationNotAdmitted);
    }
    if string_field(receipt.get("reason"))? != CURRENT_REASON {
        return Err(CurrentSyntaxHydrationError::CurrentReceiptInconsistent(
            "reason",
        ));
    }
    if exact_bool(receipt.get("source_authority_minted"))? != false
        || exact_bool(receipt.get("semantic_identity_minted_by_bridge"))? != false
    {
        return Err(CurrentSyntaxHydrationError::HydrationContractInvalid(
            "authority ceiling",
        ));
    }

    let locator = receipt
        .get("locator")
        .and_then(Value::as_object)
        .ok_or(CurrentSyntaxHydrationError::MissingLocator)?;
    let file_id = u64_field(locator.get("file_id"), "file_id")?;
    let relative_path = string_field(locator.get("relative_path"))?.to_owned();
    if relative_path != string_field(receipt.get("path"))? {
        return Err(CurrentSyntaxHydrationError::CurrentReceiptInconsistent(
            "relative_path",
        ));
    }
    let source_generation = u64_field(locator.get("source_generation"), "source_generation")?;
    let source_byte_len = u64_field(locator.get("byte_len"), "byte_len")?;
    let locator_sha = string_field(locator.get("sha256"))?;
    let source_sha256 = parse_sha256(locator_sha)?;

    let expected_len = u64_field(receipt.get("expected_byte_len"), "expected_byte_len")?;
    let observed_len = u64_field(receipt.get("observed_byte_len"), "observed_byte_len")?;
    if expected_len != observed_len || observed_len != source_byte_len {
        return Err(CurrentSyntaxHydrationError::CurrentReceiptInconsistent(
            "body length",
        ));
    }
    let expected_sha = string_field(receipt.get("expected_body_sha256"))?;
    let observed_sha = string_field(receipt.get("observed_body_sha256"))?;
    if expected_sha != observed_sha || observed_sha != locator_sha {
        return Err(CurrentSyntaxHydrationError::CurrentReceiptInconsistent(
            "body digest",
        ));
    }
    let witness_ref = string_field(receipt.get("witness_ref"))?.to_owned();
    if witness_ref.trim().is_empty() {
        return Err(CurrentSyntaxHydrationError::CurrentReceiptInconsistent(
            "witness_ref",
        ));
    }

    for node in ordered_nodes {
        if node.end_byte > source_byte_len {
            return Err(CurrentSyntaxHydrationError::SyntaxSpanOutsideCurrentBody {
                end_byte: node.end_byte,
                body_len: source_byte_len,
            });
        }
    }

    let source_generation_ref = canonical_source_generation_ref(source_generation);
    let source = SourceBindingV1 {
        source_owner_ref: anchor_owner_ref.clone(),
        source_generation_ref: source_generation_ref.clone(),
        file_id,
        source_sha256,
    };
    let syntax_graph = admit_syntax_graph(grammar, profile, &source, ordered_nodes, ordered_edges)?;

    Ok(CurrentSyntaxHydrationIdentityV1 {
        syntax_graph,
        anchor_id: anchor_id.to_owned(),
        relative_path,
        file_id,
        source_generation,
        source_generation_ref,
        source_sha256,
        source_byte_len,
        anchor_owner_ref,
        witness_ref,
        body_currentness_status: CURRENT.to_owned(),
        hydration_admitted: true,
        source_authority_minted: false,
        semantic_authority_minted: false,
        review_authority_minted: false,
        external_effect: false,
    })
}

fn exact_bool(value: Option<&Value>) -> Result<bool, CurrentSyntaxHydrationError> {
    value
        .and_then(Value::as_bool)
        .ok_or(CurrentSyntaxHydrationError::HydrationContractInvalid(
            "expected boolean",
        ))
}

fn string_field(value: Option<&Value>) -> Result<&str, CurrentSyntaxHydrationError> {
    value
        .and_then(Value::as_str)
        .ok_or(CurrentSyntaxHydrationError::HydrationContractInvalid(
            "expected string",
        ))
}

fn u64_field(
    value: Option<&Value>,
    field: &'static str,
) -> Result<u64, CurrentSyntaxHydrationError> {
    value
        .and_then(Value::as_u64)
        .ok_or(CurrentSyntaxHydrationError::InvalidLocator(field))
}

fn parse_sha256(value: &str) -> Result<[u8; 32], CurrentSyntaxHydrationError> {
    if value.len() != 64
        || !value
            .bytes()
            .all(|byte| byte.is_ascii_hexdigit() && !byte.is_ascii_uppercase())
    {
        return Err(CurrentSyntaxHydrationError::InvalidLocator("sha256"));
    }
    let mut out = [0u8; 32];
    for (index, byte) in out.iter_mut().enumerate() {
        *byte = u8::from_str_radix(&value[index * 2..index * 2 + 2], 16)
            .map_err(|_| CurrentSyntaxHydrationError::InvalidLocator("sha256"))?;
    }
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;
    use aura_k27_astge_syntax_profile::{NodeSelectionPolicyV1, SyntaxEdgeProjectionV1};

    fn grammar() -> ParserGrammarBindingV1 {
        ParserGrammarBindingV1 {
            parser_binding_name: "tree-sitter-python".into(),
            parser_binding_version: "0.25.10".into(),
            grammar_name: "python".into(),
            grammar_version: "0.25.0".into(),
            grammar_abi_version: 15,
        }
    }

    fn profile(reference: &str) -> NormalizationProfileV1 {
        NormalizationProfileV1 {
            profile_ref: reference.into(),
            node_selection: NodeSelectionPolicyV1::NamedNodesOnly,
            direct_parent_child_edges_only: true,
        }
    }

    fn nodes() -> Vec<SyntaxNodeProjectionV1> {
        vec![
            SyntaxNodeProjectionV1 {
                local_node_id: 90,
                grammar_kind_id: 1,
                grammar_kind_name: "module".into(),
                named: true,
                start_byte: 0,
                end_byte: 12,
            },
            SyntaxNodeProjectionV1 {
                local_node_id: 7,
                grammar_kind_id: 9,
                grammar_kind_name: "function_definition".into(),
                named: true,
                start_byte: 0,
                end_byte: 12,
            },
        ]
    }

    fn edges() -> Vec<SyntaxEdgeProjectionV1> {
        vec![SyntaxEdgeProjectionV1 {
            parent_local_node_id: 90,
            child_local_node_id: 7,
        }]
    }

    fn hydration(status: &str, admitted: bool, generation: u64, sha: &str) -> String {
        let locator = if admitted {
            serde_json::json!({
                "file_id": 7,
                "relative_path": "src/example.py",
                "source_generation": generation,
                "byte_len": 12,
                "sha256": sha,
            })
        } else {
            Value::Null
        };
        serde_json::json!({
            "version": HYDRATION_VERSION,
            "anchor_owner_reused": "scripts/aura_source_anchor_map.py",
            "source_body_witness_required": true,
            "unknown_or_stale_hydration_admitted": false,
            "codemap_digest8_currentness_authority": false,
            "source_authority_minted": false,
            "project007_runtime_implemented": false,
            "anchor_receipts": [{
                "anchor_id": "anchor.example",
                "path": "src/example.py",
                "semantic_id": "SEM:EXAMPLE",
                "signature_hash": "sig",
                "anchor_projection_resolved": true,
                "semantic_identity_minted_by_bridge": false,
                "source_authority_minted": false,
                "body_currentness_status": status,
                "hydration_admitted": admitted,
                "reason": if status == CURRENT { CURRENT_REASON } else if status == "STALE" { "SOURCE_BODY_DIGEST_DRIFT" } else { "MISSING_SOURCE_BODY_WITNESS" },
                "witness_ref": if admitted { "witness://body/7/41" } else { "" },
                "expected_byte_len": if admitted { 12 } else { 0 },
                "observed_byte_len": if admitted { 12 } else { 0 },
                "expected_body_sha256": if admitted { sha } else { "" },
                "observed_body_sha256": if admitted { sha } else { "" },
                "locator": locator,
            }],
            "source_locators_v1": [],
        })
        .to_string()
    }

    const SHA_A: &str = "4444444444444444444444444444444444444444444444444444444444444444";
    const SHA_B: &str = "5555555555555555555555555555555555555555555555555555555555555555";

    #[test]
    fn current_body_derives_source_binding_and_admits_syntax_identity() {
        let result = admit_current_syntax_hydration(
            &hydration(CURRENT, true, 41, SHA_A),
            "anchor.example",
            &grammar(),
            &profile("python/NAMED_ONLY/v1"),
            &nodes(),
            &edges(),
        )
        .unwrap();
        assert_eq!(result.file_id, 7);
        assert_eq!(result.source_generation, 41);
        assert_eq!(
            result.source_generation_ref,
            "AURA_SOURCE_BODY_GENERATION_V1:41"
        );
        assert_eq!(result.source_byte_len, 12);
        assert_eq!(result.body_currentness_status, CURRENT);
        assert!(result.hydration_admitted);
        assert!(!result.source_authority_minted);
        assert!(!result.semantic_authority_minted);
        assert!(!result.review_authority_minted);
        assert!(!result.external_effect);
    }

    #[test]
    fn stale_and_unknown_bodies_cannot_mint_current_syntax_identity() {
        let stale = hydration("STALE", false, 41, SHA_A);
        let unknown = hydration("UNKNOWN", false, 41, SHA_A);
        assert_eq!(
            admit_current_syntax_hydration(
                &stale,
                "anchor.example",
                &grammar(),
                &profile("python/NAMED_ONLY/v1"),
                &nodes(),
                &edges(),
            ),
            Err(CurrentSyntaxHydrationError::BodyStale)
        );
        assert_eq!(
            admit_current_syntax_hydration(
                &unknown,
                "anchor.example",
                &grammar(),
                &profile("python/NAMED_ONLY/v1"),
                &nodes(),
                &edges(),
            ),
            Err(CurrentSyntaxHydrationError::BodyUnknown)
        );
    }

    #[test]
    fn source_generation_namespace_is_explicit_and_changes_graph_identity() {
        let a = admit_current_syntax_hydration(
            &hydration(CURRENT, true, 41, SHA_A),
            "anchor.example",
            &grammar(),
            &profile("python/NAMED_ONLY/v1"),
            &nodes(),
            &edges(),
        )
        .unwrap();
        let b = admit_current_syntax_hydration(
            &hydration(CURRENT, true, 42, SHA_A),
            "anchor.example",
            &grammar(),
            &profile("python/NAMED_ONLY/v1"),
            &nodes(),
            &edges(),
        )
        .unwrap();
        assert_ne!(a.source_generation_ref, b.source_generation_ref);
        assert_ne!(a.syntax_graph.graph_sha256, b.syntax_graph.graph_sha256);
    }

    #[test]
    fn body_digest_change_changes_syntax_identity() {
        let a = admit_current_syntax_hydration(
            &hydration(CURRENT, true, 41, SHA_A),
            "anchor.example",
            &grammar(),
            &profile("python/NAMED_ONLY/v1"),
            &nodes(),
            &edges(),
        )
        .unwrap();
        let b = admit_current_syntax_hydration(
            &hydration(CURRENT, true, 41, SHA_B),
            "anchor.example",
            &grammar(),
            &profile("python/NAMED_ONLY/v1"),
            &nodes(),
            &edges(),
        )
        .unwrap();
        assert_ne!(a.syntax_graph.graph_sha256, b.syntax_graph.graph_sha256);
    }

    #[test]
    fn normalization_profile_remains_an_independent_identity_axis() {
        let body = hydration(CURRENT, true, 41, SHA_A);
        let a = admit_current_syntax_hydration(
            &body,
            "anchor.example",
            &grammar(),
            &profile("python/NAMED_ONLY/v1"),
            &nodes(),
            &edges(),
        )
        .unwrap();
        let b = admit_current_syntax_hydration(
            &body,
            "anchor.example",
            &grammar(),
            &profile("python/NAMED_ONLY/v2"),
            &nodes(),
            &edges(),
        )
        .unwrap();
        assert_ne!(a.syntax_graph.graph_sha256, b.syntax_graph.graph_sha256);
    }

    #[test]
    fn syntax_projection_cannot_extend_past_current_body() {
        let mut too_long = nodes();
        too_long[1].end_byte = 13;
        assert_eq!(
            admit_current_syntax_hydration(
                &hydration(CURRENT, true, 41, SHA_A),
                "anchor.example",
                &grammar(),
                &profile("python/NAMED_ONLY/v1"),
                &too_long,
                &edges(),
            ),
            Err(CurrentSyntaxHydrationError::SyntaxSpanOutsideCurrentBody {
                end_byte: 13,
                body_len: 12,
            })
        );
    }

    #[test]
    fn inconsistent_current_length_or_digest_is_rejected() {
        let mut value: Value = serde_json::from_str(&hydration(CURRENT, true, 41, SHA_A)).unwrap();
        value["anchor_receipts"][0]["observed_byte_len"] = Value::from(11u64);
        assert_eq!(
            admit_current_syntax_hydration(
                &value.to_string(),
                "anchor.example",
                &grammar(),
                &profile("python/NAMED_ONLY/v1"),
                &nodes(),
                &edges(),
            ),
            Err(CurrentSyntaxHydrationError::CurrentReceiptInconsistent(
                "body length"
            ))
        );

        let mut value: Value = serde_json::from_str(&hydration(CURRENT, true, 41, SHA_A)).unwrap();
        value["anchor_receipts"][0]["observed_body_sha256"] = Value::from(SHA_B);
        assert_eq!(
            admit_current_syntax_hydration(
                &value.to_string(),
                "anchor.example",
                &grammar(),
                &profile("python/NAMED_ONLY/v1"),
                &nodes(),
                &edges(),
            ),
            Err(CurrentSyntaxHydrationError::CurrentReceiptInconsistent(
                "body digest"
            ))
        );
    }

    #[test]
    fn duplicate_anchor_receipts_are_ambiguous() {
        let mut value: Value = serde_json::from_str(&hydration(CURRENT, true, 41, SHA_A)).unwrap();
        let duplicate = value["anchor_receipts"][0].clone();
        value["anchor_receipts"]
            .as_array_mut()
            .unwrap()
            .push(duplicate);
        assert_eq!(
            admit_current_syntax_hydration(
                &value.to_string(),
                "anchor.example",
                &grammar(),
                &profile("python/NAMED_ONLY/v1"),
                &nodes(),
                &edges(),
            ),
            Err(CurrentSyntaxHydrationError::AnchorAmbiguous)
        );
    }
}
