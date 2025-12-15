# Draw Steel Agents Documentation

This document describes the agent architecture and implementations in the Draw Steel project.

## Overview

The Draw Steel project uses AI agents to provide expert assistance for the Draw Steel tabletop RPG system. These agents leverage a knowledge base containing parsed content from the three main Draw Steel books: **Heroes**, **Monsters**, and **Delian Tomb**.

## Agent Architecture

The system uses the [AI Agents SDK](https://github.com/ai-agents/agents) framework and provides two main implementations:

### 1. Basic Agent (`draw_steel_expert.py`)

A simple factory function that creates standalone agent instances:

```python
from backend.agents.draw_steel_expert import create_draw_steel_expert

agent = create_draw_steel_expert(
    collection_name="draw_steel_heroes",
    model=GEMINI_FLASH_LITE_MODEL
)
```

**Features:**
- Single agent instance
- Basic database search functionality
- Simple API for quick integration

### 2. Advanced Agent Class (`draw_steel_expert_class.py`)

A more sophisticated class-based implementation with enhanced features:

```python
from backend.agents.draw_steel_expert_class import DrawSteelExpert

# Initialize expert
expert = DrawSteelExpert(collection_name="draw_steel_heroes")

# Run queries
result = await expert.run_agent("How does combat work in Draw Steel?")

# Streaming responses
async for chunk in expert.run_agent_streamed("Tell me about orcs"):
    print(chunk, end="")
```

**Features:**
- **Session Management**: Multiple concurrent chat sessions
- **Streaming Support**: Real-time response generation
- **Configurable Retrieval**: Adjust search parameters
- **Resource Management**: Context manager support
- **Persistence**: SQLite-backed session storage

## Core Components

### Database Integration

Agents connect to a Weaviate vector database containing:
- Game rules and mechanics
- Character creation guidelines
- Adventure content
- Setting information
- Game master advice

The database excludes structured data like monster stat blocks and character ability mechanics.

### Search Functionality

The primary tool available to agents is `search_text`:

```python
@function_tool
async def search_text(query: str) -> str:
    """Search the Draw Steel knowledge base.
    
    Uses hybrid search (semantic + keyword) to find relevant information.
    Returns JSON-formatted results with context and metadata.
    """
```

**Search Parameters:**
- `top_k`: Number of results to return (default: 5)
- `hybrid_alpha`: Balance between semantic and keyword search (default: 0.5)

### Session Management

The `DrawSteelExpert` class supports multiple sessions:

```python
# Create a new session
session_id = expert.create_session()

# List all sessions
sessions = expert.list_sessions()

# Use a specific session
result = await expert.run_agent("Query", session_id=session_id)
```

## Agent Capabilities

### Knowledge Domains

Agents have expertise in:

1. **Game Rules**: Combat, negotiation, downtime, recoveries
2. **Character Creation**: Ancestries, cultures, careers, classes, kits
3. **Setting Information**: Orden, the Timescape, gods and religion
4. **Adventure Content**: Delian Tomb adventure modules
5. **Game Master Support**: Encounter building, monster hierarchies, dynamic terrain

### Example Use Cases

```python
# Rule explanations
agent.run_agent("How does the Power Roll system work?")

# Character creation help
agent.run_agent("What are the differences between High Elves and Wode Elves?")

# Adventure guidance
agent.run_agent("What challenges await in Part 2 of Delian Tomb?")

# Game master assistance
agent.run_agent("How should I balance an encounter with giants?")
```

## Configuration

### Retrieval Configuration

```python
from backend.agents.draw_steel_expert_class import RetrievalConfig

config = RetrievalConfig(
    collection_name="draw_steel_monsters",
    model=GEMINI_FLASH_LITE_MODEL,
    top_k=10,  # Return more results
    hybrid_alpha=0.7,  # More semantic, less keyword
    max_calls_per_query=15
)

expert = DrawSteelExpert(collection_name="draw_steel_monsters")
expert.update_retrieval_config(config)
```

### Model Selection

Agents use LiteLLM models. The default is `GEMINI_FLASH_LITE_MODEL`, but can be configured:

```python
from backend.utils.agent_models import GEMINI_FLASH_LITE_MODEL, CLAUDE_MODEL

# Use a different model
expert = DrawSteelExpert(
    collection_name="draw_steel_heroes",
    model=CLAUDE_MODEL
)
```

## Integration with Frontend

The agents are designed to work with the Textual-based chat interfaces:

- `frontend/textual/fugly_chat.py` - Main chat interface
- `frontend/textual/new_chat.py` - Newer UI implementation

Example integration:

```python
# In a Textual app
async def handle_query(query: str):
    expert = DrawSteelExpert(collection_name="draw_steel_heroes")
    
    # Stream responses to UI
    async for chunk in expert.run_agent_streamed(query):
        update_chat_display(chunk)
```

## Development Notes

### TODO Items

- Implement chunk deduplication in chat history
- Add adjacent chunk retrieval for better context
- Improve session management API
- Enhance error handling and recovery

### Best Practices

1. **Resource Management**: Use context managers
   ```python
   with DrawSteelExpert(collection_name="heroes") as expert:
       # Use expert
       pass
   ```

2. **Session Cleanup**: Manage session lifecycle
   ```python
   session_id = expert.create_session()
   try:
       # Use session
       pass
   finally:
       # Cleanup if needed
       pass
   ```

3. **Error Handling**: Wrap agent calls in try-catch
   ```python
   try:
       result = await expert.run_agent(query)
   except Exception as e:
       handle_error(e)
   ```

## Files Reference

- `backend/agents/__init__.py` - Agent initialization and configuration
- `backend/agents/draw_steel_expert.py` - Basic agent factory
- `backend/agents/draw_steel_expert_class.py` - Advanced agent class
- `backend/agents/prompts/` - Agent prompt templates
- `backend/database/` - Database integration
- `backend/utils/agent_models.py` - Model configurations

## Getting Started

To use the agents in your application:

```python
from backend.agents.draw_steel_expert_class import DrawSteelExpert

async def main():
    # Initialize expert for Heroes content
    expert = DrawSteelExpert(collection_name="draw_steel_heroes")
    
    # Ask a question
    result = await expert.run_agent("What are the core character attributes?")
    print(result.output)
    
    # Clean up
    expert.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

## Support

For issues or questions about the agent system:

1. Check existing issues in the repository
2. Review the TODO items in the agent files
3. Consult the Draw Steel rulebooks for domain knowledge
4. Examine the database schema for understanding data structure
