# Arena Atomic Absorption Transaction — Point-of-Use Commit Fence

D0-only worker cell for ManyResearchers/OnePublisher convergence. `PublicationPlan` and `ResourcePublicationPlan` are transport records, not commit authority.

## Keeper laws

`Publish => ExactOwnerHeadCAS AND AtomicManifest AND ExactSemanticRedeliveryQuotient AND ProvenanceBoundManifest AND NoConflictingPathWrites AND NoStagingDebris AND AuthorityNonWidening`

`ConsequentialCommit => CanonicalReconstructionFromAuthoritativeInputs AND ExactSubmittedPlanIdentity AND ExactOwnerHeadCAS AND AuthorityNonWidening`

`PublishWithRuntimeResources => ConsequentialCommit AND ExactLeaseRegistryCAS AND CommitTimeLeaseLiveness AND ResourceModeCompatibility AND NoActiveLeaseConflict AND NoProposalResourceConflict`

Corollaries:
- a caller-constructed `READY` plan is never commit authority;
- the legacy commit call without authoritative planner inputs fails closed;
- commit reconstructs the canonical plan from the owner snapshot + proposals and rejects any submitted-plan drift in writes, manifest, disposition, authority flags, or other consequence-bearing fields;
- stale proposal => `REBASE_REQUIRED`, zero writes;
- owner-head movement after planning => zero writes;
- same consequence collapses only for exact semantic publication redelivery;
- same consequence + different receipt/write/resource binding => hold, never silent quotient;
- runtime resource planning binds the lease-registry root **and the plan evaluation time**;
- resource commit authenticates the submitted plan at its original evaluation time, CAS-checks owner + registry, then re-runs resource admission at the observed commit time;
- therefore `RegistryRootCurrent != LeaseCurrentAtCommit`: a lease can expire while registry bytes remain unchanged and must still yield zero writes;
- D0 only: no effect authority, Gate10, provider/model execution, OS lease mutation, merge, or deploy authority is granted.

## Reproducible proof on final local semantic bytes

Three deleted/recreated stdlib-only virtual environments, each executed under Python isolated mode (`-I`):

- 74 focused tests/environment = **222/222 PASS**;
- legacy transaction campaign: 100,000 cases/environment, stable root `442fe17be49d64756f6f69d24fad6ba00b305a554482f0293546331345ced3ee`;
- R2 semantic + commit-fence campaign: 100,000 cases + HS1000/environment, stable root `fcc342b97e623aabedbbb27cc24f3da03f6e66a4e97dd02e00f441f66d0166c0`;
- resource/lease campaign: 100,000 cases + HS1000/environment, stable root `be06d65835fd4485aa7fbba6c2acc9838aef835ab0054a40360b41ae6dcbcdf6`;
- aggregate randomized/classification cases across the three environments: **900,000**;
- aggregate HS1000 consequence-boundary challenges: **9,000**;
- forged-plan escapes: **0**;
- unauthenticated legacy-commit escapes: **0**;
- owner-head CAS escapes: **0**;
- lease-registry CAS escapes: **0**;
- commit-time lease-expiry escapes with unchanged registry root: **0**;
- Omega8: exactly **1/6561** keeper in every campaign;
- 13D: **0/243** trailing-context repairs of a hard-invalid core.

Final local SHA-256:

- `atomic_absorption.py` `7c4e127efd8d08dca0ee90cccfa51528783acb5d681b9f0034091e95116d5c23`
- `resource_absorption.py` `88769c9e5a77b3fb74e619285669c9199606078b704d600dd0b54892ef2c9ef4`
- `test_atomic_absorption.py` `e30496afb84502c2bfac4e4e617ab4d3e0f033875bbb4cf0107c8a665c79c682`
- `test_atomic_absorption_r2.py` `add4a399295dbb3b4c18e4f39b24c5e86be6d1d352b90c09935765919e6159e9`
- `test_resource_absorption.py` `06ed99114a52d609bcb691770023e7b1d1a491b576b1fe71f1af617ae1ae4dad`
- `campaign.py` `83c06351ef499cb6f6d0a5c8bee08d4b9576379a7d2f289b6740e6300562a5d7`
- `campaign_r2.py` `f3c573b462442413fdba614ec2d11f0f31822726b8de4cdd19a3ef2adcc37213`
- `campaign_resource_absorption.py` `72fea24840cfd825259a5733095b73e06b2c1bdf2f752db4617a8689b995ff01`

Commands from the worker-cell directory:

```bash
python -m unittest discover -s . -p 'test_*.py' -v
python -I campaign.py
python -I campaign_r2.py
python -I campaign_resource_absorption.py
```

Inherited-coverage check: the final suite retains the prior resource conflict/future-release/release-before-issue regressions in addition to the new commit-fence cases.

Failed-first scar: the first isolated-mode campaign attempt could not import its sibling module because `-I` removes the script directory from `sys.path`. That run receives zero proof credit. The final campaigns self-locate before imports and the complete proof was rerun from freshly recreated environments.
