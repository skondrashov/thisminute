# Agent Protocol

How agents operate on thisminute.org. For project architecture and technical reference, see `AGENTS.md`.

## Startup

1. You will be told your name (e.g., "you are the builder")
2. **Understand your role**: Read your agent file (`agents/{your-name}.md`).
3. **Get current time**: Run `powershell -Command "Get-Date -Format 'yyyy-MM-dd HH:mm'"` and record the output. You MUST use this exact timestamp in all forum posts and reports. NEVER guess, approximate, or fabricate a timestamp — always use the value returned by this command.
4. **Understand the project**: Read `AGENTS.md` for architecture and key design decisions. Then read the reference docs listed in your role file (`ref/frontend.md`, `ref/backend.md`) — only the ones marked as relevant to your role.
5. **Check the forum**: Read `FORUM.md`:
    - What have other agents been working on?
    - Vote on proposals relevant to your role (+1 agree, -1 disagree)
    - You MUST vote on at least 3 posts every cycle before posting anything new
6. **Check messages**: Read `messages/{your-name}.md` if it exists. Handle any messages, then move them to `messages/archive/{your-name}.md`.
7. **Execute your tasks**: Follow the Tasks section of your agent file.
8. **Report findings**: Post to `FORUM.md` or save to `reports/{your-name}.md`.
9. **Update memory**: Add learnings to `memory/{your-name}.md`. Remove stale info.
10. **Shutdown reflection**: The orchestrator will ask you to evaluate each context layer: its spawn prompt, your role file, AGENTS.md, PROTOCOL.md, memory files, and forum/messages. Be specific and honest — flag wrong info, missing context, and noise. Your feedback directly improves what the next agent gets.
11. **Exit** (unless you're the orchestrator).

## Communication

**Where to put what:**

- **Forum** (`FORUM.md`): Proposals needing votes, findings, active discussions. Be concise.
- **Messages** (`messages/{agent}.md`): Specific requests to one agent. Be verbose.
- **Memory** (`memory/{agent}.md`): What you need to know to do your job. What you wish you knew.
- **Reports** (`reports/{agent}.md`): Routine updates, verification logs, archived history.
- **Human** (`messages/human.md`): Messages to the person running the project.

### Forum Voting

Every post has metadata: `**Author:** name | **Timestamp:** YYYY-MM-DD HH:MM | **Votes:** +N/-M`

- **+1**: Agree / Verified / Should prioritize
- **-1**: Disagree / Incorrect / Deprioritize
- To upvote: change `+N/-M` to `+N+1/-M`
- To downvote: change `+N/-M` to `+N/-M+1`

High-vote items (+3 or more) represent group consensus.

## Request Agent Spawn

If you think an agent needs to follow up on something, post to the forum or send a direct message to the orchestrator:

```
REQUEST SPAWN: [agent-name]
REASON: [reason]
```

## Key Guidelines

1. **Read before acting**: Understand `AGENTS.md`, your role file, relevant `ref/` docs, and `FORUM.md` before making changes
2. **Document learnings**: Add useful knowledge to your memory file
3. **Be specific**: Include file paths, line numbers, concrete details in forum posts
4. **Respect priorities**: Check forum votes to understand group consensus
5. **Don't modify CLAUDE.md**: Unless explicitly asked by a human user
6. **`flush=True`** on all prints in background tasks
7. **Avoid unicode** in print — cp1252 can't encode arrows/special chars on Windows
8. **Never fabricate history**: Only reference events/dates you can verify via git log or file timestamps. If you don't know when something happened, check `git log` — don't guess.
