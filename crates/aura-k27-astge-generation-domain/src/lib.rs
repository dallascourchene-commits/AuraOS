#![forbid(unsafe_code)]

use aura_k27_astge::StorageGenerationBindingV1;
use std::fmt::{Debug, Formatter};
use std::marker::PhantomData;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum GenerationDomainV1 {
    Snapshot,
    Placement,
    Source,
    GraphServing,
}

pub trait GenerationAxisV1: Copy + 'static {
    const DOMAIN: GenerationDomainV1;
    const LABEL: &'static str;
}

#[derive(Clone, Copy, PartialEq, Eq, Hash)]
pub enum SnapshotAxisV1 {}
impl GenerationAxisV1 for SnapshotAxisV1 {
    const DOMAIN: GenerationDomainV1 = GenerationDomainV1::Snapshot;
    const LABEL: &'static str = "snapshot";
}

#[derive(Clone, Copy, PartialEq, Eq, Hash)]
pub enum PlacementAxisV1 {}
impl GenerationAxisV1 for PlacementAxisV1 {
    const DOMAIN: GenerationDomainV1 = GenerationDomainV1::Placement;
    const LABEL: &'static str = "placement";
}

#[derive(Clone, Copy, PartialEq, Eq, Hash)]
pub enum SourceAxisV1 {}
impl GenerationAxisV1 for SourceAxisV1 {
    const DOMAIN: GenerationDomainV1 = GenerationDomainV1::Source;
    const LABEL: &'static str = "source";
}

#[derive(Clone, Copy, PartialEq, Eq, Hash)]
pub enum GraphServingAxisV1 {}
impl GenerationAxisV1 for GraphServingAxisV1 {
    const DOMAIN: GenerationDomainV1 = GenerationDomainV1::GraphServing;
    const LABEL: &'static str = "graph_serving";
}

/// A generation value whose axis is part of its Rust type.
///
/// Cross-axis equality is intentionally unavailable. Code that wants to compare or
/// transport different axes must first project each value to `GenerationCoordinateV1`,
/// where the domain tag remains explicit.
///
/// ```compile_fail
/// use aura_k27_astge_generation_domain::{PlacementGenerationV1, SnapshotGenerationV1};
/// let snapshot = SnapshotGenerationV1::new(7);
/// let placement = PlacementGenerationV1::new(7);
/// assert_eq!(snapshot, placement);
/// ```
#[derive(Clone, Copy, PartialEq, Eq, Hash)]
pub struct GenerationV1<A: GenerationAxisV1> {
    value: u64,
    _axis: PhantomData<A>,
}

impl<A: GenerationAxisV1> GenerationV1<A> {
    pub const fn new(value: u64) -> Self {
        Self {
            value,
            _axis: PhantomData,
        }
    }

    pub const fn value(self) -> u64 {
        self.value
    }

    pub const fn coordinate(self) -> GenerationCoordinateV1 {
        GenerationCoordinateV1 {
            domain: A::DOMAIN,
            value: self.value,
        }
    }
}

impl<A: GenerationAxisV1> Debug for GenerationV1<A> {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("GenerationV1")
            .field("domain", &A::LABEL)
            .field("value", &self.value)
            .finish()
    }
}

pub type SnapshotGenerationV1 = GenerationV1<SnapshotAxisV1>;
pub type PlacementGenerationV1 = GenerationV1<PlacementAxisV1>;
pub type SourceGenerationV1 = GenerationV1<SourceAxisV1>;
pub type GraphServingGenerationV1 = GenerationV1<GraphServingAxisV1>;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct GenerationCoordinateV1 {
    pub domain: GenerationDomainV1,
    pub value: u64,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct MmapGenerationAxesV1 {
    pub snapshot: SnapshotGenerationV1,
    pub placement: PlacementGenerationV1,
}

impl MmapGenerationAxesV1 {
    pub const fn new(
        snapshot: SnapshotGenerationV1,
        placement: PlacementGenerationV1,
    ) -> Self {
        Self {
            snapshot,
            placement,
        }
    }

    pub fn from_current_storage(
        snapshot_generation: u64,
        binding: &StorageGenerationBindingV1,
    ) -> Self {
        Self::new(
            SnapshotGenerationV1::new(snapshot_generation),
            PlacementGenerationV1::new(binding.placement_generation),
        )
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct TransactionGenerationAxesV1 {
    pub source: SourceGenerationV1,
    pub graph_serving: GraphServingGenerationV1,
}

impl TransactionGenerationAxesV1 {
    pub const fn new(
        source: SourceGenerationV1,
        graph_serving: GraphServingGenerationV1,
    ) -> Self {
        Self {
            source,
            graph_serving,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GenerationDomainErrorV1 {
    DomainMismatch {
        expected: GenerationDomainV1,
        observed: GenerationDomainV1,
    },
    ValueMismatch {
        domain: GenerationDomainV1,
        expected: u64,
        observed: u64,
    },
}

pub fn require_coordinate(
    expected: GenerationCoordinateV1,
    observed: GenerationCoordinateV1,
) -> Result<(), GenerationDomainErrorV1> {
    if expected.domain != observed.domain {
        return Err(GenerationDomainErrorV1::DomainMismatch {
            expected: expected.domain,
            observed: observed.domain,
        });
    }
    if expected.value != observed.value {
        return Err(GenerationDomainErrorV1::ValueMismatch {
            domain: expected.domain,
            expected: expected.value,
            observed: observed.value,
        });
    }
    Ok(())
}

/// This function intentionally accepts only a snapshot generation. Passing a
/// placement generation is a compile-time error rather than a runtime comparison.
///
/// ```compile_fail
/// use aura_k27_astge_generation_domain::{require_snapshot_generation, PlacementGenerationV1};
/// let placement = PlacementGenerationV1::new(9);
/// require_snapshot_generation(placement, 9).unwrap();
/// ```
pub fn require_snapshot_generation(
    observed: SnapshotGenerationV1,
    expected_raw: u64,
) -> Result<(), GenerationDomainErrorV1> {
    require_coordinate(
        SnapshotGenerationV1::new(expected_raw).coordinate(),
        observed.coordinate(),
    )
}

pub fn require_placement_generation(
    observed: PlacementGenerationV1,
    expected_raw: u64,
) -> Result<(), GenerationDomainErrorV1> {
    require_coordinate(
        PlacementGenerationV1::new(expected_raw).coordinate(),
        observed.coordinate(),
    )
}

pub fn require_graph_serving_generation(
    observed: GraphServingGenerationV1,
    expected_raw: u64,
) -> Result<(), GenerationDomainErrorV1> {
    require_coordinate(
        GraphServingGenerationV1::new(expected_raw).coordinate(),
        observed.coordinate(),
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn equal_numeric_values_remain_distinct_generation_coordinates() {
        let snapshot = SnapshotGenerationV1::new(7).coordinate();
        let placement = PlacementGenerationV1::new(7).coordinate();
        let source = SourceGenerationV1::new(7).coordinate();
        let graph = GraphServingGenerationV1::new(7).coordinate();

        assert_ne!(snapshot, placement);
        assert_ne!(snapshot, source);
        assert_ne!(source, graph);
        assert_eq!(snapshot.value, placement.value);
    }

    #[test]
    fn mmap_axes_preserve_snapshot_and_placement_independently() {
        let binding = StorageGenerationBindingV1 {
            node_count: 3,
            page_count: 1,
            placement_generation: 7,
            placement_scheme_digest: [0x22; 32],
        };
        let axes = MmapGenerationAxesV1::from_current_storage(41, &binding);
        assert_eq!(axes.snapshot, SnapshotGenerationV1::new(41));
        assert_eq!(axes.placement, PlacementGenerationV1::new(7));
        assert_ne!(axes.snapshot.coordinate(), axes.placement.coordinate());
    }

    #[test]
    fn transaction_axes_allow_equal_numbers_without_identity_alias() {
        let axes = TransactionGenerationAxesV1::new(
            SourceGenerationV1::new(11),
            GraphServingGenerationV1::new(11),
        );
        assert_eq!(axes.source.value(), axes.graph_serving.value());
        assert_ne!(axes.source.coordinate(), axes.graph_serving.coordinate());
    }

    #[test]
    fn explicit_domain_mismatch_fails_before_value_can_alias() {
        let expected = SnapshotGenerationV1::new(9).coordinate();
        let observed = PlacementGenerationV1::new(9).coordinate();
        assert_eq!(
            require_coordinate(expected, observed),
            Err(GenerationDomainErrorV1::DomainMismatch {
                expected: GenerationDomainV1::Snapshot,
                observed: GenerationDomainV1::Placement,
            })
        );
    }

    #[test]
    fn same_domain_value_mismatch_is_typed() {
        assert_eq!(
            require_graph_serving_generation(GraphServingGenerationV1::new(8), 9),
            Err(GenerationDomainErrorV1::ValueMismatch {
                domain: GenerationDomainV1::GraphServing,
                expected: 9,
                observed: 8,
            })
        );
    }
}
