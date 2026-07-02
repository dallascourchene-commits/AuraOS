import json
import pytest
from pathlib import Path
import tempfile
import asyncio

from aura_research_manifest import ResearchPaperEntry, ResearchManifest, load_research_manifest, ingest_research_manifest

def test_manifest_dataclasses():
    entry = ResearchPaperEntry(
        arxiv_id="2407.01489",
        label="Agentless",
        target_modules=["aura_repo_localizer.py"],
        implementation_lesson="Deterministic localize-first",
        acceptance_test="Council fails → localizer returns <=5 files",
        future_ingest=True,
        priority=1
    )
    d = entry.to_dict()
    assert d["arxiv_id"] == "2407.01489"
    assert d["label"] == "Agentless"
    assert "aura_repo_localizer.py" in d["target_modules"]
    
    re_entry = ResearchPaperEntry.from_dict(d)
    assert re_entry.arxiv_id == entry.arxiv_id
    assert re_entry.label == entry.label

def test_load_manifest():
    temp_dir = tempfile.TemporaryDirectory()
    manifest_file = Path(temp_dir.name) / "test_manifest.json"
    
    manifest_data = {
        "manifest_version": "1.0",
        "created_for": "Unit Test",
        "papers": [
            {
                "arxiv_id": "2407.01489",
                "label": "Agentless",
                "target_modules": ["aura_repo_localizer.py"],
                "implementation_lesson": "Deterministic localize-first",
                "acceptance_test": "Council fails → localizer returns <=5 files",
                "future_ingest": True,
                "priority": 1
            }
        ]
    }
    
    manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")
    
    manifest = load_research_manifest(manifest_file)
    assert manifest is not None
    assert manifest.manifest_version == "1.0"
    assert manifest.created_for == "Unit Test"
    assert len(manifest.papers) == 1
    assert manifest.papers[0].arxiv_id == "2407.01489"
    
    temp_dir.cleanup()

@pytest.mark.anyio
async def test_ingest_research_manifest_mock(monkeypatch):
    class MockNode:
        def __init__(self):
            class MockMemoryPalace:
                def __init__(self):
                    self.conn = None
            self.memory_palace = MockMemoryPalace()

    called_arxiv_ids = []
    
    async def mock_ingest_arxiv_ids(self, arxiv_ids):
        called_arxiv_ids.extend(arxiv_ids)
        return {"status": "success", "count": len(arxiv_ids), "ingested": arxiv_ids, "failed": []}

    from arxiv_forager import ArXivForager
    monkeypatch.setattr(ArXivForager, "ingest_arxiv_ids", mock_ingest_arxiv_ids)
    
    temp_dir = tempfile.TemporaryDirectory()
    manifest_file = Path(temp_dir.name) / "test_manifest.json"
    
    manifest_data = {
        "manifest_version": "1.0",
        "created_for": "Unit Test",
        "papers": [
            {
                "arxiv_id": "2407.01489",
                "label": "Agentless",
                "target_modules": ["aura_repo_localizer.py"],
                "implementation_lesson": "Deterministic localize-first",
                "acceptance_test": "Council fails → localizer returns <=5 files",
                "future_ingest": True,
                "priority": 1
            },
            {
                "arxiv_id": "2404.05427",
                "label": "AutoCodeRover",
                "target_modules": ["aura_repo_localizer.py"],
                "implementation_lesson": "AST/program-structure search + fault localization.",
                "acceptance_test": "Localizer uses AST parser",
                "future_ingest": False, # Should be skipped
                "priority": 2
            }
        ]
    }
    
    manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")
    
    node = MockNode()
    result = await ingest_research_manifest(manifest_file, node_ref=node)
    
    assert result["status"] == "success"
    assert "2407.01489" in called_arxiv_ids
    assert "2404.05427" not in called_arxiv_ids
    assert len(called_arxiv_ids) == 1
    
    temp_dir.cleanup()
