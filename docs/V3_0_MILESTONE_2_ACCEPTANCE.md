# Milestone 2 acceptance checklist

- [ ] Initialize from a valid JSON brief.
- [ ] Reject missing app name and existing workspace.
- [ ] Persist state after every transition and resume after a new process.
- [ ] Generate a focused prompt for the next pending task.
- [ ] Enforce explicit approval gates for architecture, integrations and release preparation.
- [ ] Require evidence when marking a task completed.
- [ ] Pause blocks new task prompts; resume restores workflow.
- [ ] No automatic Claude calls, arbitrary shell execution, app source generation or publishing.
- [ ] Tests cover the main happy paths and safety boundaries.
