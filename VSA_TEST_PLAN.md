# VSA/HDC Operations Test Plan
**Purpose:** Verify core polysynthetic compression and hyperdimensional computing operations work correctly

---

## Test Strategy

Since I'm in Plan mode (can only edit Markdown), I'll create a detailed test plan that can be executed in Code mode or manually.

---

## Test 1: Core VSA Operations (aura_core.py)

### Test 1.1: Polysynthetic Compression
**File:** `aura_core.py` - `SovereignEngine` class

**Test Code:**
```python
from aura_core import SovereignEngine

# Initialize engine
engine = SovereignEngine()

# Test 1: Intent to vector conversion
intent = "show me the topology"
vector = engine.continuous_tda_filtration(intent)

# Verify:
assert vector.shape == (10000,), f"Expected shape (10000,), got {vector.shape}"
assert vector.dtype == np.int8, f"Expected dtype int8, got {vector.dtype}"
assert set(vector) == {-1, 1}, f"Expected binary values {{-1, 1}}, got {set(vector)}"
print("✅ Test 1.1: Polysynthetic compression works")

# Test 2: Deterministic encoding (same input = same output)
vector2 = engine.continuous_tda_filtration(intent)
assert np.array_equal(vector, vector2), "Encoding should be deterministic"
print("✅ Test 1.2: Deterministic encoding verified")

# Test 3: Different inputs produce different vectors
vector3 = engine.continuous_tda_filtration("different command")
similarity = np.dot(vector, vector3) / 10000
assert similarity < 0.9, f"Different inputs too similar: {similarity}"
print("✅ Test 1.3: Different inputs produce distinct vectors")
```

**Expected Results:**
- Vector shape: (10000,)
- Vector dtype: int8
- Values: only -1 or 1
- Deterministic: same input → same output
- Distinct: different inputs → different vectors

---

## Test 2: Self-Organizing Map (VSOM)

### Test 2.1: Best Matching Unit
**File:** `aura_core.py` - `match_vsom()` method

**Test Code:**
```python
# Test VSOM matching
intent_vector = engine.continuous_tda_filtration("test command")
coordinate, similarity = engine.match_vsom(intent_vector)

# Verify:
assert isinstance(coordinate, tuple), "Coordinate should be tuple"
assert len(coordinate) == 2, "Coordinate should be (row, col)"
assert 0 <= coordinate[0] < 10, f"Row out of bounds: {coordinate[0]}"
assert 0 <= coordinate[1] < 10, f"Col out of bounds: {coordinate[1]}"
assert -10000 <= similarity <= 10000, f"Similarity out of range: {similarity}"
print(f"✅ Test 2.1: VSOM matching works - coordinate: {coordinate}, similarity: {similarity}")

# Test 2: Consistent mapping
coord2, sim2 = engine.match_vsom(intent_vector)
assert coordinate == coord2, "Same vector should map to same coordinate"
print("✅ Test 2.2: VSOM mapping is consistent")
```

**Expected Results:**
- Coordinate: (row, col) where 0 ≤ row, col < 10
- Similarity: integer in range [-10000, 10000]
- Consistency: same vector → same coordinate

---

## Test 3: Intent-to-Action Binding

### Test 3.1: FST Router
**File:** `aura_core.py` - `bind_intent_to_action()` method

**Test Code:**
```python
# Test intent binding
intent = "visualize critical friction"
action = "EXECUTE::AR_TETRAHEDRON_HOT_HI"
coordinate = engine.bind_intent_to_action(intent, action)

# Verify binding was stored
assert coordinate in engine.fst_router, "Coordinate not in FST router"
assert engine.fst_router[coordinate] == action, "Action not bound correctly"
print(f"✅ Test 3.1: Intent bound to action at coordinate {coordinate}")

# Test retrieval
vector = engine.continuous_tda_filtration(intent)
coord, _ = engine.match_vsom(vector)
retrieved_action = engine.fst_router.get(coord)
assert retrieved_action == action, f"Expected {action}, got {retrieved_action}"
print("✅ Test 3.2: Action retrieval works")
```

**Expected Results:**
- Binding creates entry in `fst_router` dict
- Retrieval returns correct action
- Coordinate is deterministic

---

## Test 4: Hyperdimensional Computing (aura_node.py)

### Test 4.1: HDC Core Operations
**File:** `aura_node.py` - `AuraHyperdimensionalCore` class (lines 911-1024)

**Test Code:**
```python
from aura_node import AuraHyperdimensionalCore
import numpy as np

# Initialize HDC core
hdc = AuraHyperdimensionalCore(dimensions=10000)

# Test 1: Binding (element-wise multiplication)
a = np.random.randn(10000) + 1j * np.random.randn(10000)
b = np.random.randn(10000) + 1j * np.random.randn(10000)
bound = hdc.bind(a, b)

assert bound.shape == (10000,), f"Bind shape mismatch: {bound.shape}"
assert bound.dtype == np.complex128, f"Bind dtype mismatch: {bound.dtype}"
print("✅ Test 4.1: HDC binding works")

# Test 2: Bundling (normalized sum)
vectors = [a, b]
bundled = hdc.bundle(vectors)

assert bundled.shape == (10000,), f"Bundle shape mismatch: {bundled.shape}"
assert np.isclose(np.linalg.norm(bundled), 1.0, atol=1e-6), "Bundle not normalized"
print("✅ Test 4.2: HDC bundling works")

# Test 3: Permutation (circular shift)
permuted = hdc.permute(a)

assert permuted.shape == a.shape, "Permute shape mismatch"
assert np.array_equal(permuted[1:], a[:-1]), "Permute not circular shift"
assert permuted[0] == a[-1], "Permute first element incorrect"
print("✅ Test 4.3: HDC permutation works")

# Test 4: Similarity (cosine)
similarity = hdc.similarity(a, a)
assert np.isclose(similarity, 1.0, atol=1e-6), f"Self-similarity should be 1.0, got {similarity}"

similarity_ab = hdc.similarity(a, b)
assert -1.0 <= similarity_ab <= 1.0, f"Similarity out of range: {similarity_ab}"
print(f"✅ Test 4.4: HDC similarity works (a·b = {similarity_ab:.4f})")
```

**Expected Results:**
- Binding: element-wise multiplication of complex vectors
- Bundling: normalized sum (norm = 1.0)
- Permutation: circular shift by 1
- Similarity: cosine similarity in [-1, 1]

---

## Test 5: Text Encoding

### Test 5.1: Encode Text to HDC Vector
**File:** `aura_node.py` - `encode_text()` method

**Test Code:**
```python
# Test text encoding
text = "Hello world"
encoded = hdc.encode_text(text)

assert encoded.shape == (10000,), f"Encoded shape mismatch: {encoded.shape}"
assert encoded.dtype == np.complex128, f"Encoded dtype mismatch: {encoded.dtype}"
print("✅ Test 5.1: Text encoding works")

# Test determinism
encoded2 = hdc.encode_text(text)
assert np.allclose(encoded, encoded2), "Text encoding not deterministic"
print("✅ Test 5.2: Text encoding is deterministic")

# Test different texts produce different vectors
encoded3 = hdc.encode_text("Different text")
similarity = hdc.similarity(encoded, encoded3)
assert similarity < 0.9, f"Different texts too similar: {similarity}"
print(f"✅ Test 5.3: Different texts produce distinct vectors (sim={similarity:.4f})")
```

**Expected Results:**
- Encoded vector: shape (10000,), dtype complex128
- Deterministic: same text → same vector
- Distinct: different texts → different vectors (similarity < 0.9)

---

## Test 6: Thermal Entropy Extraction

### Test 6.1: Device Entropy
**File:** `aura_node.py` - `extract_thermal_entropy()` method

**Test Code:**
```python
# Test thermal entropy extraction
temp_c = 42.5
entropy_vector = hdc.extract_thermal_entropy(temp_c)

assert entropy_vector.shape == (10000,), f"Entropy shape mismatch: {entropy_vector.shape}"
assert entropy_vector.dtype == np.complex128, f"Entropy dtype mismatch: {entropy_vector.dtype}"
print("✅ Test 6.1: Thermal entropy extraction works")

# Test different temperatures produce different vectors
entropy2 = hdc.extract_thermal_entropy(45.0)
similarity = hdc.similarity(entropy_vector, entropy2)
assert similarity < 0.99, f"Different temps too similar: {similarity}"
print(f"✅ Test 6.2: Different temperatures produce distinct entropy (sim={similarity:.4f})")
```

**Expected Results:**
- Entropy vector: shape (10000,), dtype complex128
- Temperature-dependent: different temps → different vectors

---

## Test 7: Performance Benchmarks

### Test 7.1: Intent Parsing Speed
**Claim:** <0.05ms per intent

**Test Code:**
```python
import time

# Benchmark intent parsing
intents = [
    "show topology",
    "execute command",
    "analyze data",
    "optimize system",
    "generate report"
]

times = []
for intent in intents:
    start = time.perf_counter()
    vector = engine.continuous_tda_filtration(intent)
    coord, sim = engine.match_vsom(vector)
    end = time.perf_counter()
    times.append((end - start) * 1000)  # Convert to ms

avg_time = np.mean(times)
max_time = np.max(times)

print(f"✅ Test 7.1: Intent parsing performance")
print(f"   Average: {avg_time:.4f}ms")
print(f"   Maximum: {max_time:.4f}ms")
print(f"   Target: <0.05ms")

if avg_time < 0.05:
    print("   ✅ PASSED: Meets performance target")
else:
    print(f"   ⚠️  WARNING: {avg_time/0.05:.1f}× slower than target")
```

**Expected Results:**
- Average time: <0.05ms (target)
- Consistent performance across different intents

---

## Test 8: Integration Test

### Test 8.1: End-to-End Polysynthetic Pipeline
**Test the complete flow: text → vector → VSOM → action**

**Test Code:**
```python
# Full pipeline test
def test_polysynthetic_pipeline():
    engine = SovereignEngine()
    
    # 1. Bind some intents
    bindings = {
        "show topology": "EXECUTE::TOPOLOGY_SCAN",
        "visualize friction": "EXECUTE::AR_TETRAHEDRON_HOT_HI",
        "clear display": "EXECUTE::WIPE_AR_DISPLAY",
    }
    
    for intent, action in bindings.items():
        engine.bind_intent_to_action(intent, action)
    
    # 2. Test retrieval
    for intent, expected_action in bindings.items():
        vector = engine.continuous_tda_filtration(intent)
        coord, similarity = engine.match_vsom(vector)
        retrieved_action = engine.fst_router.get(coord)
        
        assert retrieved_action == expected_action, \
            f"Intent '{intent}': expected {expected_action}, got {retrieved_action}"
        print(f"✅ '{intent}' → {coord} → {retrieved_action}")
    
    print("✅ Test 8.1: End-to-end pipeline works")

test_polysynthetic_pipeline()
```

**Expected Results:**
- All intents correctly map to their bound actions
- Retrieval is deterministic and accurate

---

## Test Execution Plan

### Option 1: Manual Testing (Current Mode - Plan)
1. Copy test code snippets into Python REPL
2. Run each test sequentially
3. Verify outputs match expected results

### Option 2: Automated Testing (Requires Code Mode)
1. Switch to Code mode
2. Create `test_vsa_operations.py` with all tests
3. Run: `python test_vsa_operations.py`
4. Review test results

### Option 3: Use Existing Test Suite
Run existing tests:
```bash
python test_aura_functions.py      # General function tests
python test_aura_substrate.py      # Substrate operations
python systems_check.py            # Boot smoke tests
```

---

## Expected Outcomes

### If All Tests Pass ✅
- VSA operations are working correctly
- Polysynthetic compression is functional
- HDC operations are mathematically sound
- Performance targets are met (or documented if not)

### If Tests Fail ⚠️
Document failures and recommend fixes:
1. **Shape mismatches** → Check dimension constants
2. **Type errors** → Verify numpy dtype handling
3. **Performance issues** → Profile bottlenecks
4. **Non-determinism** → Check random seed handling

---

## Next Steps

**Recommendation:** Switch to Code mode to implement and run these tests.

**Command to switch modes:**
```
/mode code
```

Then create `test_vsa_operations.py` and execute the test suite.

---

**Test Plan Created:** 2026-06-22  
**Status:** Ready for implementation in Code mode