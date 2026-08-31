use crate::{coordinate_for_sid, EdgeInput, NodeInput, MAX_EDGES_PER_BLOCK};
use std::io::{Error, ErrorKind, Result as IoResult};
use tree_sitter::{Node, Parser};

/// V1 uses a single structural edge kind: direct Tree-sitter parent -> child.
/// Symbol/call/dataflow edges remain separate successor proof planes.
pub const AST_CHILD_EDGE_KIND: u8 = 1;
const AST_PLACEMENT_DOMAIN_AXIS: u8 = 0;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct IngestedAst {
    pub root_node_id: u64,
    pub file_id: u32,
    pub source_len: u32,
    pub nodes: Vec<NodeInput>,
}

/// Parse one Rust source file with Tree-sitter and normalize the exact syntax tree
/// into PR460's deterministic dense-node storage input.
///
/// K27 placement is deliberately derived from a caller-supplied physical
/// namespace plus file/node coordinates. It is not semantic identity or source
/// currentness. The semantic structure of this V1 artifact is node kind, byte
/// span, file identity, and direct AST-child topology.
pub fn parse_rust_source(
    source: &str,
    file_id: u32,
    placement_namespace: &str,
) -> IoResult<IngestedAst> {
    if placement_namespace.trim().is_empty() {
        return Err(Error::new(
            ErrorKind::InvalidInput,
            "placement namespace is required",
        ));
    }
    let source_len = u32::try_from(source.len()).map_err(|_| {
        Error::new(
            ErrorKind::InvalidInput,
            "source exceeds V1 32-bit byte-span contract",
        )
    })?;

    let language = tree_sitter_rust::LANGUAGE.into();
    let mut parser = Parser::new();
    parser.set_language(&language).map_err(|error| {
        Error::new(
            ErrorKind::InvalidData,
            format!("Tree-sitter Rust language rejected: {error}"),
        )
    })?;
    let tree = parser
        .parse(source.as_bytes(), None)
        .ok_or_else(|| Error::new(ErrorKind::InvalidData, "Tree-sitter returned no syntax tree"))?;
    let root = tree.root_node();
    if root.has_error() {
        return Err(Error::new(
            ErrorKind::InvalidData,
            "Tree-sitter syntax tree contains an error node",
        ));
    }

    let mut nodes = Vec::<NodeInput>::new();
    let root_node_id = append_preorder_node(
        root,
        source.len(),
        file_id,
        placement_namespace,
        &mut nodes,
    )?;
    if root_node_id != 0 {
        return Err(Error::new(
            ErrorKind::InvalidData,
            "V1 Tree-sitter root must normalize to node id zero",
        ));
    }

    Ok(IngestedAst {
        root_node_id,
        file_id,
        source_len,
        nodes,
    })
}

fn append_preorder_node(
    node: Node<'_>,
    source_len: usize,
    file_id: u32,
    placement_namespace: &str,
    nodes: &mut Vec<NodeInput>,
) -> IoResult<u64> {
    let node_id = u64::try_from(nodes.len())
        .map_err(|_| Error::new(ErrorKind::InvalidData, "node table exceeds u64 identity space"))?;
    let byte_start = u32::try_from(node.start_byte())
        .map_err(|_| Error::new(ErrorKind::InvalidData, "node start exceeds V1 span"))?;
    let byte_end = u32::try_from(node.end_byte())
        .map_err(|_| Error::new(ErrorKind::InvalidData, "node end exceeds V1 span"))?;
    if node.end_byte() > source_len || byte_end < byte_start {
        return Err(Error::new(
            ErrorKind::InvalidData,
            "Tree-sitter node span is outside source bytes",
        ));
    }
    if node.child_count() > MAX_EDGES_PER_BLOCK {
        return Err(Error::new(
            ErrorKind::InvalidData,
            "Tree-sitter node degree exceeds V1 single-row capacity",
        ));
    }

    let placement_sid = format!("{placement_namespace}\0{file_id}\0{node_id}");
    nodes.push(NodeInput {
        node_id,
        placement_coord_packed: coordinate_for_sid(&placement_sid, AST_PLACEMENT_DOMAIN_AXIS).packed,
        type_id: u32::from(node.kind_id()),
        file_id,
        byte_start,
        byte_end,
        flags: u32::from(node.is_named()),
        edges: Vec::with_capacity(node.child_count()),
    });

    let mut child_edges = Vec::<EdgeInput>::with_capacity(node.child_count());
    let mut cursor = node.walk();
    for child in node.children(&mut cursor) {
        let child_id = append_preorder_node(
            child,
            source_len,
            file_id,
            placement_namespace,
            nodes,
        )?;
        child_edges.push(EdgeInput {
            target_node_id: child_id,
            kind: AST_CHILD_EDGE_KIND,
        });
    }
    nodes[node_id as usize].edges = child_edges;
    Ok(node_id)
}
