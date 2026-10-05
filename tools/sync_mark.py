#!/usr/bin/env python3
"""Generate the native icon from the exact Three.js contour source."""
import json
import argparse
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def render(concept='open-flow'):
    filename='concept-lift.js' if concept=='lift' else 'mark.js'
    title='Lift alternative' if concept=='lift' else 'Open Flow refinement'
    source=(ROOT/'omasteamdeck/assets/startup'/filename).read_text()
    mark=json.loads(source.split('export const mark = ',1)[1].strip().removesuffix(';'))
    paths=[mark['outer'],*mark['holes']]
    d=' '.join(' '.join(map(str,command)) for path in paths for command in path)
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 180 180">'
            f'<title>OmaFlow {title} — pending review</title>'
            f'<path fill="#edf3fa" fill-rule="evenodd" d="{d}"/></svg>\n')
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--concept',choices=['open-flow','lift'],default='open-flow')
    concept=parser.parse_args().concept
    filename='omaflow-lift-concept.svg' if concept=='lift' else 'omaflow-mark.svg'
    (ROOT/'omasteamdeck/assets'/filename).write_text(render(concept))
