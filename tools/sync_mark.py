#!/usr/bin/env python3
"""Generate the native icon from the exact Three.js contour source."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def render():
    source=(ROOT/'omasteamdeck/assets/startup/mark.js').read_text()
    mark=json.loads(source.split('export const mark = ',1)[1].strip().removesuffix(';'))
    paths=[mark['outer'],*mark['holes']]
    d=' '.join(' '.join(map(str,command)) for path in paths for command in path)
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 180 180">'
            '<title>OmaFlow Open Flow refinement — pending review</title>'
            f'<path fill="#edf3fa" fill-rule="evenodd" d="{d}"/></svg>\n')
if __name__=='__main__':
    (ROOT/'omasteamdeck/assets/omaflow-mark.svg').write_text(render())
