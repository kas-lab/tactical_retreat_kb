# Agent Notes

This file is a short checklist for agents working in this repo.

## Quick test entrypoint

Preferred focused run (hypothetical fulfillment tests) inside Docker:

```bash
scripts/run-tests-docker.sh -k test_hyp
```

## Common failure checks

- Is TypeDB running on `localhost:1729`?
- Is the ROS + workspace environment sourced?
- Is the `tactical_retreat` container running (if using Docker)?

## Rule authoring reminders

- Avoid negation cycles: do not read/write the same predicate under `not {}`.
- Variables in `then` must be bound in `when` outside nested blocks.
- If you need to assign attributes to a relation, bind or create the relation first.
