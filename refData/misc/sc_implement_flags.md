Let me search for information about superclaude and its implement command.Let me get the detailed flags documentation.The GitHub page didn't render the markdown content. Let me try the raw URL.Based on the search results and documentation, here are the flags that can be used with `/sc:implement`:

**MCP / Tool Flags:**
- `--c7` — Use Context7 MCP for official documentation lookup
- `--magic` — Use Magic MCP for UI components
- `--all-mcp` — Enable all available MCP servers
- `--no-mcp` — Native execution only, no MCP tools

**Thinking / Reasoning Flags:**
- `--think` — Extended reasoning mode
- `--ultrathink` — Maximum depth reasoning
- `--seq` — Use Sequential MCP for token-efficient reasoning

**Safety / Validation Flags:**
- `--safe-mode` — Extra safety checks
- `--safe` — Safe execution mode
- `--validate` — Post-implementation validation
- `--interactive` — Interactive confirmation for changes

**Quality / Style Flags:**
- `--morph` — Use Morphllm MCP for code transformation
- `--play` — Use Playwright MCP for browser testing

**Persona Flags (universal, work with any command):**
- `--frontend` — Frontend specialist persona
- `--backend` — Backend specialist persona
- `--architect` — Architecture-focused approach
- `--security` — Security-focused implementation
- `--performance` — Performance-focused implementation

**Example usage:**
```
/sc:implement "responsive dashboard" --magic --c7
/sc:implement "React 18 application with TypeScript" --c7
/sc:implement fix --validate
```

Note: SuperClaude v4.x flags are mostly behavioral hints that Claude Code reads from context files. You can also run `/sc:implement --help` in Claude Code to see the currently available flags for your installed version.