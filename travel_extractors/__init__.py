"""Travel extraction plugins for Aura's local-first scraper ingestion lane."""

from travel_extractors.option_b import NormalizedTravelRecord, extract_option_b_record

__all__ = ["NormalizedTravelRecord", "extract_option_b_record"]
