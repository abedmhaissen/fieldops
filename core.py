"""Deterministic customer service sandbox. No production mutations."""
from dataclasses import asdict, dataclass, replace
import json
import math
from pathlib import Path


@dataclass(frozen=True)
class Config:
    tenant_filter: bool = False
    current_only: bool = False
    timeout_ms: int = 100
    retries: int = 0


CASES = json.loads((Path(__file__).parent / 'cases.json').read_text())
ALLOWED = {'tenant_filter', 'current_only', 'timeout_ms', 'retries'}


def patch(config, changes):
    if set(changes) - ALLOWED:
        raise ValueError('Only allowlisted configuration changes are supported')
    data = {**asdict(config), **changes}
    if any(type(data[k]) is not bool for k in ('tenant_filter', 'current_only')):
        raise ValueError('Filters must be booleans')
    if any(type(data[k]) is not int for k in ('timeout_ms', 'retries')):
        raise ValueError('Timeout and retries must be integers')
    if not 50 <= data['timeout_ms'] <= 1000 or not 0 <= data['retries'] <= 2:
        raise ValueError('Configuration exceeds sandbox bounds')
    return replace(config, **changes)


def replay(config, cases=CASES):
    """Replay explicit synthetic faults; latency is simulated, not wall-clock."""
    results = []
    for case in cases:
        elapsed = case['latency_ms']
        attempts = 1 + min(config.retries, case['transient_failures'])
        ok = elapsed <= config.timeout_ms and config.retries >= case['transient_failures']
        isolated = config.tenant_filter or not case['cross_tenant_decoy']
        current = config.current_only or not case['stale_decoy']
        results.append({'id': case['id'], 'correct': ok and isolated and current,
                        'isolated': isolated, 'available': ok,
                        'latency_ms': min(elapsed, config.timeout_ms) * attempts})
    times = sorted(r['latency_ms'] for r in results)
    n = len(results)
    if not n:
        raise ValueError('Evaluation requires at least one case')
    return {'accuracy': sum(r['correct'] for r in results) / n,
            'isolation': sum(r['isolated'] for r in results) / n,
            'availability': sum(r['available'] for r in results) / n,
            'p95_ms': times[math.ceil(n * .95) - 1], 'cases': results}


def review(before, after):
    failures = []
    for key in ('accuracy', 'isolation', 'availability'):
        if after[key] < 1:
            failures.append(f'{key} must reach 1.0 on the synthetic acceptance suite')
        if after[key] < before[key]:
            failures.append(f'{key} regressed')
    if after['p95_ms'] > 700:
        failures.append('p95 exceeds the customer 700 ms budget')
    return {'approved': not failures, 'feedback': failures}


def fixture_run():
    """Scripted baseline demonstrating the repair/review contract, not LLM inference."""
    initial = Config()
    before = replay(initial)
    candidate = patch(initial, {'tenant_filter': True, 'current_only': True})
    first_review = review(before, replay(candidate))
    candidate = patch(candidate, {'timeout_ms': 300, 'retries': 1})
    after = replay(candidate)
    return {'mode': 'offline-scripted', 'before': before, 'after': after,
            'first_review': first_review, 'review': review(before, after),
            'config': asdict(candidate), 'production_deployed': False}
