"""Small RunPod client. Reads the key from the environment or ~/.zshrc and never prints it."""
import json, os, re, sys, urllib.request
def key():
    k = os.environ.get('RUNPOD_API_KEY')
    if k: return k
    m = re.findall(r"RUNPOD_API_KEY=['\"]?([^'\"\s]+)", open(os.path.expanduser('~/.zshrc')).read())
    return m[-1] if m else None
def gql(q, v=None):
    r = urllib.request.Request('https://api.runpod.io/graphql', data=json.dumps(dict(query=q, variables=v or {})).encode(), headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key(), 'User-Agent': 'soundbath-rooms'})
    return json.load(urllib.request.urlopen(r, timeout=40))
if __name__ == '__main__':
    k = key(); print('key found:', bool(k), 'placeholder:', k in ('your_key', 'YOUR_KEY') if k else None, 'length:', len(k) if k else 0)
    d = gql('query { myself { id clientBalance currentSpendPerHr pods { id name desiredStatus } } gpuTypes { id displayName memoryInGb secureCloud communityCloud lowestPrice(input:{gpuCount:1}) { minimumBidPrice uninterruptablePrice stockStatus } } }')
    if 'errors' in d: print(d['errors'][:1]); sys.exit(1)
    m = d['data']['myself']; print('balance', m['clientBalance'], 'spend/hr', m['currentSpendPerHr'], 'pods', [(p['name'], p['desiredStatus']) for p in m['pods']])
    g = [x for x in d['data']['gpuTypes'] if (x.get('memoryInGb') or 0) >= 24 and x['lowestPrice'] and x['lowestPrice'].get('uninterruptablePrice')]
    for x in sorted(g, key=lambda x: x['lowestPrice']['uninterruptablePrice'])[:12]:
        print(x['id'], x['memoryInGb'], x['lowestPrice']['uninterruptablePrice'], x['lowestPrice']['stockStatus'], 'sec' if x['secureCloud'] else '', 'com' if x['communityCloud'] else '')
