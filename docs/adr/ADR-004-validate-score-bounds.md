# ADR-004: Reject Out-of-Range Risk Scores at Load Time

## Decision

Validate risk scores in [0.0, 1.0] explicitly rather than silently clamping invalid inputs.
