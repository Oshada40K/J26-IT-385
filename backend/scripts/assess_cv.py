"""Assess any CV through the same authenticated upload API as the frontend.

Run from backend: .venv/bin/python scripts/assess_cv.py path/to/cv.pdf
Outputs a shareable result and private local session credentials in .data/.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.component01_skill.router import router


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('cv', type=Path)
    parser.add_argument('--output', type=Path, default=Path('.data/sample-assessment.json'))
    args = parser.parse_args()
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client:
        session = client.post('/api/component01/skills/session').json()
        headers = {'Authorization': 'Bearer ' + session['access_token']}
        result = client.post('/api/component01/skills/upload', data={'candidate_id': session['candidate_id']}, files={'file': (args.cv.name, args.cv.read_bytes())}, headers=headers)
        if result.status_code != 200:
            parser.exit(1, result.text + '\n')
        base = '/api/component01/skills/' + session['candidate_id']
        details = client.get(base + '/details', headers=headers).json()
        shared = client.get(base, headers=headers).json()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({'profile': shared, 'details': details}, indent=2) + '\n')
        private = args.output.with_name(args.output.stem + '-session.json')
        private.touch(mode=0o600, exist_ok=True)
        private.write_text(json.dumps(session, indent=2) + '\n')
        print(f"Saved {len(details['skills'])} estimated skills to {args.output}")
        print(f'Private access credentials: {private} (do not commit or share).')


if __name__ == '__main__':
    main()
