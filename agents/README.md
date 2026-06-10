# Agents

This directory contains **operational prompts** for AI agents that work
on this repository. Each file is a self-contained brief you can hand
to a fresh AI session (or pass to a sub-agent spawn) to give it a
defined role in the repo.

The **contract** for each role — what it must do, what it must not,
how it should behave — lives in [`../AGENTS.md`](../AGENTS.md). The
files in this directory are the operational layer: identity, checklist,
output format, spawn template.

## Available agents

| File | Role | Contract section |
|---|---|---|
| [`cataloger.md`](cataloger.md) | Cataloger — catalog rows, dataset folders, provenance | `AGENTS.md` § "Cataloger role" |
| [`analyst.md`](analyst.md) | Analyst — produce an analysis: data + viz + writeup | `AGENTS.md` § "Analyst role" |
| [`reviewer.md`](reviewer.md) | Reviewer — methodology and robustness review of analyses | `AGENTS.md` § "Reviewer role" |

All three roles are operational. Pick the file matching the work to
be done, hand it (or its contents) to a sub-agent spawn or a fresh
chat session, and the agent will have a defined identity, checklist,
and output format.

## How to use

### Spawn a Reviewer sub-session
Hand it the contents of `reviewer.md` as the system/task prompt, plus
the path or PR to review. The agent will:
1. Read the relevant dataset + analysis files
2. Run through the methodology/robustness/viz/reproducibility checklist
3. Produce a structured review with verdict

### Spawn a Cataloger sub-session
Hand it the contents of `cataloger.md` plus the upstream URL or the
existing CSV row to act on. The agent will gather the input
checklist, write the catalog row + folder + provenance, and open a PR.

### Spawn an Analyst sub-session
Hand it the contents of `analyst.md` plus the dataset slug and the
question or angle. The agent will read the dataset, write the analysis
script + figure + README, and open a PR.

### Use the contract directly
If you're already in a session and want to act as a Reviewer, just
read `AGENTS.md` § "Reviewer role" and follow the contract. The
operational file is for *spawning* a new agent; the contract is for
*being* one.

## Adding a new agent

1. Write the operational prompt in this directory: identity, principles,
   what to do when invoked, checklist, output format, spawn template,
   what it doesn't do.
2. Add a contract section to `../AGENTS.md` (Job, Inputs, Output,
   Self-checks).
3. Update the table in this README.
4. The two files should not drift. If they do, the operational file
   wins (it's what the agent actually does).

## Anti-patterns

- **Don't create one agent per task.** Roles are behavioral patterns,
  not microservices. If you're spawning a new agent for every PR,
  something is off.
- **Don't let agents edit their own contracts.** `AGENTS.md` and
  `agents/*.md` are reviewed like code. An agent can *propose* changes
  in a PR; humans (or the maintainer) merge.
- **Don't conflate the role with the model.** A role can be played
  by any model that can read and follow the spec. Don't hardcode
  "Claude" or "GPT-4" anywhere in this directory.
