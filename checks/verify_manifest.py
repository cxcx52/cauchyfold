#!/usr/bin/env python3
"""Check distributed files without recompilation or estimator execution."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
manifest = json.loads((ROOT / 'manifest.json').read_bytes())
for item in manifest['files']:
    p = ROOT / item['path']
    b = p.read_bytes()
    assert len(b) == item['bytes'], ('length', item['path'])
    assert hashlib.sha256(b).hexdigest() == item['sha256'], ('SHA256', item['path'])
print('PASS:', len(manifest['files']), 'distributed files match manifest.json')
