from __future__ import annotations

import unittest
from unittest.mock import patch

from tools import aura_external_discovery as d


class DiscoveryAdapterTests(unittest.TestCase):
    def test_google_scholar_is_not_scraped(self):
        with self.assertRaisesRegex(d.DiscoveryError, d.GOOGLE_SCHOLAR_BLOCK):
            d.discover("GOOGLE_SCHOLAR", "agent memory")

    @patch.object(d, "_json_get")
    def test_github_resolves_exact_commit(self, get):
        get.side_effect = [
            ({"items": [{
                "full_name": "o/r", "default_branch": "main", "html_url": "https://github.com/o/r",
                "description": "x", "language": "Python", "license": {"spdx_id": "MIT"},
                "topics": ["agents"], "archived": False, "fork": False, "stargazers_count": 10,
                "updated_at": "2026-08-31T16:00:00Z", "pushed_at": "2026-08-31T16:00:00Z"
            }]}, {}),
            ({"sha": "a"*40, "commit": {"committer": {"date": "2026-08-31T15:59:00Z"}}}, {"etag": '"e"'}),
        ]
        rows = d.discover_github("agents", limit=1)
        self.assertEqual(rows[0].provider_revision, "a"*40)
        self.assertTrue(rows[0].exact_source_uri.endswith("/tree/" + "a"*40))
        self.assertFalse(rows[0].code_execution_authorized)

    @patch.object(d, "_json_get")
    def test_hf_uses_exact_repo_sha_and_no_download_authority(self, get):
        get.return_value = ([{
            "id": "org/model", "sha": "b"*40, "lastModified": "2026-08-31T16:00:00Z",
            "tags": ["transformers"], "gated": False, "private": False, "disabled": False,
            "downloads": 1, "likes": 2, "securityStatus": {"status": "safe"}
        }], {})
        rows = d.discover_hugging_face("model", limit=1)
        self.assertEqual(rows[0].provider_revision, "b"*40)
        self.assertEqual(rows[0].revision_strength, "EXACT_REPO_SHA")
        self.assertFalse(rows[0].model_download_authorized)
        self.assertFalse(rows[0].remote_code_authorized)

    @patch.object(d, "_text_get")
    def test_arxiv_version_is_generation_identity(self, get):
        get.return_value = ("""<?xml version='1.0'?><feed xmlns='http://www.w3.org/2005/Atom'>
        <entry><id>https://arxiv.org/abs/2606.26511v2</id><updated>2026-06-26T01:00:00Z</updated>
        <published>2026-06-25T01:00:00Z</published><title>Temporal Memory</title><summary>Summary.</summary>
        <author><name>A</name></author><link rel='alternate' href='https://arxiv.org/abs/2606.26511v2'/></entry></feed>""", {})
        rows = d.discover_arxiv("temporal", limit=1)
        self.assertEqual(rows[0].canonical_id, "2606.26511v2")
        self.assertEqual(rows[0].revision_strength, "EXACT_VERSION_ID")

    @patch.object(d, "_json_get")
    def test_openalex_keeps_updated_timestamp(self, get):
        get.return_value = ({"results": [{
            "id": "https://openalex.org/W1", "title": "T", "updated_date": "2026-08-31T15:00:00Z",
            "publication_date": "2026-08-30", "created_date": "2026-08-30",
            "doi": "https://doi.org/10.1/x", "primary_location": {"landing_page_url": "https://example.org/x"},
            "type": "article", "open_access": {}, "primary_topic": {}, "authorships": []
        }]}, {})
        rows = d.discover_openalex("x", limit=1)
        self.assertEqual(rows[0].provider_revision, "2026-08-31T15:00:00Z")
        self.assertEqual(rows[0].revision_strength, "PROVIDER_UPDATED_TIMESTAMP")

    @patch.object(d, "_json_get")
    def test_semantic_scholar_marks_weak_native_revision(self, get):
        get.return_value = ({"data": [{
            "paperId": "P1", "title": "T", "url": "https://www.semanticscholar.org/paper/P1",
            "abstract": "a", "year": 2026, "externalIds": {}, "openAccessPdf": None,
            "publicationDate": "2026-08-30", "publicationTypes": ["JournalArticle"]
        }]}, {})
        rows = d.discover_semantic_scholar("x", limit=1)
        self.assertEqual(rows[0].revision_strength, "SYNTHETIC_METADATA_GENERATION_NO_NATIVE_UPDATED_AT")

    @patch.object(d, "_json_get")
    def test_crossref_keeps_index_generation(self, get):
        get.return_value = ({"message": {"items": [{
            "DOI": "10.1000/example", "title": ["Example"], "type": "journal-article",
            "publisher": "Example", "license": [], "relation": {},
            "indexed": {"date-time": "2026-08-31T16:00:00Z"},
            "deposited": {"date-time": "2026-08-31T15:00:00Z"},
            "URL": "https://doi.org/10.1000/example"
        }]}}, {})
        rows = d.discover_crossref("x", limit=1)
        self.assertEqual(rows[0].canonical_id, "10.1000/example")
        self.assertEqual(rows[0].revision_strength, "PROVIDER_INDEX_TIMESTAMP")
        self.assertFalse(rows[0].code_execution_authorized)


if __name__ == "__main__":
    unittest.main()
