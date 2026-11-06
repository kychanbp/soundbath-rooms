"""start | ip | stop for one test pod. Ends the pod for good on stop."""
import json, os, sys, time
from rp import gql
NAME = 'soundbath-motion'
def pods(): return [p for p in gql('query { myself { pods { id name desiredStatus costPerHr runtime { ports { ip isIpPublic privatePort publicPort } uptimeInSeconds } machine { gpuDisplayName } } } }')['data']['myself']['pods']]
cmd = sys.argv[1]
if cmd == 'start':
    if [p for p in pods() if p['name'] == NAME]: print('already', pods()); sys.exit()
    pub = open(os.path.expanduser('~/.ssh/runpod_soundbath.pub')).read().strip()
    m = 'mutation($i: PodFindAndDeployOnDemandInput) { podFindAndDeployOnDemand(input: $i) { id costPerHr machine { gpuDisplayName } } }'
    for g in ('NVIDIA GeForce RTX 4090', 'NVIDIA RTX 6000 Ada Generation', 'NVIDIA A40', 'NVIDIA RTX PRO 4500 Blackwell'):
        i = dict(cloudType='ALL', gpuCount=1, volumeInGb=0, containerDiskInGb=120, minVcpuCount=8, minMemoryInGb=30, gpuTypeId=g, name=NAME,
                 imageName='runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04', ports='22/tcp', env=[dict(key='PUBLIC_KEY', value=pub)], supportPublicIp=True)
        d = gql(m, dict(i=i))
        if d.get('data', {}).get('podFindAndDeployOnDemand'): print('started', d['data']['podFindAndDeployOnDemand']); sys.exit()
        print('no', g, str(d.get('errors'))[:120])
    sys.exit(1)
if cmd == 'ip':
    for _ in range(60):
        for p in pods():
            for x in (p.get('runtime') or {}).get('ports') or []:
                if x['privatePort'] == 22 and x['isIpPublic']: print(x['ip'], x['publicPort'], p['id'], p['costPerHr'], p['machine']['gpuDisplayName']); sys.exit()
        time.sleep(5)
    print('timeout', pods()); sys.exit(1)
if cmd == 'stop':
    for p in pods():
        print('end', p['id'], gql('mutation($i: PodTerminateInput!) { podTerminate(input: $i) }', dict(i=dict(podId=p['id']))).get('errors'))
    print('left', pods())
