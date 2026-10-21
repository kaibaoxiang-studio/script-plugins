"""Event-sourced local runs, derived from Bird's Nest's MIT-licensed EventStore design.

Events are canonical; snapshots are disposable projections. Transactions serialize
sequence allocation across processes. Read-only status does not create a database.
"""
from __future__ import annotations
import json
from pathlib import Path
import sqlite3
from .common import now, digest

class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as con:
            con.executescript('''
              CREATE TABLE IF NOT EXISTS events(
                run_id TEXT NOT NULL, seq INTEGER NOT NULL, kind TEXT NOT NULL,
                created_at TEXT NOT NULL, payload TEXT NOT NULL, sha256 TEXT NOT NULL,
                PRIMARY KEY(run_id,seq));
              CREATE TABLE IF NOT EXISTS snapshots(run_id TEXT PRIMARY KEY, payload TEXT NOT NULL);
            ''')

    def connect(self):
        con = sqlite3.connect(self.path, timeout=30)
        con.execute('PRAGMA journal_mode=WAL')
        return con

    @staticmethod
    def reduce(state, kind, payload):
        if kind == 'created':
            return {**payload, 'status': 'pending', 'nodes': {}, 'questions': []}
        if kind == 'status':
            state['status'] = payload['status']
            state['questions'] = payload.get('questions', [])
        elif kind == 'node':
            state['nodes'][payload['id']] = payload
        elif kind == 'answers':
            state.setdefault('answers', {}).update(payload)
        return state

    def append(self, run_id, kind, payload):
        with self.connect() as con:
            con.execute('BEGIN IMMEDIATE')
            row = con.execute('SELECT payload FROM snapshots WHERE run_id=?', (run_id,)).fetchone()
            if kind == 'created' and row:
                raise ValueError('Run already exists')
            if kind != 'created' and not row:
                raise KeyError(run_id)
            state = json.loads(row[0]) if row else {}
            seq = con.execute('SELECT COALESCE(MAX(seq),0)+1 FROM events WHERE run_id=?', (run_id,)).fetchone()[0]
            con.execute('INSERT INTO events VALUES(?,?,?,?,?,?)',
                        (run_id,seq,kind,now(),json.dumps(payload,ensure_ascii=False),digest(payload)))
            state = self.reduce(state,kind,payload)
            con.execute('INSERT OR REPLACE INTO snapshots VALUES(?,?)',
                        (run_id,json.dumps(state,ensure_ascii=False)))
        return state

    def get(self, run_id):
        with self.connect() as con:
            row=con.execute('SELECT payload FROM snapshots WHERE run_id=?',(run_id,)).fetchone()
        if not row:
            raise KeyError(run_id)
        return json.loads(row[0])

    def replay(self, run_id):
        with self.connect() as con:
            con.execute('BEGIN IMMEDIATE')
            rows=con.execute('SELECT kind,payload,sha256 FROM events WHERE run_id=? ORDER BY seq',(run_id,)).fetchall()
            if not rows:
                raise KeyError(run_id)
            state={}
            for kind, raw, expected in rows:
                payload=json.loads(raw)
                if digest(payload)!=expected:
                    raise ValueError('Event hash mismatch')
                state=self.reduce(state,kind,payload)
            con.execute('INSERT OR REPLACE INTO snapshots VALUES(?,?)',(run_id,json.dumps(state,ensure_ascii=False)))
        return state
