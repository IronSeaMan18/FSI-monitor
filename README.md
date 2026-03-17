# Agent System Documentation

**Version:** 1.0.0
**Created:** 2026-03-04
**Location:** `~/agents/`

---

## Overview

This is a comprehensive agent management system for Claude Code, designed to create, organize, and deploy AI agents, sub-agents, and skills that enhance your development workflow.

### What This System Does

- **Creates** custom AI agents through guided interviews
- **Organizes** agents in a structured, interconnectable ecosystem
- **Validates** agent logic and dependencies
- **Deploys** skills directly to Claude Code
- **Manages** agent versions and updates

---

## Quick Start

### Creating Your First Agent

Simply say:
```
Jarvis, let's create an agent
```

The Master of Agents will interview you and create a production-ready agent.

### Viewing Existing Agents

```bash
ls ~/agents/agents/      # See all agents
ls ~/agents/sub-agents/  # See all sub-agents
ls ~/agents/skills/      # See all skills
```

---

## Directory Structure

```
~/agents/
├── agents/              # Main agents (autonomous, goal-oriented)
│   └── *.md            # Each agent in its own file
│
├── sub-agents/          # Sub-agents (helpers for main agents)
│   └── *.md            # Each sub-agent in its own file
│
├── skills/              # Skills (slash commands for users)
│   └── *.md            # Each skill in its own file
│
├── templates/           # Templates for creating new entities
│   ├── agent-template.md
│   ├── sub-agent-template.md
│   └── skill-template.md
│
├── MASTER_OF_AGENTS.md  # The architect that creates agents
├── CATEGORIES.md        # Category definitions and standards
└── README.md           # This file
```

---

## Agent Types

### 1. Agents (`~/agents/agents/`)

**Purpose:** Autonomous entities that accomplish complete goals

**Characteristics:**
- Self-contained with clear objectives
- Can orchestrate sub-agents
- User-facing trigger phrases
- 0-to-hero execution capability

**Categories:**
- **Research:** Gather and analyze information
- **Action:** Execute operations and modifications
- **Orchestrator:** Coordinate complex workflows
- **Domain-Specific:** Specialized expertise (frontend, backend, DevOps, etc.)

**Example:**
```
Agent: CodeArcheologist
Trigger: "analyze the codebase architecture"
Purpose: Deep dive into project structure, patterns, and dependencies
```

---

### 2. Sub-Agents (`~/agents/sub-agents/`)

**Purpose:** Specialized helpers that support main agents

**Characteristics:**
- Called by parent agents, not directly by users
- Focused on specific sub-tasks
- Return structured results
- Input/output contracts

**Categories:**
- **Specialized:** Handle specific sub-tasks
- **Helper:** Provide utility functions
- **Validator:** Verify conditions and data

**Example:**
```
Sub-Agent: dependency-resolver-sub
Parent: Project Bootstrapper
Purpose: Resolve and install npm/pip/cargo dependencies
```

---

### 3. Skills (`~/agents/skills/`)

**Purpose:** Slash commands for quick, focused tasks

**Characteristics:**
- Invoked with `/command-name`
- Accept arguments
- Quick execution
- User-friendly

**Categories:**
- **Utility:** Common operations
- **Automation:** Repetitive tasks
- **Workflow:** Multi-step processes

**Example:**
```
Skill: /scaffold-component
Usage: /scaffold-component MyComponent --type react
Purpose: Generate boilerplate for new components
```

---

## Schema Standards

### Agent File Structure

Every agent file contains:

1. **Metadata**
   - Name, version, category, dates

2. **System Prompt**
   - Comprehensive prompt defining behavior

3. **Trigger Phrases**
   - How users invoke the agent

4. **Tool Requirements**
   - Required and optional tools/MCPs

5. **Dependencies**
   - Other agents, sub-agents, services

6. **Interconnections**
   - What it calls, what calls it

7. **Capabilities**
   - Core functions and limitations

8. **Usage Examples**
   - Real-world scenarios

9. **Execution Flow**
   - Step-by-step workflow

10. **Testing**
    - Test cases and validation

11. **Change Log**
    - Version history

---

## Master of Agents

The Master of Agents is your professional AI architect for creating new agents.

### Trigger Phrases

- `Jarvis, let's create an agent`
- `Jarvis, let's create a sub-agent`
- `Jarvis, let's create a skill`

### The Interview Process

When you trigger the Master, it conducts a comprehensive interview:

1. **Intent Discovery** - What should it do?
2. **Motivation Analysis** - Why do you need it?
3. **Operational Design** - How should it operate?
4. **Technical Requirements** - What tools are needed?
5. **Integration & Context** - How does it connect?
6. **Quality & Testing** - How do we validate it?
7. **Additional Details** - Anything else?

### The Creation Process

After the interview:

1. **Design** - Architect the solution
2. **Validate** - Check logic and dependencies
3. **Create** - Generate the complete MD file
4. **Verify** - Test 0-to-hero execution
5. **Store** - Save to appropriate location
6. **Report** - Explain usage to you

---

## Naming Conventions

### Agents
- **Format:** PascalCase or kebab-case
- **Pattern:** `[Domain/Action] [Noun]`
- **Examples:**
  - `CodeArcheologist.md` or `code-archeologist.md`
  - `APIExplorer.md` or `api-explorer.md`

### Sub-Agents
- **Format:** kebab-case with `-sub` suffix
- **Pattern:** `[function]-[noun]-sub.md`
- **Examples:**
  - `dependency-resolver-sub.md`
  - `schema-validator-sub.md`

### Skills
- **Format:** kebab-case
- **Pattern:** `[action]-[object].md`
- **Examples:**
  - `scaffold-component.md` → `/scaffold-component`
  - `auto-commit.md` → `/auto-commit`

---

## Integration with Claude Code

### Skills Integration

Skills can be directly integrated into Claude Code:

```bash
# Copy skill to Claude Code
cp ~/agents/skills/[skill-name].md ~/.claude/skills/

# Reload skills (restart Claude Code or reload window)
```

### Using Agents in Cursor/Antigravity

Agents work automatically when their trigger phrases are used in conversations.

---

## Versioning

### Version Format
`MAJOR.MINOR.PATCH`

- **MAJOR:** Breaking changes
- **MINOR:** New features, backward compatible
- **PATCH:** Bug fixes, minor improvements

### Updating Agents

To update an existing agent:
```
Jarvis, update [agent-name]
```

The Master will:
1. Read current version
2. Ask what needs to change
3. Increment version appropriately
4. Update change log
5. Rewrite file

---

## Categories

Detailed category definitions in: `~/agents/CATEGORIES.md`

### Quick Reference

| Category | Purpose | Complexity | Examples |
|----------|---------|------------|----------|
| Research | Information gathering | Medium | Code analysis, doc search |
| Action | Execute operations | Low-Medium | File ops, git commands |
| Orchestrator | Coordinate workflows | High | Full deployment, project setup |
| Domain-Specific | Specialized expertise | Medium-High | React dev, API design |

---

## Best Practices

### Creating Agents

1. **Start with Intent** - Be clear about the goal
2. **Check Existing** - Don't duplicate functionality
3. **Define Scope** - Keep agents focused
4. **Plan Dependencies** - Map interconnections upfront
5. **Include Examples** - Real usage scenarios
6. **Write Tests** - Validation criteria

### Maintaining Agents

1. **Version Everything** - Track changes
2. **Update Change Logs** - Document modifications
3. **Test After Updates** - Verify functionality
4. **Review Dependencies** - Keep them current
5. **Archive Obsolete** - Don't delete, move to archive/

### Interconnecting Agents

1. **Define Contracts** - Clear input/output
2. **Handle Failures** - Graceful degradation
3. **Avoid Circular** - No circular dependencies
4. **Document Flow** - Show data movement
5. **Test Integration** - Validate connections

---

## Examples

### Example Agent: Git Commander

```markdown
# Agent Name: Git Commander

**Category:** Action
**Trigger:** "handle git [operation]"

## System Prompt
Expert git agent that handles all git operations including commits,
branches, merges, and repository management.

## Tool Requirements
- Bash (for git commands)
- Read (for checking files)
- gh CLI (for GitHub operations)

## Usage Example
User: "handle git commit for these changes"
Agent: [Reviews changes] → [Crafts commit message] → [Creates commit]
```

### Example Sub-Agent: Dependency Resolver

```markdown
# Sub-Agent Name: dependency-resolver-sub

**Parent:** Project Bootstrapper
**Purpose:** Detect and install project dependencies

## Input
{
  "project_path": "/path/to/project",
  "package_manager": "npm|pip|cargo"
}

## Output
{
  "installed": ["package1", "package2"],
  "status": "success"
}
```

### Example Skill: Scaffold Component

```markdown
# Skill Name: scaffold-component

**Slash Command:** `/scaffold-component`

## Arguments
/scaffold-component <name> --type <react|vue|angular>

## Usage
User: /scaffold-component Button --type react
Skill: Creates Button.tsx, Button.module.css, Button.test.tsx
```

---

## Troubleshooting

### Agent Not Responding

1. Check trigger phrase matches exactly
2. Verify dependencies are installed
3. Review system prompt for clarity
4. Check file permissions

### Interconnection Issues

1. Verify dependent agents exist
2. Check for circular dependencies
3. Validate data contracts match
4. Review execution flow

### Skill Not Available

1. Ensure copied to `~/.claude/skills/`
2. Restart Claude Code
3. Check naming convention
4. Verify file format

---

## Advanced Topics

### Creating Orchestrator Agents

Orchestrators coordinate multiple agents:

```markdown
1. Break down user goal into sub-tasks
2. Identify which agents handle each task
3. Call agents in correct sequence
4. Handle inter-agent data passing
5. Aggregate results
6. Report final outcome
```

### Agent Communication

Agents can pass data through:
- Return values
- Temporary files
- Shared context
- Message passing

### Error Handling

All agents should:
- Validate inputs
- Handle missing dependencies gracefully
- Provide clear error messages
- Suggest recovery actions
- Log issues for debugging

---

## Roadmap

### Planned Features

- [ ] Agent registry with search
- [ ] Dependency graph visualization
- [ ] Automated testing framework
- [ ] Version conflict resolution
- [ ] Agent marketplace/sharing
- [ ] Performance metrics
- [ ] Hot reload for updates

---

## Contributing

To add to this system:

1. Use Master of Agents for creation
2. Follow naming conventions
3. Complete all template sections
4. Test thoroughly
5. Update this README if needed

---

## Resources

- **Templates:** `~/agents/templates/`
- **Categories:** `~/agents/CATEGORIES.md`
- **Master Agent:** `~/agents/MASTER_OF_AGENTS.md`
- **Claude Code Docs:** https://docs.claude.com/claude-code

---

## Support

For issues or questions:
1. Review this README
2. Check CATEGORIES.md for standards
3. Consult MASTER_OF_AGENTS.md for creation process
4. Ask "Jarvis, help with agents"

---

**System Status:** ✓ Active
**Total Agents:** [Run `ls ~/agents/agents/ | wc -l`]
**Total Sub-Agents:** [Run `ls ~/agents/sub-agents/ | wc -l`]
**Total Skills:** [Run `ls ~/agents/skills/ | wc -l`]

---

Last Updated: 2026-03-04
Version: 1.0.0
