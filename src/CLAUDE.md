# Backend Source

## Agent Implementation Pattern
Every agent follows this structure:
1. Inherit from `BaseAgent` (src/agents/base_agent.py)
2. Implement `execute(input: AgentInput) -> AgentOutput`
3. Implement `validate_input()` and `validate_output()`
4. Define quality gate criteria as class constants
5. Use structured logging for all operations

## Pipeline Order (DO NOT CHANGE)
Ingestion → Generation → Quality → WeakDetection → Tailoring → [Interview parallel]

## RAG Pattern
All generation agents MUST:
1. Call retriever.retrieve(query, top_k) FIRST
2. Include retrieved context in LLM prompt
3. Verify output against retrieved sources
4. Never generate from parametric memory alone

## Error Handling
- Use custom exception hierarchy from src/exceptions.py
- Agents catch and wrap errors in AgentError with context
- API routes return structured error responses via error middleware
