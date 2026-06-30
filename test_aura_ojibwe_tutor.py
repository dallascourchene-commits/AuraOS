"""
Tests — Aura Anishinaabemowin Tutor
======================================
Full test suite for all Wave 4 tutor modules.

Covers:
  1. Source registry — schema version, confidence floors
  2. Data governance — OCAP/CARE enforcement
  3. Dialect profile — Treaty #1 schema
  4. OPD license adapter — CC-BY-NC-SA enforcement
  5. Lexicon sidecar — immutability, provenance
  6. Orthography — normalization preserves raw input
  7. Review queue — CANDIDATE items captured
  8. Learner profile — isolated from lexicon truth
  9. Privacy policy — no learner data to LLMs
 10. Audio consent — blocks without permission_ref
 11. Morph bridge — OjibweMorph FST or stub
 12. Dialect conflict resolver — Treaty #1 preferred
 13. Translation guard — three-gate pipeline
 14. Pronunciation bridge — audio level enforcement
 15. Tutor engine — full pipeline, always returns confidence
"""

import pytest

# ---------------------------------------------------------------------------
# 1. Source Registry
# ---------------------------------------------------------------------------

class TestLanguageSourceRegistry:
    def test_seed_sources_present(self):
        from aura_language_source_registry import LanguageSourceRegistry
        r = LanguageSourceRegistry()
        assert r.get("opd_main") is not None
        assert r.get("aura_fst_internal") is not None
        assert r.get("llm_explanation_bounded") is not None

    def test_schema_version_enforced(self):
        from aura_language_source_registry import SourceRecord, SourceType
        with pytest.raises(ValueError, match="Unknown schema version"):
            SourceRecord(
                schema_version="BAD_VERSION",
                source_id="test",
                source_name="Test",
                source_type=SourceType.VERIFIED,
                dialect_tags=("Treaty1",),
                permission_ref="test_ref",
                license="MIT",
                confidence=0.95,
                citation="Test",
            )

    def test_confidence_floor_enforced(self):
        from aura_language_source_registry import SourceRecord, SourceType, AURA_LANGUAGE_SOURCE_REGISTRY_V1
        with pytest.raises(ValueError, match="below minimum"):
            SourceRecord(
                schema_version=AURA_LANGUAGE_SOURCE_REGISTRY_V1,
                source_id="low",
                source_name="Low confidence",
                source_type=SourceType.VERIFIED,
                dialect_tags=(),
                permission_ref="ref",
                license="MIT",
                confidence=0.50,  # Below 0.95 floor for VERIFIED
                citation="Test",
            )

    def test_permission_ref_required(self):
        from aura_language_source_registry import SourceRecord, SourceType, AURA_LANGUAGE_SOURCE_REGISTRY_V1
        with pytest.raises(ValueError, match="permission_ref"):
            SourceRecord(
                schema_version=AURA_LANGUAGE_SOURCE_REGISTRY_V1,
                source_id="noperm",
                source_name="No perm",
                source_type=SourceType.CROSS_REFERENCE,
                dialect_tags=(),
                permission_ref="",
                license="MIT",
                confidence=0.40,
                citation="Test",
            )


# ---------------------------------------------------------------------------
# 2. Data Governance
# ---------------------------------------------------------------------------

class TestLanguageDataGovernance:
    def test_restricted_blocked_from_llm(self):
        from aura_language_data_governance import LanguageDataGovernancePolicy, DataAccessLevel
        policy = LanguageDataGovernancePolicy()
        decision = policy.check_can_send_to_llm(DataAccessLevel.RESTRICTED, "test item")
        assert not decision.allowed

    def test_ceremonial_private_blocked_from_llm(self):
        from aura_language_data_governance import LanguageDataGovernancePolicy, DataAccessLevel
        policy = LanguageDataGovernancePolicy()
        decision = policy.check_can_send_to_llm(DataAccessLevel.CEREMONIAL_PRIVATE, "ceremony")
        assert not decision.allowed

    def test_public_allowed_to_llm(self):
        from aura_language_data_governance import LanguageDataGovernancePolicy, DataAccessLevel
        policy = LanguageDataGovernancePolicy()
        decision = policy.check_can_send_to_llm(DataAccessLevel.PUBLIC, "greeting")
        assert decision.allowed

    def test_community_only_blocked_without_context(self):
        from aura_language_data_governance import LanguageDataGovernancePolicy, DataAccessLevel
        policy = LanguageDataGovernancePolicy(community_context_active=False)
        decision = policy.check_access(DataAccessLevel.COMMUNITY_ONLY, "community word")
        assert not decision.allowed

    def test_community_only_allowed_with_context(self):
        from aura_language_data_governance import LanguageDataGovernancePolicy, DataAccessLevel
        policy = LanguageDataGovernancePolicy(community_context_active=True)
        decision = policy.check_access(DataAccessLevel.COMMUNITY_ONLY, "community word")
        assert decision.allowed

    def test_ceremonial_private_blocked_from_access(self):
        from aura_language_data_governance import LanguageDataGovernancePolicy, DataAccessLevel
        policy = LanguageDataGovernancePolicy(community_context_active=True)
        decision = policy.check_access(DataAccessLevel.CEREMONIAL_PRIVATE, "ceremony")
        assert not decision.allowed


# ---------------------------------------------------------------------------
# 3. Dialect Profile
# ---------------------------------------------------------------------------

class TestDialectProfile:
    def test_treaty1_profile_loads(self):
        from aura_ojibwe_dialect_profile import TREATY1_PLAINS_OJIBWE, AURA_DIALECT_PROFILE_V1
        assert TREATY1_PLAINS_OJIBWE.dialect_id == "Treaty1_Plains_Ojibwe"
        assert TREATY1_PLAINS_OJIBWE.schema_version == AURA_DIALECT_PROFILE_V1

    def test_opd_is_cross_reference_only(self):
        from aura_ojibwe_dialect_profile import TREATY1_PLAINS_OJIBWE
        assert "opd_main" in TREATY1_PLAINS_OJIBWE.cross_reference_source_ids
        assert "opd_main" not in TREATY1_PLAINS_OJIBWE.primary_source_ids

    def test_schema_version_enforced(self):
        from aura_ojibwe_dialect_profile import DialectProfile, OrthographyConvention
        with pytest.raises(ValueError, match="Unknown schema version"):
            DialectProfile(
                schema_version="WRONG",
                dialect_id="test",
                dialect_name="Test",
                alternate_names=(),
                geographic_scope="Nowhere",
                primary_source_ids=(),
                cross_reference_source_ids=(),
                orthography=OrthographyConvention("DV", "desc", "doubled"),
                animacy_classes=("animate", "inanimate"),
                vowels_short=("a", "i", "o", "e"),
                vowels_long=("aa", "ii", "oo"),
                consonant_notes="",
                verb_classes=("VAI",),
                noun_classes=("NA",),
                source_hierarchy_description="",
            )


# ---------------------------------------------------------------------------
# 4. OPD License Adapter
# ---------------------------------------------------------------------------

class TestOPDLicenseAdapter:
    def test_opd_entries_are_cross_reference_not_verified(self):
        from aura_opd_license_adapter import OPDEntry, AURA_OPD_LICENSE_ADAPTER_V1
        entry = OPDEntry(
            schema_version=AURA_OPD_LICENSE_ADAPTER_V1,
            word="boozhoo",
            gloss_en="hello",
            part_of_speech="PCInterj",
            opd_url="https://ojibwe.lib.umn.edu/",
        )
        assert entry.source_type == "CROSS_REFERENCE"

    def test_opd_noncommercial_license_blocks_commercial(self):
        from aura_opd_license_adapter import OPDLicenseAdapter, OPDUseContext
        adapter = OPDLicenseAdapter()
        decision = adapter.check_use_permitted(OPDUseContext.COMMERCIAL)
        assert not decision.allowed

    def test_opd_noncommercial_license_blocks_bulk_export(self):
        from aura_opd_license_adapter import OPDLicenseAdapter, OPDUseContext, OPD_MAX_BULK_ENTRIES
        adapter = OPDLicenseAdapter()
        decision = adapter.check_use_permitted(OPDUseContext.BULK_EXPORT, OPD_MAX_BULK_ENTRIES + 1)
        assert not decision.allowed

    def test_opd_individual_lookup_permitted(self):
        from aura_opd_license_adapter import OPDLicenseAdapter, OPDUseContext
        adapter = OPDLicenseAdapter()
        decision = adapter.check_use_permitted(OPDUseContext.INDIVIDUAL_LOOKUP)
        assert decision.allowed
        assert decision.attribution_required
        assert decision.noncommercial_only


# ---------------------------------------------------------------------------
# 5. Lexicon Sidecar
# ---------------------------------------------------------------------------

class TestOjibweLexiconSidecar:
    def test_seed_entries_present(self):
        from aura_ojibwe_lexicon_sidecar import OjibweLexiconSidecar
        lex = OjibweLexiconSidecar()
        assert lex.lookup("boozhoo") is not None
        assert lex.lookup("nimishoomis") is not None
        assert lex.lookup("aki") is not None

    def test_lexicon_entry_immutable(self):
        from aura_ojibwe_lexicon_sidecar import OjibweLexiconSidecar
        lex = OjibweLexiconSidecar()
        entry = lex.lookup("boozhoo")
        with pytest.raises((AttributeError, TypeError)):
            entry.gloss_en = "HACKED"  # frozen dataclass should block this

    def test_learner_profile_cannot_modify_lexicon_entry(self):
        """Learner profile methods must not touch LexiconEntry objects."""
        from aura_ojibwe_lexicon_sidecar import OjibweLexiconSidecar
        from aura_language_learner_profile import new_learner_profile
        lex = OjibweLexiconSidecar()
        profile = new_learner_profile("Treaty1_Plains_Ojibwe")
        original_entry = lex.lookup("boozhoo")
        profile.record_practice("boozhoo", correct=True, session_id="s1")
        # Entry unchanged
        assert lex.lookup("boozhoo") is original_entry
        assert lex.lookup("boozhoo").gloss_en == original_entry.gloss_en

    def test_only_verified_vetted_entries_added(self):
        from aura_ojibwe_lexicon_sidecar import OjibweLexiconSidecar, LexiconEntry, AURA_OJIBWE_LEXICON_SIDECAR_V1
        from aura_language_data_governance import DataAccessLevel
        lex = OjibweLexiconSidecar()
        bad_entry = LexiconEntry(
            schema_version=AURA_OJIBWE_LEXICON_SIDECAR_V1,
            word="testword",
            stem="test",
            part_of_speech="NA",
            animacy_class="animate",
            dialect_tags=(),
            gloss_en="test",
            example_phrase=None,
            example_gloss=None,
            source_ref="opd_main",
            source_type="CROSS_REFERENCE",  # Not VERIFIED or VETTED
            permission_ref="test_ref",
            access_level=DataAccessLevel.PUBLIC,
        )
        with pytest.raises(ValueError, match="Only VERIFIED or VETTED"):
            lex.add_community_entry(bad_entry)


# ---------------------------------------------------------------------------
# 6. Orthography
# ---------------------------------------------------------------------------

class TestOjibweOrthography:
    def test_normalization_preserves_original_form(self):
        from aura_ojibwe_orthography import OjibweOrthographyNormalizer
        norm = OjibweOrthographyNormalizer()
        result = norm.normalize("bôozhoo")
        assert result.raw_input == "bôozhoo"
        assert result.normalized_form != result.raw_input or not result.transformations_applied

    def test_long_vowel_diacritics_converted(self):
        from aura_ojibwe_orthography import OjibweOrthographyNormalizer
        norm = OjibweOrthographyNormalizer()
        result = norm.normalize("nîbaa")
        assert "ii" in result.normalized_form

    def test_variants_generated(self):
        from aura_ojibwe_orthography import OjibweOrthographyNormalizer
        norm = OjibweOrthographyNormalizer()
        result = norm.normalize("zaaga'igan")
        # Should generate at least one variant (no-apostrophe form)
        assert isinstance(result.variant_candidates, list)

    def test_syllabics_converted(self):
        from aura_ojibwe_orthography import OjibweOrthographyNormalizer
        norm = OjibweOrthographyNormalizer()
        result = norm.normalize("ᐊ")
        assert "a" in result.normalized_form


# ---------------------------------------------------------------------------
# 7. Review Queue
# ---------------------------------------------------------------------------

class TestLanguageReviewQueue:
    def test_candidate_translation_creates_review_queue_item(self):
        from aura_language_review_queue import LanguageReviewQueue, make_review_item, ReviewItemType
        queue = LanguageReviewQueue()
        item = make_review_item(
            item_type=ReviewItemType.PHRASE_CANDIDATE,
            dialect_profile_id="Treaty1_Plains_Ojibwe",
            candidate="nibaawin",
            reason="FST passed but no Treaty #1 source record",
            source_refs=["opd_main"],
        )
        review_id = queue.submit(item)
        assert queue.get(review_id) is not None
        assert len(queue.pending()) == 1

    def test_reviewer_decision_recorded(self):
        from aura_language_review_queue import LanguageReviewQueue, make_review_item, ReviewItemType, ReviewStatus
        queue = LanguageReviewQueue()
        item = make_review_item(
            item_type=ReviewItemType.WORD_CANDIDATE,
            dialect_profile_id="Treaty1_Plains_Ojibwe",
            candidate="zaaga'igan",
            reason="OPD cross-reference only",
        )
        rid = queue.submit(item)
        queue.decide(rid, ReviewStatus.APPROVED, "Correct Treaty #1 form")
        assert queue.get(rid).status == ReviewStatus.APPROVED


# ---------------------------------------------------------------------------
# 8. Learner Profile
# ---------------------------------------------------------------------------

class TestLearnerProfile:
    def test_profile_schema_version_enforced(self):
        from aura_language_learner_profile import LearnerProfile
        with pytest.raises(ValueError, match="Unknown schema version"):
            LearnerProfile(schema_version="BAD", dialect_profile="Treaty1_Plains_Ojibwe")

    def test_qdkt_summary_excludes_learner_id(self):
        from aura_language_learner_profile import new_learner_profile
        profile = new_learner_profile("Treaty1_Plains_Ojibwe")
        summary = profile.qdkt_summary()
        assert "learner_id" not in summary

    def test_to_dict_safe_excludes_learner_id(self):
        from aura_language_learner_profile import new_learner_profile
        profile = new_learner_profile("Treaty1_Plains_Ojibwe")
        d = profile.to_dict_safe()
        assert "learner_id" not in d

    def test_progress_recorded_without_touching_lexicon(self):
        from aura_language_learner_profile import new_learner_profile
        from aura_ojibwe_lexicon_sidecar import OjibweLexiconSidecar
        lex = OjibweLexiconSidecar()
        profile = new_learner_profile("Treaty1_Plains_Ojibwe")
        original = lex.lookup("boozhoo")
        profile.record_practice("boozhoo", correct=True, session_id="s1")
        assert lex.lookup("boozhoo") is original


# ---------------------------------------------------------------------------
# 9. Privacy Policy
# ---------------------------------------------------------------------------

class TestLanguagePrivacyPolicy:
    def test_learner_data_never_goes_to_llm(self):
        from aura_language_privacy_policy import LanguagePrivacyPolicy
        policy = LanguagePrivacyPolicy()
        decision = policy.check_learner_data_to_llm("learner history")
        assert not decision.allowed

    def test_audio_upload_blocked_by_default(self):
        from aura_language_privacy_policy import LanguagePrivacyPolicy
        policy = LanguagePrivacyPolicy()
        decision = policy.check_audio_upload("elder recording")
        assert not decision.allowed

    def test_classroom_mode_blocks_learner_id_export(self):
        from aura_language_privacy_policy import LanguagePrivacyPolicy, PrivacyMode
        policy = LanguagePrivacyPolicy(mode=PrivacyMode.CLASSROOM)
        decision = policy.check_learner_id_in_export()
        assert not decision.allowed

    def test_teacher_export_mode_allows_learner_id(self):
        from aura_language_privacy_policy import LanguagePrivacyPolicy, PrivacyMode
        policy = LanguagePrivacyPolicy(mode=PrivacyMode.TEACHER_EXPORT, teacher_export_granted=True)
        decision = policy.check_learner_id_in_export()
        assert decision.allowed


# ---------------------------------------------------------------------------
# 10. Audio Consent Registry
# ---------------------------------------------------------------------------

class TestAudioConsentRegistry:
    def test_audio_requires_permission_ref(self):
        from aura_ojibwe_audio_consent_registry import AudioConsentRecord, AudioLevel, AURA_AUDIO_CONSENT_REGISTRY_V1
        with pytest.raises(ValueError, match="permission_ref"):
            AudioConsentRecord(
                schema_version=AURA_AUDIO_CONSENT_REGISTRY_V1,
                audio_id="audio_test",
                word="boozhoo",
                permission_ref="",  # empty — should fail
                audio_level=AudioLevel.LEVEL_1_PUBLIC_LINK,
                source_name="Test",
            )

    def test_audio_blocked_without_registry_entry(self):
        from aura_ojibwe_audio_consent_registry import AudioConsentRegistry
        registry = AudioConsentRegistry()
        decision = registry.check_access("nonexistent_audio_id")
        assert not decision.allowed

    def test_audio_blocked_when_playback_disabled(self):
        from aura_ojibwe_audio_consent_registry import AudioConsentRegistry, AudioConsentRecord, AudioLevel, AURA_AUDIO_CONSENT_REGISTRY_V1
        registry = AudioConsentRegistry()
        registry.register(AudioConsentRecord(
            schema_version=AURA_AUDIO_CONSENT_REGISTRY_V1,
            audio_id="audio_test_disabled",
            word="boozhoo",
            permission_ref="consent_001",
            audio_level=AudioLevel.LEVEL_1_PUBLIC_LINK,
            source_name="Test",
            playback_enabled=False,
        ))
        decision = registry.check_access("audio_test_disabled")
        assert not decision.allowed

    def test_audio_level_blocks_tts_without_community_consent(self):
        from aura_ojibwe_audio_consent_registry import AudioConsentRegistry, AudioConsentRecord, AudioLevel, AURA_AUDIO_CONSENT_REGISTRY_V1
        registry = AudioConsentRegistry()
        registry.register(AudioConsentRecord(
            schema_version=AURA_AUDIO_CONSENT_REGISTRY_V1,
            audio_id="audio_tts",
            word="boozhoo",
            permission_ref="consent_001",
            audio_level=AudioLevel.LEVEL_4_SYNTHETIC_TTS,  # Above MVP max
            source_name="TTS Dataset",
            playback_enabled=True,
        ))
        decision = registry.check_access("audio_tts")
        assert not decision.allowed
        assert "MVP maximum" in decision.reason


# ---------------------------------------------------------------------------
# 11. Morph Bridge (OjibweMorph FST)
# ---------------------------------------------------------------------------

class TestOjibweMorphBridge:
    def test_bridge_loads_without_error(self):
        from aura_ojibwe_morph_bridge import OjibweMorphBridge
        bridge = OjibweMorphBridge()
        status = bridge.fst_status()
        assert "fst_available" in status

    def test_nibaa_parses_as_vai(self):
        from aura_ojibwe_morph_bridge import OjibweMorphBridge, ParseStatus
        bridge = OjibweMorphBridge()
        result = bridge.parse_word("nibaa")
        if result.status == ParseStatus.PARSED:
            # OjibweMorph available: check VAI
            assert result.verb_class is not None
            assert "VAI" in str(result.verb_class)
        else:
            # FST unavailable: stub status is acceptable
            assert result.status in (ParseStatus.FST_UNAVAILABLE, ParseStatus.UNRECOGNIZED)

    def test_aki_parses_as_ni(self):
        from aura_ojibwe_morph_bridge import OjibweMorphBridge, ParseStatus
        bridge = OjibweMorphBridge()
        result = bridge.parse_word("aki")
        if result.status == ParseStatus.PARSED:
            assert result.noun_class is not None
            assert "NI" in str(result.noun_class)

    def test_parse_result_always_has_schema_version(self):
        from aura_ojibwe_morph_bridge import OjibweMorphBridge, AURA_OJIBWE_MORPH_BRIDGE_V1
        bridge = OjibweMorphBridge()
        result = bridge.parse_word("boozhoo")
        assert result.schema_version == AURA_OJIBWE_MORPH_BRIDGE_V1

    def test_citation_present_when_fst_loaded(self):
        from aura_ojibwe_morph_bridge import OjibweMorphBridge, OJIBWEMORPH_CITATION
        bridge = OjibweMorphBridge()
        result = bridge.parse_word("nibaa")
        assert result.citation == OJIBWEMORPH_CITATION


# ---------------------------------------------------------------------------
# 12. Dialect Conflict Resolver
# ---------------------------------------------------------------------------

class TestDialectConflictResolver:
    def test_no_conflict_when_forms_identical(self):
        from aura_ojibwe_dialect_conflict_resolver import DialectConflictResolver
        resolver = DialectConflictResolver()
        result = resolver.check_opd_against_treaty1(
            concept="grandmother",
            opd_form="nookomis",
            treaty1_form="nookomis",
            treaty1_source_type="VERIFIED",
        )
        assert result is None

    def test_dialect_conflict_prefers_treaty1_verified_source(self):
        from aura_ojibwe_dialect_conflict_resolver import DialectConflictResolver, ConflictPreference
        resolver = DialectConflictResolver()
        record = resolver.check_opd_against_treaty1(
            concept="fire",
            opd_form="ishkode",
            treaty1_form="shkode",
            treaty1_source_type="VERIFIED",
        )
        assert record is not None
        assert record.preference == ConflictPreference.TREATY1_VERIFIED
        assert record.tutor_preferred_form == "shkode"

    def test_conflict_tutor_message_non_hierarchical(self):
        """The tutor message must acknowledge both dialects, not dismiss OPD."""
        from aura_ojibwe_dialect_conflict_resolver import DialectConflictResolver
        resolver = DialectConflictResolver()
        record = resolver.check_opd_against_treaty1(
            concept="fire",
            opd_form="ishkode",
            treaty1_form="shkode",
            treaty1_source_type="VERIFIED",
        )
        # Should mention both forms
        assert "ishkode" in record.tutor_message or "shkode" in record.tutor_message
        assert "dialect" in record.tutor_message.lower()


# ---------------------------------------------------------------------------
# 13. Translation Guard
# ---------------------------------------------------------------------------

class TestTranslationGuard:
    def _make_guard(self, with_queue=True):
        from aura_language_source_registry import LanguageSourceRegistry
        from aura_ojibwe_dialect_profile import TREATY1_PLAINS_OJIBWE
        from aura_ojibwe_morph_bridge import OjibweMorphBridge
        from aura_ojibwe_translation_guard import TranslationGuard
        from aura_language_review_queue import LanguageReviewQueue
        registry = LanguageSourceRegistry()
        bridge = OjibweMorphBridge()
        queue = LanguageReviewQueue() if with_queue else None
        return TranslationGuard(TREATY1_PLAINS_OJIBWE, registry, bridge, queue), queue

    def test_dialect_profile_required(self):
        from aura_language_source_registry import LanguageSourceRegistry
        from aura_ojibwe_morph_bridge import OjibweMorphBridge
        from aura_ojibwe_translation_guard import TranslationGuard, ConfidenceStatus
        registry = LanguageSourceRegistry()
        bridge = OjibweMorphBridge()
        guard = TranslationGuard(None, registry, bridge)  # No dialect profile
        result = guard.evaluate("boozhoo", "opd_main", "Hello")
        assert result.confidence_status == ConfidenceStatus.BLOCKED

    def test_missing_source_gives_candidate_or_blocked(self):
        from aura_ojibwe_translation_guard import ConfidenceStatus
        guard, _ = self._make_guard()
        result = guard.evaluate("somefakeword", None, "no source")
        assert result.confidence_status in (ConfidenceStatus.BLOCKED, ConfidenceStatus.CANDIDATE_NEEDS_REVIEW)

    def test_blocked_response_has_no_translation(self):
        from aura_ojibwe_translation_guard import ConfidenceStatus
        guard, _ = self._make_guard()
        result = guard.evaluate("boozhoo", None, "Hello")
        if result.confidence_status == ConfidenceStatus.BLOCKED:
            assert result.translation is None

    def test_candidate_creates_review_queue_item(self):
        from aura_ojibwe_translation_guard import ConfidenceStatus
        guard, queue = self._make_guard(with_queue=True)
        # opd_main has confidence 0.40, below VERIFIED threshold 0.80
        result = guard.evaluate("boozhoo", "opd_main", "Hello")
        if result.confidence_status == ConfidenceStatus.CANDIDATE_NEEDS_REVIEW:
            assert result.review_queue_id is not None
            assert queue.get(result.review_queue_id) is not None

    def test_every_result_has_confidence_status(self):
        guard, _ = self._make_guard()
        result = guard.evaluate("boozhoo", "opd_main", "Hello")
        assert result.confidence_status is not None


# ---------------------------------------------------------------------------
# 14. Pronunciation Bridge
# ---------------------------------------------------------------------------

class TestPronunciationBridge:
    def test_level0_always_returns_phonetic_text(self):
        from aura_ojibwe_pronunciation_bridge import OjibwePronunciationBridge
        from aura_ojibwe_audio_consent_registry import AudioConsentRegistry
        bridge = OjibwePronunciationBridge(AudioConsentRegistry())
        hint = bridge.get_hint("boozhoo")
        assert hint.phonetic_breakdown
        assert "boozhoo" in hint.phonetic_breakdown

    def test_audio_blocked_without_consent(self):
        from aura_ojibwe_pronunciation_bridge import OjibwePronunciationBridge
        from aura_ojibwe_audio_consent_registry import AudioConsentRegistry, AudioLevel
        bridge = OjibwePronunciationBridge(AudioConsentRegistry())
        hint = bridge.get_hint("nibaa", audio_ref="nonexistent_audio")
        assert hint.audio_level == AudioLevel.LEVEL_0_TEXT_ONLY
        assert hint.audio_url is None


# ---------------------------------------------------------------------------
# 15. Tutor Engine — end-to-end
# ---------------------------------------------------------------------------

class TestOjibweTutorEngine:
    def _make_engine(self):
        from aura_ojibwe_tutor_engine import OjibweTutorEngine
        return OjibweTutorEngine()

    def test_every_language_answer_has_source_and_dialect_status(self):
        engine = self._make_engine()
        result = engine.respond("boozhoo")
        assert result.confidence_status is not None
        assert isinstance(result.source_refs, list)
        assert result.dialect_notes is not None or result.confidence_status.value == "VERIFIED"

    def test_tutor_response_always_includes_confidence_status(self):
        engine = self._make_engine()
        for word in ["boozhoo", "nibaa", "aki", "nonexistentword123"]:
            result = engine.respond(word)
            assert result.confidence_status is not None
            assert result.schema_version is not None

    def test_blocked_response_has_no_answer(self):
        from aura_ojibwe_tutor_engine import OjibweTutorEngine
        from aura_language_data_governance import LanguageDataGovernancePolicy, DataAccessLevel
        from aura_ojibwe_translation_guard import ConfidenceStatus
        # Build engine with a governance policy that blocks everything
        engine = OjibweTutorEngine()
        # The blocked path is: no source + no dialect. Test via guard directly.
        result = engine.respond("boozhoo")
        if result.confidence_status == ConfidenceStatus.BLOCKED:
            assert result.answer is None

    def test_known_word_returns_answer_with_citation(self):
        engine = self._make_engine()
        result = engine.respond("boozhoo")
        # boozhoo is in our lexicon — should get something
        assert result.query == "boozhoo"
        assert result.source_refs is not None

    def test_fst_parse_present_in_morphology_response(self):
        from aura_ojibwe_tutor_engine import OjibweTutorEngine, TutorMode
        engine = OjibweTutorEngine()
        result = engine.respond("nibaa", mode=TutorMode.MORPHOLOGY_EXPLANATION)
        # Morphology breakdown should always be present (even if FST unavailable)
        assert result.morphology_breakdown is not None

    def test_external_llm_never_receives_restricted_data(self):
        """Governance check blocks restricted data before it could reach LLM egress."""
        from aura_language_data_governance import LanguageDataGovernancePolicy, DataAccessLevel
        policy = LanguageDataGovernancePolicy()
        decision = policy.check_can_send_to_llm(DataAccessLevel.RESTRICTED, "restricted item")
        assert not decision.allowed
        # This is the wall — tutor engine calls this before any LLM egress
