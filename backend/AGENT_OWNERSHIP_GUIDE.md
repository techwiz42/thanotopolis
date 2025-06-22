# Agent Ownership Guide

## Overview

The Thanotopolis platform supports two types of agents:
1. **Free Agents**: Available to all organizations
2. **Proprietary Agents**: Available only to specific organizations

## Recent Updates

✅ **Multi-Organization Support Implemented**: Proprietary agents can now be shared across multiple organizations using the `OWNER_DOMAINS` list.

✅ **Demo Answering Service Agent Created**: Meet Barney, a specialized telephone answering agent for the demo organization with features including:
- **Personal Identity**: Introduces himself as "Barney from Cyberiad.ai"
- **Company Knowledge**: Knowledgeable about Cyberiad.ai and the agentic framework
- **Multi-language support**: Fluent in 12 languages with native identity preservation
- **Web search capabilities**: Can research information in real-time
- **Call tracking and summarization**: Remembers conversation points and provides summaries
- **Agent collaboration**: Can hand off to specialist agents when needed
- **Optimized for telephony**: Low-latency responses perfect for phone conversations

## Implementation

### Agent Definition

Agents are defined as Python classes that inherit from `BaseAgent`. The ownership is controlled by the `OWNER_DOMAINS` class attribute.

### OWNER_DOMAINS Attribute

The `OWNER_DOMAINS` attribute is a list of organization subdomains that have access to the agent:

- **Empty list `[]`**: The agent is free and available to all organizations
- **List with domains**: The agent is proprietary and only available to listed organizations
- **No attribute**: Defaults to `[]` (free agent) for backward compatibility

## Examples

### Free Agent
```python
from app.agents.base_agent import BaseAgent

class MyFreeAgent(BaseAgent):
    """Agent available to all organizations."""
    OWNER_DOMAINS = []  # Empty list = free agent
    
    def __init__(self, name="MY_FREE_AGENT"):
        instructions = "Your agent instructions here..."
        super().__init__(name=name, instructions=instructions)
```

### Single Organization Agent
```python
class MyProprietaryAgent(BaseAgent):
    """Agent available only to ACME organization."""
    OWNER_DOMAINS = ["acme"]  # Only 'acme' subdomain
    
    def __init__(self, name="MY_PROPRIETARY_AGENT"):
        instructions = "Your agent instructions here..."
        super().__init__(name=name, instructions=instructions)
```

### Multi-Organization Agent
```python
class MySharedAgent(BaseAgent):
    """Agent available to multiple organizations."""
    OWNER_DOMAINS = ["acme", "demo", "partner-org"]  # Multiple organizations
    
    def __init__(self, name="MY_SHARED_AGENT"):
        instructions = "Your agent instructions here..."
        super().__init__(name=name, instructions=instructions)
```

### Legacy Agent (Backward Compatible)
```python
class MyLegacyAgent(BaseAgent):
    """Legacy agent without OWNER_DOMAINS defaults to free agent."""
    # No OWNER_DOMAINS attribute - defaults to []
    
    def __init__(self, name="MY_LEGACY_AGENT"):
        instructions = "Your agent instructions here..."
        super().__init__(name=name, instructions=instructions)
```

## How It Works

1. When a user requests agents, the system checks their organization's subdomain
2. For each discovered agent, the system checks:
   - If `OWNER_DOMAINS = []`, the agent is included (free agent)
   - If `OWNER_DOMAINS` contains the user's subdomain, the agent is included
   - Otherwise, the agent is excluded

## Adding Organizations to Existing Agents

To grant additional organizations access to a proprietary agent, simply add their subdomain to the `OWNER_DOMAINS` list:

```python
# Before
OWNER_DOMAINS = ["acme"]

# After - now both acme and newcorp have access
OWNER_DOMAINS = ["acme", "newcorp"]
```

## Security Considerations

- If an agent has no `OWNER_DOMAINS` attribute, it defaults to being a free agent
- If `OWNER_DOMAINS` is not a list or is malformed, the agent is treated as unavailable for safety
- The system always fails closed - if ownership cannot be determined, access is denied

## Migration from Old System

The old system used:
- `IS_FREE_AGENT = True/False`
- `OWNER_DOMAIN = "single-org"`

The new system uses:
- `OWNER_DOMAINS = []` for free agents
- `OWNER_DOMAINS = ["org1", "org2", ...]` for proprietary agents

Simply replace the old attributes with the new `OWNER_DOMAINS` list format.