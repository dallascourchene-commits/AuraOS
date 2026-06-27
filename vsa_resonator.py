"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8c5-[Q-SYS:D4FAE19AB3EF864B]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit)
DEPENDENCIES: numpy
FUNCTIONS: __init__, bind, bundle, gsb_quantize, sampled_similarity, encode_hit_interaction, decode_hit_member, resonate
SYNOPSIS: This Python module provides high-performance numerical processing and quantum-inspired similarity computation via NumPy, featuring initialization, dynamic binding, data bundling, quantization, sampled similarity analysis, and hit interaction encoding/decoding with resonance-based signal amplification.
[/AURA_MASTER_KEY]
"""
# [AURA OPTIMIZED] - Bloat removed.

import hashlib

import numpy as np


class VSAResonator:
    def __init__(self, dim=10000, sample_ratio=0.05):
        """
        Initialize a VSAResonator instance with specified dimensionality and sampling configuration.

        Precomputes deterministic sampling indices for efficient sampled similarity evaluation
        and initializes internal state.

        Parameters:
        	dim (int): Vector dimensionality. Default is 10000.
        	sample_ratio (float): Fraction of coordinates to sample for similarity evaluation (0 to 1). Default is 0.05.
        """
        self.dim = dim
        self.sample_ratio = sample_ratio
        self.sample_size = int(self.dim * self.sample_ratio)  # 5% target: 500 coordinates

        # Pre-allocate a deterministic sampling mask to prevent runtime generator overhead
        rng = np.random.default_rng(seed=0x53E6E)
        self._sampling_indices = rng.choice(self.dim, size=self.sample_size, replace=False)

        # Codebooks are quantized once inside resonate(). Caching arbitrary
        # temporary arrays by id is unsafe because NumPy object ids are reused.
        self._gsb_cache = {}

    def bind(self, v1, v2):
        """
        Bind two vectors in bipolar Vector Symbolic Architecture.

        Returns:
            np.ndarray: The bound vector.
        """
        return np.multiply(v1, v2)

    def bundle(self, vectors):
        """
        Combine multiple vectors into a single bundled vector through element-wise addition and sign thresholding.

        Parameters:
        	vectors (array-like): A sequence of vectors to bundle together.

        Returns:
        	np.ndarray: A bipolar vector where each element is -1 or 1.
        """
        summed = np.sum(vectors, axis=0)
        summed[summed == 0] = 1
        return np.sign(summed)

    def gsb_quantize(self, vector_10k: np.ndarray) -> tuple:
        """
        Decompose a vector into gain, shape, and bias components.

        For complex inputs, extracts the phase angle before decomposition.

        Returns:
        	A tuple of (gain, shape, bias) where gain is the standard deviation of the
        	centered vector with a minimum of 1.0, shape is an int8 array of the signs
        	of centered values (with zeros replaced by 1), and bias is the mean.
        """
        if np.iscomplexobj(vector_10k):
            vector_10k = np.angle(vector_10k).astype(np.float32)
        bias = float(np.mean(vector_10k))
        centered = vector_10k - bias
        gain = float(np.std(centered))
        if gain == 0:
            gain = 1.0
        shape = np.sign(centered).astype(np.int8)
        shape[shape == 0] = 1

        return gain, shape, bias

    def sampled_similarity(self, q_gain: float, q_shape: np.ndarray, q_bias: float,
                           c_gain: float, c_shape: np.ndarray, c_bias: float) -> float:
        """
                           Compute similarity between two GSB-quantized vectors using sampled coordinates.

                           Parameters:
                               q_gain (float): Gain component of the query vector
                               q_shape (np.ndarray): Shape component of the query vector
                               q_bias (float): Bias component of the query vector
                               c_gain (float): Gain component of the candidate vector
                               c_shape (np.ndarray): Shape component of the candidate vector
                               c_bias (float): Bias component of the candidate vector

                           Returns:
                               float: Similarity score combining shape alignment with gain and bias adjustments
                           """
        # Zero-copy slice read directly over the pre-allocated L2-cache sampling mask
        q_slice = np.real(q_shape[self._sampling_indices])
        c_slice = np.real(c_shape[self._sampling_indices])

        # Accumulate outside int8. NumPy's int8 dot wraps at 127, which made
        # identical 10,000-D vectors appear almost orthogonal.
        dot_product = np.dot(
            q_slice.astype(np.float32, copy=False),
            c_slice.astype(np.float32, copy=False),
        )

        # Scale and rehydrate with continuous physical gain and bias
        normalized_sim = float(dot_product) / self.sample_size
        return (q_gain * c_gain * normalized_sim) + (q_bias * c_bias)

    def encode_hit_interaction(self, node_vectors: list) -> np.ndarray:
        """
        Encode an N-way node interaction sequence into a single holographic vector.

        Each node vector is position-shifted and bound cumulatively into the result.
        An empty sequence returns a vector of ones.

        Returns:
            np.ndarray: The bound interaction vector with dtype int8.
        """
        if not node_vectors:
            return np.ones(self.dim, dtype=np.int8)

        bound_interaction = np.ones(self.dim, dtype=np.int8)
        for idx, vec in enumerate(node_vectors):
            permuted_vec = np.roll(vec, shift=idx + 1)
            bound_interaction = np.multiply(bound_interaction, permuted_vec)

        return bound_interaction

    def decode_hit_member(self, hit_vector: np.ndarray, index_to_extract: int, known_vectors: list) -> int:
        """
        Identify which vector from a known set best matches the member at a specified position in an encoded interaction.

        Parameters:
            hit_vector (np.ndarray): An encoded N-way interaction vector.
            index_to_extract (int): The position in the original sequence to decode.
            known_vectors (list): Reference vectors to match against.

        Returns:
            int: The index of the best-matching vector from known_vectors.
        """
        unbound_state = np.copy(hit_vector)
        for idx, vec in enumerate(known_vectors):
            if idx != index_to_extract:
                permuted_vec = np.roll(vec, shift=idx + 1)
                unbound_state = np.multiply(unbound_state, permuted_vec)

        extracted_vector = np.roll(unbound_state, shift=-(index_to_extract + 1))
        eg, es, eb = self.gsb_quantize(extracted_vector)

        best_idx = 0
        best_sim = -float('inf')
        for idx, v in enumerate(known_vectors):
            cg, cs, cb = self.gsb_quantize(v)
            sim = self.sampled_similarity(eg, es, eb, cg, cs, cb)
            if sim > best_sim:
                best_sim = sim
                best_idx = idx
        return best_idx

    @staticmethod
    def _bipolar_digest(vector: np.ndarray) -> bytes:
        """
        Hash a bipolar vector into a compact digest for dictionary lookups.

        Returns:
            bytes: A 16-byte blake2b digest of the vector's bipolar encoding.
        """
        packed = np.packbits(np.asarray(vector).reshape(-1) > 0, bitorder="little")
        return hashlib.blake2b(packed.tobytes(), digest_size=16).digest()

    def _exact_bipolar_factorization(self, composite_vector, book_a, book_b):
        """
        Find factor indices whose product equals the composite vector.

        Parameters:
            composite_vector: Vector to factorize.
            book_a: First codebook.
            book_b: Second codebook.

        Returns:
            (index_a, index_b) if book_a[index_a] * book_b[index_b] equals
            composite_vector, None otherwise.
        """
        if not book_a or not book_b:
            return None
        composite = np.asarray(composite_vector)
        if not np.all(np.isin(composite, (-1, 1))):
            return None
        lookup_a = {
            self._bipolar_digest(vector): index
            for index, vector in enumerate(book_a)
        }
        for index_b, vector_b in enumerate(book_b):
            candidate_a = np.multiply(composite, vector_b)
            index_a = lookup_a.get(self._bipolar_digest(candidate_a))
            if index_a is not None and np.array_equal(
                np.multiply(book_a[index_a], vector_b),
                composite,
            ):
                return index_a, index_b
        return None

    def resonate(self, composite_vector, book_a, book_b, max_iters=10):
        """
        Factorize the composite vector by identifying the factors from two codebooks that reconstruct it.

        Returns:
            Tuple of (index_a, index_b) from book_a and book_b respectively that best reconstruct the composite vector.
        """
        exact = self._exact_bipolar_factorization(composite_vector, book_a, book_b)
        if exact is not None:
            return exact

        est_a = self.bundle(book_a)
        est_b = self.bundle(book_b)

        # Pre-quantize and cache the codebooks using the high-speed O(1) lookup
        quantized_a = [self.gsb_quantize(v) for v in book_a]
        quantized_b = [self.gsb_quantize(v) for v in book_b]

        best_idx_a = 0
        best_idx_b = 0

        for i in range(max_iters):
            guess_a = self.bind(composite_vector, est_b)
            geg, ges, geb = self.gsb_quantize(guess_a)

            # Fast, sampled similarity scan over Codebook A
            best_idx_a = 0
            best_sim_a = -float('inf')
            for idx, (cg, cs, cb) in enumerate(quantized_a):
                sim = self.sampled_similarity(geg, ges, geb, cg, cs, cb)
                if sim > best_sim_a:
                    best_sim_a = sim
                    best_idx_a = idx
            est_a = book_a[best_idx_a]

            guess_b = self.bind(composite_vector, est_a)
            geg_b, ges_b, geb_b = self.gsb_quantize(guess_b)

            # Fast, sampled similarity scan over Codebook B
            best_idx_b = 0
            best_sim_b = -float('inf')
            for idx, (cg, cs, cb) in enumerate(quantized_b):
                sim = self.sampled_similarity(geg_b, ges_b, geb_b, cg, cs, cb)
                if sim > best_sim_b:
                    best_sim_b = sim
                    best_idx_b = idx
            est_b = book_b[best_idx_b]

            if best_sim_a > 0.95 and best_sim_b > 0.95:
                return best_idx_a, best_idx_b

        return best_idx_a, best_idx_b
