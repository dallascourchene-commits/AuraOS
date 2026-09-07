from __future__ import annotations
import json, sys
from dataclasses import asdict
from pathlib import Path

HERE=Path(__file__).resolve()
ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE.parent))
from k27_dynamic_navigator import TrafficEvent,summarize_traffic,digest

DATA=ROOT/'artifacts/arena/k27_dynamic_navigator/real_navigation_traffic_20260907.json'

def main():
    raw=json.loads(DATA.read_text())
    events=[TrafficEvent(**row) for row in raw['events']]
    summary=summarize_traffic(events)
    exact_locators={e.locator for e in events if e.hydration_level=='exact'}
    touched_locators={e.locator for e in events}
    metadata_or_snippet=sum(e.hydration_level!='exact' for e in events)
    receipt={
      'schema':'aura.k27.dynamic_navigator.telemetry_receipt.v1',
      'observation_scope':raw['observation_scope'],
      'summary':asdict(summary),
      'exact_hydrated_unique_locators':len(exact_locators),
      'touched_unique_locators':len(touched_locators),
      'nonexact_event_fraction':metadata_or_snippet/len(events),
      'production_wide_traffic_claim':False,
      'effect_authority':False,
      'gate10':False,
    }
    receipt['receipt_root']=digest(receipt)
    print(json.dumps(receipt,sort_keys=True,indent=2))

if __name__=='__main__': main()
