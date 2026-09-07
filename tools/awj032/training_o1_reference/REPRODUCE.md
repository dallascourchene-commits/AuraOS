# Exact-source reproduction

From an isolated checkout of this branch:

```bash
git clone https://github.com/lyogavin/airllm.git .awj032_airllm_upstream_fixture
git -C .awj032_airllm_upstream_fixture checkout 55e435087d951da8c25ab3672e969025241a398e
python3 -m venv /tmp/awj032-o1-venv
cd tools/awj032/training_o1_reference
/tmp/awj032-o1-venv/bin/python -m unittest -q test_training_admission
```

Expected source roots:

- `air_llm/airllm/airllm_lora.py`: `442c70a85a53603089ce14604bdc48550e343e3b3405dccc080a4d841bc50172`
- `air_llm/airllm/lora_linear.py`: `acda13718742c7f79c2713b04d06787c81999a85d6792aa1fa836ab77e1745f5`
- `README.md`: `746f35e0bee6598643666792c050c8833b5d441d36e0a60dd0846ae0d34ece73`

Do not substitute a newer upstream commit while claiming this receipt; source movement is a re-audit/rebind trigger.
