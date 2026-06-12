# ADR-003: Regression Testing and Gatekeeping Strategy

## Status
Accepted

## Context
Prompt engineering is highly iterative. Small changes to system prompts can fix specific edge cases but inadvertently degrade performance on other queries, a phenomenon known as prompt drift. To prevent silent regressions, we must run automated quality evaluations. However, evaluating the full dataset of 150 questions on every commit takes too long and is too expensive to run on a CI server (e.g., GitHub Actions).

## Alternatives Considered
1.  **Run Full Evaluation on Every PR**: High coverage but incurs high token cost and takes several minutes to complete, slowing down development cycles.
2.  **No Automated Regression Tests**: Low cost but relies on manual testing, making it highly probable that quality regressions slip into the main branch.
3.  **Critical Cases Subset Regression Testing (Selected)**: Run full evaluations manually or on a schedule, but enforce a fast, low-cost critical case subset evaluation as a gatekeeper during code changes and pull requests.

## Decision
We implement a multi-stage testing strategy:
1.  **Fast Unit Tests**: Test pure calculation helper functions (MRR, nDCG, chunk merging) without LLM/API dependencies. These run instantly on every commit.
2.  **Critical Cases Subset (Integration Regression Test)**: Select a representative subset of 7 questions (`CRITICAL_CASE_INDICES`) spanning all categories. The regression test suite evaluates this subset, compares results against stored baseline snapshot JSONs, and asserts that scores do not regress by more than `5%`.
3.  **CI/CD Integration**: The subset regression test is decorated with `@pytest.mark.integration`. In the CI pipeline, we default to running only unit tests (`pytest -m "not integration"`) to prevent credential leakage and control costs. Developers can execute integration regression tests locally or in secure CI environments using the `integration` marker.

## Consequences
*   Protects codebase from prompt drift and regression with minimal API expenditure.
*   Enforces engineering discipline by failing tests automatically when system performance degrades.
*   Requires a baseline snapshot JSON to be generated beforehand (`baseline.py save`) to serve as the comparison ground truth.
