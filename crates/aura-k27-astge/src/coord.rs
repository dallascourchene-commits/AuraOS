use core::fmt;

pub const K27_TRITS: usize = 27;
const K27_USED_BITS: usize = K27_TRITS * 2;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CoordinateError {
    InvalidTrit { index: usize, value: u8 },
    InvalidPackedTrit { index: usize },
    HighBitsSet,
    PrefixTooLong { len: usize },
}

impl fmt::Display for CoordinateError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidTrit { index, value } => {
                write!(f, "invalid trit {value} at index {index}")
            }
            Self::InvalidPackedTrit { index } => {
                write!(f, "packed coordinate contains reserved trit value at index {index}")
            }
            Self::HighBitsSet => write!(f, "packed coordinate uses bits above the 27-trit field"),
            Self::PrefixTooLong { len } => write!(f, "prefix length {len} exceeds {K27_TRITS}"),
        }
    }
}

impl std::error::Error for CoordinateError {}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Default)]
pub struct K27Coordinate {
    packed: u64,
}

impl K27Coordinate {
    pub fn from_trits(trits: [u8; K27_TRITS]) -> Result<Self, CoordinateError> {
        let mut packed = 0_u64;
        for (index, trit) in trits.into_iter().enumerate() {
            if trit > 2 {
                return Err(CoordinateError::InvalidTrit { index, value: trit });
            }
            packed |= u64::from(trit) << (index * 2);
        }
        Ok(Self { packed })
    }

    pub fn from_packed(packed: u64) -> Result<Self, CoordinateError> {
        if packed >> K27_USED_BITS != 0 {
            return Err(CoordinateError::HighBitsSet);
        }
        for index in 0..K27_TRITS {
            if ((packed >> (index * 2)) & 0b11) == 0b11 {
                return Err(CoordinateError::InvalidPackedTrit { index });
            }
        }
        Ok(Self { packed })
    }

    pub const fn packed(self) -> u64 {
        self.packed
    }

    pub fn get_trit(self, index: usize) -> Option<u8> {
        (index < K27_TRITS).then(|| ((self.packed >> (index * 2)) & 0b11) as u8)
    }

    pub fn trits(self) -> [u8; K27_TRITS] {
        let mut out = [0_u8; K27_TRITS];
        for (index, slot) in out.iter_mut().enumerate() {
            *slot = self.get_trit(index).expect("bounded K27 trit index");
        }
        out
    }

    pub fn matches_prefix(self, other: Self, len: usize) -> Result<bool, CoordinateError> {
        if len > K27_TRITS {
            return Err(CoordinateError::PrefixTooLong { len });
        }
        if len == 0 {
            return Ok(true);
        }
        let bits = len * 2;
        let mask = if bits == 64 {
            u64::MAX
        } else {
            (1_u64 << bits) - 1
        };
        Ok((self.packed & mask) == (other.packed & mask))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn trits_round_trip_exactly() {
        let mut trits = [0_u8; K27_TRITS];
        for (index, trit) in trits.iter_mut().enumerate() {
            *trit = (index % 3) as u8;
        }
        let coord = K27Coordinate::from_trits(trits).unwrap();
        assert_eq!(coord.trits(), trits);
        assert_eq!(K27Coordinate::from_packed(coord.packed()).unwrap(), coord);
    }

    #[test]
    fn reserved_trit_and_high_bits_fail_closed() {
        assert!(matches!(
            K27Coordinate::from_packed(0b11),
            Err(CoordinateError::InvalidPackedTrit { index: 0 })
        ));
        assert!(matches!(
            K27Coordinate::from_packed(1_u64 << K27_USED_BITS),
            Err(CoordinateError::HighBitsSet)
        ));
    }

    #[test]
    fn prefix_matching_is_bounded() {
        let zero = K27Coordinate::default();
        assert!(zero.matches_prefix(zero, 27).unwrap());
        assert!(matches!(
            zero.matches_prefix(zero, 28),
            Err(CoordinateError::PrefixTooLong { len: 28 })
        ));
    }
}
