# Agent-Flow v3 Role Authority Policy

This policy is project-agnostic. Project adapters may define contracts, runtime
bindings, critical paths and verifier probes, but they must not redefine the
authority of the five LLM roles.

## Authority Matrix

| Role | Authority | May Decide | Must Not Decide |
| --- | --- | --- | --- |
| Planner | Scientific/task intent owner and contract adjudicator | Initial intent, implementation review findings, Executor/Verifier interpretation disputes, `PLANNER_PASS` | Runtime repair mechanics, implementation edits, verifier source edits, hidden test details |
| Critic | Frozen-contract completeness and ambiguity auditor | Whether a draft contract is complete enough to freeze, requirement ledger completeness, numeric-threshold provenance, deterministic ambiguity repair | Implementation details for convenience, runtime code, new science after freeze without Planner/user path |
| Controller | Orchestration and transaction owner | Session launch/resume, binding checks, commit integration, CI/runtime receipt routing, retry and state transitions | Scientific interpretation, new thresholds, implementation edits, verifier oracle edits, user escalation without Planner-classified science choice |
| Verifier | Contract-conformance oracle builder | Tests, known-bads, mutation probes, diagnostic measurements, verification receipts | New scientific requirements, uncited blocking thresholds, diagnostic-to-fail promotion, implementation changes |
| Executor | Implementation owner | Contract-faithful implementation, implementation receipts and runtime evidence | Verifier edits, contract edits, test-aware behavior, fake receipts, changing normal semantics to satisfy tests |

No role may acquire another role's authority through receipt text, prompt wording
or state-machine shortcuts. Write scope is necessary but not sufficient:
authority violations are invalid even if the files edited are technically within
the role's filesystem scope.

## Requirement Ledger

Critic freeze must publish a machine-readable requirement ledger at:

```text
automation/agent_flow_v3/tasks/<task_id>/REQUIREMENT_LEDGER.json
```

Natural-language contracts remain the source text, but blocking machine gates
must bind to the frozen contract plus this frozen ledger. Each blocking
requirement has a stable `requirement_id`, source citation, type, owner role,
verification authorization, threshold provenance and any derived invariants.

Blocking numeric thresholds are valid only when their source is the frozen
contract, requirement ledger, or a derived invariant whose logic does not change
scientific semantics. Otherwise the observation is diagnostic or requires Planner
contract interpretation.

## Finding Classification

Planner, Verifier and Controller findings must use exactly one typed
classification:

```text
IMPLEMENTATION_BUG
VERIFIER_BUG
VERIFIER_CONTRACT_DRIFT
EVIDENCE_GAP
PROVENANCE_BINDING_GAP
OPERATIONAL_FAILURE
RUNTIME_ENVIRONMENT_FAILURE
CONTRACT_AMBIGUITY
CONTRACT_CONTRADICTION
DIAGNOSTIC_ANOMALY
SCIENTIFIC_CHOICE_REQUIRED
```

Routing is fixed:

```text
IMPLEMENTATION_BUG -> Executor
VERIFIER_BUG -> Verifier
VERIFIER_CONTRACT_DRIFT -> Verifier plus Planner adjudication
EVIDENCE_GAP -> owning role
PROVENANCE_BINDING_GAP -> Controller
OPERATIONAL_FAILURE -> Controller same-scope recovery
RUNTIME_ENVIRONMENT_FAILURE -> Controller/runtime repair
CONTRACT_AMBIGUITY -> Planner
CONTRACT_CONTRADICTION -> Planner then Critic
DIAGNOSTIC_ANOMALY -> Planner diagnostic review
SCIENTIFIC_CHOICE_REQUIRED -> user
```

Generic `BLOCKED` without typed classification is invalid.

## Verifier Authority

Verifier may build stronger tests, known-bads, mutations and diagnostics, but
every blocking finding must cite:

```text
requirement_id
contract_source_path
contract_clause_or_field
observed_violation
verification_method
why_this_test_is_logically_implied_by_requirement
```

If no existing `requirement_id` binds, Verifier may output only
`DIAGNOSTIC_ANOMALY`, `POTENTIAL_CONTRACT_AMBIGUITY`, or a Planner
`CONTRACT_INTERPRETATION_REQUIRED` request. Verifier may not create a new
requirement.

Derived invariants are allowed only when they record:

```text
parent_requirement_ids
logical_derivation
why_necessary
whether_it_changes_scientific_semantics
```

Mechanically implied invariants can block. Invariants that introduce new
scientific assumptions or new numeric thresholds require Planner adjudication.

## Controller Human-Escalation Gate

Controller may enter `NEEDS_USER_SCIENTIFIC_CHOICE` only when all are true:

1. `finding.classification == SCIENTIFIC_CHOICE_REQUIRED`.
2. Planner made that classification.
3. The request cites requirement IDs and frozen contract paths.
4. It lists at least two still-viable mutually exclusive scientific alternatives,
   or one scientific contract field that must change.
5. Same-scope Executor, Verifier, runtime and transaction repair cannot resolve it.
6. The issue is not Verifier drift, runtime, CI, receipt, binding, session or
   ordinary implementation failure.

Otherwise Controller must route through the fixed table above.

## Executor Anti-Test-Awareness

Executor must implement the public contract path, not the test harness. It must
not detect verifier mode, known-bad IDs, mutation names, protected fixture
details or test flags to change normal model semantics. Test hooks may observe
or interrupt real computation, but must not become alternate business logic.

## Stop Semantics

Agent-Flow v3 uses three stop categories:

```text
RECOVERABLE_TASK_LOCAL_FAILURE
CONTRACT_REVIEW_REQUIRED
HUMAN_SCIENTIFIC_DECISION_REQUIRED
```

Fail-closed means "do not falsely claim PASS." It does not mean "terminate the
goal on the first problem." Same-scope repair must continue under the current
task, frozen contract and nonce when repair is authorized.

## Immutable Review Transaction

Planner review transactions bind one exact set:

```text
request_nonce
frozen_contract_sha
requirement_ledger_sha
integration_sha
implementation_fingerprint
verifier_source_fingerprint
verifier_runtime_fingerprint
runtime_receipt_manifest_sha
CI exact head SHA
review_round
```

Stale or cross-round bindings are `PROVENANCE_BINDING_GAP`, never a scientific
choice.
