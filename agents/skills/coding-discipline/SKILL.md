---
name: coding-discipline
description: Code quality defaults extracted from Claude Code's system prompt. Builder agents that touch app code should reference this skill so they don't lose CC's editing/communication discipline when their system prompt is replaced with a custom role file.
---

# Coding Discipline

You are writing or modifying code. Apply these defaults regardless of what the parent task framing emphasizes.

## File operations

Use the dedicated tools, not Bash text-munging:

- **Search file contents** — Grep (not `grep`/`rg`/`Select-String`)
- **Find files by name/pattern** — Glob (not `find`/`ls -R`/`Get-ChildItem -Recurse`)
- **Read files** — Read (not `cat`/`head`/`tail`/`Get-Content`)
- **Edit existing files** — Edit (not `sed`/`awk`/in-place rewrites). Read the file at least once first.
- **Create or fully rewrite a file** — Write (not `echo >`/`cat <<EOF`/`Out-File`)

Bash/PowerShell stays for actual shell work: running build commands, git, package managers, tests.

## Comments

Default to no comments. Code should be self-documenting through naming and structure. Add a comment only when the WHY is non-obvious — odd workarounds, surprising constraints, references to external specs. Never add a comment that restates what the code does.

## Scope

Do exactly what was asked. Don't:

- Add unrequested abstractions, factories, config systems, or "future-proofing"
- Add error handling for impossible scenarios just to feel thorough
- Refactor adjacent code that's working
- Add new features the user didn't ask for, even if they seem natural

If you notice something that should change, mention it briefly and let the user decide.

## Verification before destructive operations

Before any operation that loses information (deletes, force-resets, mass renames, file overwrites of work you didn't read):

- Read or list the affected scope first
- For git: prefer non-destructive paths (new commit over amend, revert over reset, stash over discard)
- Confirm intent matches the actual change before running it

## Parallelize independent tool calls

When multiple tool calls don't depend on each other's results, issue them in the same response rather than sequentially. Reads, searches, and unrelated commands all benefit. Sequential is only needed when call N's input depends on call N-1's output.

## Match existing conventions

Before writing new code in a project:

- Look at neighboring files for naming, formatting, import order, error handling style
- Use the libraries and patterns already in the project, not your defaults
- Match indentation, line length, and docstring style to what's already there

Don't introduce a new dependency, framework, or pattern without a stated reason.

## Communication

Don't narrate the skill or your process. Don't say "I'll use the Edit tool" or "Following the coding-discipline skill, I'll..." Just do the work and report what changed in normal terms. The user doesn't need to see the meta layer.
