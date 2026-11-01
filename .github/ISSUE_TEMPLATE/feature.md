---
name: Feature
about: New functionality, specified with a user story, Gherkin scenarios and EARS requirements
title: ""
labels: feature
---

## User story

As a … I want … so that …

## Acceptance criteria (Gherkin)

<!-- One scenario per behaviour. Cover the edge cases that apply: missing values (null),
     Swedish number format (sv-SE), a currency change, empty data. -->

```gherkin
Feature: …

  Scenario: …
    Given …
    When …
    Then …
```

## Requirements (EARS)

<!-- Numbered REQ-<issue>-<k>. Each one is testable and maps to at least one scenario. -->

- REQ-<issue>-1: The system shall …
- REQ-<issue>-2: When …, the system shall …

## Notes
