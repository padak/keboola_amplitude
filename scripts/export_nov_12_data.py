#!/usr/bin/env python3
"""
Export Amplitude data that includes Nov 12
Based on the test script result, data exists in Last 3 days range
"""

from dotenv import load_dotenv
load_dotenv(dotenv_path="/Users/padak/github/amplitude/.env")

from amplitude_driver import AmplitudeDriver
import json

client = AmplitudeDriver.from_env()

# Export from Last 3 days (which includes Nov 12)
print("Exporting events from Last 3 days (includes Nov 12)...")
events = client.read_events_export(start='20251114T17', end='20251117T17')

print(f"\n✓ Exported {len(events)} total events")

# Filter for Nov 12 events
nov_12_events = [e for e in events if '2025-11-12' in str(e.get('event_time', ''))]
print(f"✓ Nov 12 events found: {len(nov_12_events)}")

# Save to file
output_file = 'amplitude_nov_12_events.jsonl'
with open(output_file, 'w') as f:
    for event in nov_12_events:
        f.write(json.dumps(event) + '\n')

print(f"✓ Saved {len(nov_12_events)} Nov 12 events to {output_file}")

# Show summary
if nov_12_events:
    print(f"\nData summary:")
    event_types = {}
    users = set()

    for event in nov_12_events:
        event_type = event.get('event_type', 'unknown')
        event_types[event_type] = event_types.get(event_type, 0) + 1
        if user_id := event.get('user_id'):
            users.add(user_id)

    print(f"  Unique users: {len(users)}")
    print(f"  Event types: {len(event_types)}")
    print(f"  Top events:")
    for event_type, count in sorted(event_types.items(), key=lambda x: -x[1])[:5]:
        print(f"    - {event_type}: {count}")

    print(f"\n✓ Data ready for Keboola import")

client.close()
