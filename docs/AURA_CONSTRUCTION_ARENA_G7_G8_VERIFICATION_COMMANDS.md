# Construction Arena G7–G8 Verification Commands

```bash
python -m py_compile aura_construction_demo_director.py aura_spatial_cli.py
ruff check aura_construction_demo_director.py aura_spatial_cli.py tests/test_aura_construction_demo_director.py
ruff format --check aura_construction_demo_director.py aura_spatial_cli.py tests/test_aura_construction_demo_director.py
pytest -q tests/test_aura_construction_demo_director.py tests/test_aura_construction_demo_fixture.py tests/test_aura_construction_demo_projection.py tests/test_aura_spatial_render_plan.py
node --test tests/js/spatial-construction-demo.test.mjs tests/js/spatial-construction-review-regressions.test.mjs tests/js/spatial-gaussian-covariance.test.mjs
python aura_spatial_cli.py --repo-root . construction-video-demo --tour full --output /tmp/aura-construction-demo.packet.json
python -m aura_codemap_verify --compare-json .aura/CODEMAP.json
```
