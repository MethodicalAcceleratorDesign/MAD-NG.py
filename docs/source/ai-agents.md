```{eval-rst}
.. currentmodule:: pymadng
```

# Skills for AI agents

The repository ships a skill for AI coding agents that write PyMAD-NG code: [`skills/pymadng`](https://github.com/MethodicalAcceleratorDesign/MAD-NG.py/tree/main/skills/pymadng). It is a short `SKILL.md` plus a `reference.md`, in the format used by Claude Code and read as plain Markdown by other agents.

It holds what an agent needs to avoid the usual mistakes:

- {meth}`MAD.send` and {meth}`MAD.recv` must be matched, or the pipe desynchronises.
- Python strings are Lua code, and numbers go through `py:recv()` rather than being formatted into the source.
- Lua tables come back as references, and anonymous results use a limited number of temporary variables.
- How MAD-NG errors surface and how to stream data during a long command.

## Install

Copy the folder into the skills directory of your agent. For Claude Code:

```bash
cp -r skills/pymadng ~/.claude/skills/        # all projects
cp -r skills/pymadng .claude/skills/          # one project
```

The skill covers PyMAD-NG only. For the MAD-NG language itself, point the agent at the [MAD-NG manual](https://madx.web.cern.ch/releases/madng/html/).
