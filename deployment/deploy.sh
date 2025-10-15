#!/bin/bash
set -e

echo "🚀 Hospital Schedule Agent - AgentCore Deployment"
echo "=================================================="
echo ""

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is required but not installed"
    exit 1
fi

if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials not configured. Run 'aws configure'"
    exit 1
fi

echo "✅ Prerequisites met"
echo ""

# Prepare deployment files
echo "📦 Preparing deployment files..."
cd ..
uv run python -c "
import shutil
import os

# Copy schedule_agent module
if os.path.exists('deployment/schedule_agent'):
    shutil.rmtree('deployment/schedule_agent')
shutil.copytree('schedule_agent', 'deployment/schedule_agent')
print('✅ Copied schedule_agent module')
"
cd deployment

# Check if already configured
if [ -f ".bedrock_agentcore.yaml" ]; then
    echo "⚠️  Agent already configured. Skipping configuration."
    echo "   To reconfigure, delete .bedrock_agentcore.yaml and run again."
    echo ""
else
    echo "⚙️  Configuring agent..."
    uv run agentcore configure -e invoke.py --name schedule_agent
    echo "✅ Agent configured"
    echo ""
fi

# Deploy
echo "🚢 Deploying to AgentCore..."
uv run agentcore launch

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📊 Check status:"
echo "   uv run agentcore status --agent schedule_agent"
echo ""
echo "🧪 Test the agent:"
echo "   uv run agentcore invoke '{\"prompt\": \"Hello, can you help me?\"}' --agent schedule_agent"
echo ""
echo "📝 View logs:"
echo "   uv run agentcore status --agent schedule_agent  # Copy the log command from output"
echo ""
