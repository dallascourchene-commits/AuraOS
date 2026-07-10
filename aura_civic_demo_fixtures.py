"""Aura Civic Demo Fixtures — deterministic Winnipeg demo data.

Every synthetic record displays SYNTHETIC_DEMO_DATA.
"""
from __future__ import annotations
from typing import Any

TRUTH_SYNTHETIC = "SYNTHETIC_DEMO_DATA"

def hairstylist_fixtures() -> dict[str, Any]:
    return {
        "objective": "Our neighbourhood needs an affordable hairstylist. We want the community to own and benefit from it.",
        "needs": [
            {"need_id":"NEED-001","description":"Affordable hairstyling for youth and elders","truth_class":TRUTH_SYNTHETIC,"consent_to_match":True,"privacy_class":"PUBLIC_PSEUDONYMOUS"},
            {"need_id":"NEED-002","description":"Wheelchair accessible salon","truth_class":TRUTH_SYNTHETIC,"consent_to_match":True,"privacy_class":"PUBLIC_PSEUDONYMOUS"},
        ],
        "offers": [
            {"offer_id":"OFFER-SKILL-001","offer_type":"skill","description":"Licensed hairstylist with 10 years experience","consent_to_match":True,"truth_class":TRUTH_SYNTHETIC},
            {"offer_id":"OFFER-SPACE-001","offer_type":"space","description":"Accessible ground-floor room near transit","consent_to_match":True,"truth_class":TRUTH_SYNTHETIC},
            {"offer_id":"OFFER-EQUIP-001","offer_type":"equipment","description":"Chairs, mirrors, and styling tools","consent_to_match":True,"truth_class":TRUTH_SYNTHETIC},
            {"offer_id":"OFFER-FUND-001","offer_type":"funding","description":"Limited investment interest for cooperative","consent_to_match":True,"truth_class":TRUTH_SYNTHETIC},
            {"offer_id":"OFFER-MENTOR-001","offer_type":"mentor","description":"Cooperative business mentor","consent_to_match":True,"truth_class":TRUTH_SYNTHETIC},
        ],
        "concerns": [
            {"concern_id":"CONCERN-001","description":"Affordable youth/elder pricing","truth_class":TRUTH_SYNTHETIC},
            {"concern_id":"CONCERN-002","description":"Wheelchair accessibility","truth_class":TRUTH_SYNTHETIC},
            {"concern_id":"CONCERN-003","description":"Evening hours","truth_class":TRUTH_SYNTHETIC},
            {"concern_id":"CONCERN-004","description":"Parking and noise","truth_class":TRUTH_SYNTHETIC},
            {"concern_id":"CONCERN-005","description":"Insurance","truth_class":TRUTH_SYNTHETIC},
            {"concern_id":"CONCERN-006","description":"Sustainability","truth_class":TRUTH_SYNTHETIC},
        ],
        "objections": [
            {"objection_id":"OBJ-001","proposal_ref":"SCEN-chair_rental","reason":"May not maintain community ownership","severity":"OBJECTION","truth_class":TRUTH_SYNTHETIC},
        ],
        "representation_gaps": ["Youth voices underrepresented","Elder voices underrepresented"],
        "scenarios": [
            {"scenario_id":"SCEN-coop","title":"Community Cooperative","description":"Community-owned cooperative salon","metrics":{"local_ownership":0.9,"accessibility":0.7,"cost":0.5},"pareto_label":"maximum_community_ownership","truth_class":TRUTH_SYNTHETIC},
            {"scenario_id":"SCEN-chair_rental","title":"Chair Rental","description":"Stylist rents chair in existing space","metrics":{"local_ownership":0.3,"accessibility":0.5,"cost":0.8},"pareto_label":"lowest_cost","truth_class":TRUTH_SYNTHETIC},
            {"scenario_id":"SCEN-mobile","title":"Mobile Pilot","description":"Mobile hairstyling service","metrics":{"local_ownership":0.6,"accessibility":0.8,"cost":0.6},"pareto_label":"fastest_pilot","truth_class":TRUTH_SYNTHETIC},
            {"scenario_id":"SCEN-social","title":"Social Enterprise","description":"Social enterprise with sliding scale","metrics":{"local_ownership":0.5,"accessibility":0.9,"cost":0.4},"pareto_label":"balanced_candidate","truth_class":TRUTH_SYNTHETIC},
        ],
        "legal_instruments": [
            {"instrument_id":"LI-zoning","name":"Zoning Bylaw","level":"bylaw","applicability":"POSSIBLY_APPLICABLE","truth_class":"OFFICIAL_PRIMARY_SOURCE","as_of_date":"2026-01-01"},
            {"instrument_id":"LI-licence","name":"Business Licence Bylaw","level":"bylaw","applicability":"POSSIBLY_APPLICABLE","truth_class":"OFFICIAL_PRIMARY_SOURCE","as_of_date":"2026-01-01"},
        ],
        "council_items": [
            {"item_id":"CI-001","title":"Community Economic Development Committee - Update","body":"Standing Committee","meeting_date":"2026-03-15","disposition":"Received as information","truth_class":TRUTH_SYNTHETIC},
        ],
        "geojson": {
            "type":"FeatureCollection",
            "features":[
                {"type":"Feature","properties":{"name":"Demo Neighbourhood","truth_class":TRUTH_SYNTHETIC},"geometry":{"type":"Polygon","coordinates":[[[-97.15,49.88],[-97.14,49.88],[-97.14,49.89],[-97.15,49.89],[-97.15,49.88]]]}},
                {"type":"Feature","properties":{"name":"Community Centre","type":"facility","truth_class":TRUTH_SYNTHETIC},"geometry":{"type":"Point","coordinates":[-97.145,49.885]}},
                {"type":"Feature","properties":{"name":"Transit Stop","type":"transit","truth_class":TRUTH_SYNTHETIC},"geometry":{"type":"Point","coordinates":[-97.146,49.886]}},
                {"type":"Feature","properties":{"name":"Proposed Salon Location","type":"candidate","truth_class":TRUTH_SYNTHETIC},"geometry":{"type":"Point","coordinates":[-97.145,49.886]}},
            ],
        },
        "heatmap": {
            "metric":"service_access_distance","source":"SYNTHETIC_DEMO_DATA","time_range":"2026-01-01 to 2026-06-30",
            "geographic_unit":"neighbourhood","aggregation":"average","denominator":"resident_count",
            "missing_data_rate":0.0,"freshness":"2026-07-10","uncertainty":"low","truth_class":TRUTH_SYNTHETIC,
            "values":[{"label":"Central Winnipeg","value":1.2},{"label":"North Winnipeg","value":2.8}],
        },
    }

def youth_centre_fixtures() -> dict[str, Any]:
    return {
        "objective": "Create a youth healing, training, and employment centre in our neighbourhood.",
        "needs": [
            {"need_id":"NEED-Y-001","description":"Youth employment and training programs","truth_class":TRUTH_SYNTHETIC,"consent_to_match":True},
            {"need_id":"NEED-Y-002","description":"Cultural programming space","truth_class":TRUTH_SYNTHETIC,"consent_to_match":True},
        ],
        "offers": [
            {"offer_id":"OFFER-Y-001","offer_type":"space","description":"Unused community hall","consent_to_match":True,"truth_class":TRUTH_SYNTHETIC},
            {"offer_id":"OFFER-Y-002","offer_type":"funding","description":"Provincial youth grant eligibility","consent_to_match":True,"truth_class":TRUTH_SYNTHETIC},
            {"offer_id":"OFFER-Y-003","offer_type":"mentor","description":"Elder willing to teach cultural crafts","consent_to_match":True,"truth_class":TRUTH_SYNTHETIC},
        ],
        "representation_gaps": ["Youth voices underrepresented","Indigenous youth voices underrepresented"],
        "scenarios": [
            {"scenario_id":"SCEN-Y-coop","title":"Community Youth Cooperative","description":"Youth-led cooperative training centre","metrics":{"local_ownership":0.8,"accessibility":0.7,"cost":0.5},"truth_class":TRUTH_SYNTHETIC},
            {"scenario_id":"SCEN-Y-partner","title":"Partnership Model","description":"Partnership with existing service provider","metrics":{"local_ownership":0.4,"accessibility":0.9,"cost":0.7},"truth_class":TRUTH_SYNTHETIC},
        ],
    }

def council_issue_fixtures() -> dict[str, Any]:
    return {
        "issues": [
            {"item_id":"CI-001","title":"Bylaw Enforcement Update","body":"Standing Policy Committee on Protection and Community Services","meeting_date":"2026-04-02","disposition":"Motion carried","vote_record":"12-1","source_ref":"winnipeg_council_minutes","truth_class":"OFFICIAL_SNAPSHOT","extraction_confidence":0.95},
            {"item_id":"CI-002","title":"Community Grant Program Allocation","body":"Finance Committee","meeting_date":"2026-03-20","disposition":"Received as information","vote_record":"","source_ref":"winnipeg_council_minutes","truth_class":"OFFICIAL_SNAPSHOT","extraction_confidence":0.90},
        ],
        "note": "Do not infer councillor motives.",
    }
