from typing import List, Optional, Dict

def generate_test_stubs(story_id: str, acceptance_criteria: Optional[List[str]] = None) -> List[Dict]:
    tests: List[Dict] = []
    if acceptance_criteria:
        for i, ac in enumerate(acceptance_criteria, start=1):
            tests.append({"name": f"{story_id}-AC-{i}", "description": ac})
    else:
        tests.append({"name": f"{story_id}-basic", "description": "Basic acceptance test"})
    return tests
