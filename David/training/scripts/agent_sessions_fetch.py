"""Download an ordered, bounded prefix through the public dataset rows service."""
import concurrent.futures
import json
from pathlib import Path
import socket
import urllib.parse
import urllib.request

DEST = Path('data/downloads/agent_sessions')
DEST.mkdir(parents=True, exist_ok=True)
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def configure_dns():
    """Resolve the public service locally while preserving its TLS hostname."""
    host = 'datasets-server.huggingface.co'
    request = urllib.request.Request('https://1.1.1.1/dns-query?name=' + host + '&type=A', headers={'accept':'application/dns-json'})
    with OPENER.open(request, timeout=15) as response:
        addresses = [item['data'] for item in json.load(response)['Answer'] if item['type'] == 1]
    original = socket.getaddrinfo
    socket.getaddrinfo = lambda name, *args, **kwargs: original(addresses[0] if name == host else name, *args, **kwargs)


def fetch(offset):
    path = DEST / f'rows-{offset:06d}.jsonl'
    if path.exists():
        return dict(offset=offset, status='cached')
    params = dict(dataset='TonyDzi/agent-sessions', config='default', split='train', offset=offset, length=100)
    url = 'https://datasets-server.huggingface.co/rows?' + urllib.parse.urlencode(params)
    try:
        with OPENER.open(url, timeout=45) as response:
            data = json.load(response)
        temporary = path.with_suffix('.part')
        with temporary.open('w', encoding='utf-8') as output:
            for item in data['rows']:
                row = item['row']
                row['_source_row_index'] = item['row_idx']
                row['_truncated_cells'] = item.get('truncated_cells', [])
                output.write(json.dumps(row, ensure_ascii=False) + '\n')
        temporary.replace(path)
        return dict(offset=offset, status='downloaded', rows=len(data['rows']))
    except Exception as error:
        return dict(offset=offset, status='error', error_type=type(error).__name__)


if __name__ == '__main__':
    configure_dns()
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(fetch, range(0, 7000, 100)))
    report = Path('results/sources/agent_sessions-download.json')
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(results, indent=2), encoding='utf-8')
    print(json.dumps(results))
