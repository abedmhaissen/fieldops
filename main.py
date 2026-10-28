import argparse
import json
from pathlib import Path
from core import fixture_run

BRIEF = ('Customer: Northstar Retail (synthetic). Support AI mixes tenant policies, '
         'uses stale returns guidance, and fails on slow or transient ERP calls. '
         'Diagnose the failures and propose a reversible configuration. '
         'Owner: customer platform team. Success: all six acceptance cases pass; '
         'simulated p95 <= 700ms. Production rollout needs human approval.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--output', default='report.json')
    args = parser.parse_args()
    if args.live:
        from agents import build_graph
        result = build_graph().invoke({'brief': BRIEF}, {'recursion_limit': 30})
    else:
        result = fixture_run()
    Path(args.output).write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
