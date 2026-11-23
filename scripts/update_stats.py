#!/usr/bin/env python3
"""Update only the coding statistics block in this profile repository."""
import datetime as dt
import json
import pathlib
import re
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
START = '<!-- CODING-STATS:START -->'
END = '<!-- CODING-STATS:END -->'
LC_USER = 'mahmoud_Khalid29'
CF_USER = 'mahmoud11A'


def fetch_json(url, payload=None):
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(url, data=data, headers={
        'User-Agent': 'MahmoudProfileStats/1.0 (daily public profile update)',
        'Content-Type': 'application/json',
    })
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def leetcode():
    payload = {
        'query': 'query($username:String!){matchedUser(username:$username){username submitStatsGlobal{acSubmissionNum{difficulty count}}}}',
        'variables': {'username': LC_USER},
    }
    result = fetch_json('https://leetcode.com/graphql/', payload)
    user = result['data']['matchedUser']
    if not user or user['username'].lower() != LC_USER.lower():
        raise ValueError('LeetCode profile did not match')
    counts = {v['difficulty']: v['count'] for v in user['submitStatsGlobal']['acSubmissionNum']}
    if any(type(counts.get(k)) is not int or counts[k] < 0 for k in ['All', 'Easy', 'Medium', 'Hard']):
        raise ValueError('Invalid LeetCode statistics')
    if counts['All'] != sum(counts[k] for k in ['Easy', 'Medium', 'Hard']):
        raise ValueError('Inconsistent LeetCode totals')
    return counts


def cf_call(method, params):
    result = fetch_json('https://codeforces.com/api/' + method + '?' + params)
    if result.get('status') != 'OK':
        raise ValueError('Codeforces API unavailable')
    return result['result']


def codeforces():
    user = cf_call('user.info', 'handles=' + CF_USER)[0]
    if user['handle'].lower() != CF_USER.lower():
        raise ValueError('Codeforces profile did not match')
    # Use official rating fields only. Public submission history may omit activity.
    return {'rating': user.get('rating'), 'max_rating': user.get('maxRating')}


def render(state):
    lines = ['| Platform | Public statistics |',
             '| :--- | :--- |']
    lc = state.get('leetcode', {})
    cf = state.get('codeforces', {})
    if 'data' in lc:
        d = lc['data']
        text = f"**{d['All']} solved** · Easy {d['Easy']} · Medium {d['Medium']} · Hard {d['Hard']}"
    else:
        text = 'Not available yet'
    lines.append(f"| [LeetCode](https://leetcode.com/u/{LC_USER}/) | {text} |")
    if 'data' in cf:
        d = cf['data']
        rating = d['rating'] if d['rating'] is not None else 'Unrated'
        peak = d['max_rating'] if d['max_rating'] is not None else 'Unrated'
        text = f"Rating **{rating}** · Best **{peak}**"
    else:
        text = 'Not available yet'
    lines.append(f"| [Codeforces](https://codeforces.com/profile/{CF_USER}) | {text} |")
    failed = [name for name in ['leetcode', 'codeforces'] if state.get(name, {}).get('fetch_failed')]
    lines += ['', 'Scheduled to refresh daily from public profiles.']
    if failed:
        lines += ['', 'Latest fetch unavailable for ' + ', '.join(failed) + '. Previously verified data is shown and may be out of date.']
    return '\n'.join(lines)


def replace_block(text, block):
    if text.count(START) != 1 or text.count(END) != 1 or text.index(START) > text.index(END):
        raise ValueError('README must have exactly one correctly ordered statistics block')
    before, tail = text.split(START, 1)
    _, after = tail.split(END, 1)
    return before + START + '\n' + block + '\n' + END + after


def main():
    state_path = ROOT / 'stats.json'
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    for key, func in [('leetcode', leetcode), ('codeforces', codeforces)]:
        try:
            data = func()
            state[key] = {'data': data, 'updated_at': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d %H:%M'), 'fetch_failed': False}
        except Exception as error:
            print(f'{key}: fetch unavailable ({type(error).__name__}); keeping previous data')
            state.setdefault(key, {})['fetch_failed'] = True
    readme = ROOT / 'README.md'
    updated = replace_block(readme.read_text(), render(state))
    state_path.write_text(json.dumps(state, indent=2) + '\n')
    readme.write_text(updated)
    if not any('data' in state.get(k, {}) for k in ['leetcode', 'codeforces']):
        raise SystemExit('Neither source could be fetched')


if __name__ == '__main__':
    main()
