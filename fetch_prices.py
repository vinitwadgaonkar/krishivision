"""
Pre-fetch live mandi prices at build time.
Runs during Docker build to cache today's prices as JSON.
This sidesteps Cloudflare blocking runtime requests from cloud IPs.
"""

import json
import sys
from market_prices import CROP_SLUG_MAP, _fetch_json, _parse_sveltekit_data, STATE_SLUG_TO_NAME

OUTPUT_FILE = 'cached_prices.json'


def main():
    results = {}
    success = 0
    fail = 0

    for crop_name, slug in CROP_SLUG_MAP.items():
        print(f'  Fetching {crop_name} ({slug})...', end=' ')
        raw = _fetch_json(slug)
        if raw:
            parsed = _parse_sveltekit_data(raw, slug)
            if parsed:
                results[crop_name] = parsed
                avg = parsed['national_avg']
                states = len(parsed['state_prices'])
                print(f'₹{avg:,.2f} ({states} states, {parsed["num_mandis"]} mandis)')
                success += 1
                continue
        print('FAILED')
        fail += 1

    print(f'\nFetched {success}/{success + fail} crops')

    with open(OUTPUT_FILE, 'w') as f:
        json.dump({
            'prices': results,
            'fetched_at': __import__('datetime').datetime.utcnow().isoformat() + 'Z',
        }, f, indent=2)

    print(f'Saved to {OUTPUT_FILE}')
    return 0 if success > 0 else 1


if __name__ == '__main__':
    sys.exit(main())
