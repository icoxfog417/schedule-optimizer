# Hospital Schedule Agent - AgentCore Deployment

## Quick Start

### Prerequisites

1. AWS Account with Bedrock access
2. AWS CLI configured (`aws configure`)
3. Python 3.11+ and uv installed
4. Bedrock model access enabled for Claude 3.7 Sonnet

### Deploy

```bash
./deploy.sh
```

### Test

```bash
uv run agentcore invoke '{"prompt": "What can you help me with?"}' --agent schedule-agent
```

### Monitor

```bash
uv run agentcore status --agent schedule-agent
```

### Cleanup

```bash
uv run agentcore destroy --agent schedule-agent
```

## Documentation

See full documentation in `.workspace/08_deployment_guide.md`
