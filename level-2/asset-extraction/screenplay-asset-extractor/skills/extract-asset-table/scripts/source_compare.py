#!/usr/bin/env python3
"""Compare structural screenplay headers from two source formats."""
import json
from pathlib import Path
from parse_script import parse

def structure(data):
    return [(s['scene_id'],s.get('location',''),s.get('int_ext',''),s.get('time',''))
            for e in data.get('episodes',[]) for s in e.get('scenes',[])]
def compare(left,right):
    a,b=structure(parse(Path(left))),structure(parse(Path(right)))
    return {'left':str(Path(left).resolve()),'right':str(Path(right).resolve()),
            'left_scene_count':len(a),'right_scene_count':len(b),'same':a==b,
            'missing_in_right':[x for x in a if x not in b],
            'missing_in_left':[x for x in b if x not in a],
            'changed_positions':[{'index':i+1,'left':x,'right':y} for i,(x,y) in enumerate(zip(a,b)) if x!=y]}

