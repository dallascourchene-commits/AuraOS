const s = process.argv[2];
if (!s || s.length !== 27 || !/^[012]+$/.test(s)) {
  throw new Error("expected exactly 27 ternary digits");
}
let n = 0n;
for (const c of s) n = n * 3n + BigInt(c);
let x = n;
let roundtrip = "";
for (let i = 0; i < 27; i++) {
  const r = x % 3n;
  roundtrip = String(r) + roundtrip;
  x /= 3n;
}
process.stdout.write(JSON.stringify({ decimal: n.toString(), roundtrip }));
