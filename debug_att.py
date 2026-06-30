"""Debug: check what the ATT transducer actually produces in both directions."""
from pathlib import Path

att = Path("ojibwemorph_fst/ojibwe.att")
# Show the first 30 transitions starting from state 0
# and look for 'n' and 'b' transitions (first chars of our words)
with open(att, encoding="utf-8") as f:
    count = 0
    for line in f:
        parts = line.rstrip("\n").split("\t")
        if len(parts) >= 4:
            src, dst, inp, out = parts[0], parts[1], parts[2], parts[3]
            # Show transitions from state 0
            if src == "0" and count < 40:
                print(f"  State0: {inp!r} -> state{dst}, output={out!r}")
                count += 1
    print(f"...showed {count} state-0 transitions")

# Also look for any transition involving 'nibaa' style chars near the end
# Check what final states look like
print("\nSample final states (last 20 lines of file):")
with open(att, encoding="utf-8") as f:
    all_lines = f.readlines()
for line in all_lines[-20:]:
    print(f"  {line.rstrip()}")
