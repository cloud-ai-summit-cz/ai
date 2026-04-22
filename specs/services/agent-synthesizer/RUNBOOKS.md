# Service Runbooks: agent-synthesizer

## Common Issues

### Incomplete Synthesis
- Check scratchpad has all sections populated
- Re-run prerequisite agents if needed

### Agent Not Responding
- Re-provision: `uv run python -m agents.provision create`
