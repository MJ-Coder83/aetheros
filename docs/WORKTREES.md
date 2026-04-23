# Git Worktrees — InkosAI

Git worktrees let you have multiple branches checked out simultaneously in
separate directories. This is essential for InkosAI development where you may
need to work on multiple features, run comparisons, or let Prime analyze
different branches in parallel.

## Quick Start

```bash
# Create a new worktree for a feature branch
make worktree-add WT=feat/prime-introspection

# List all active worktrees
make worktree-list

# Remove a worktree when done
make worktree-remove WT=feat/prime-introspection

# Clean up all worktrees (keeps main only)
make worktree-clean
```

## Makefile Targets

| Target | Description |
|--------|-------------|
| `make worktree-add WT=<name>` | Create a new worktree at `worktrees/<name>` with a new branch |
| `make worktree-list` | List all active worktrees |
| `make worktree-remove WT=<name>` | Remove a worktree and its branch |
| `make worktree-clean` | Remove all worktrees (except the main checkout) |

## How It Works

- Worktrees are stored in the `worktrees/` directory (git-ignored).
- Each worktree gets its own branch with the same name.
- The main checkout in the project root is always on `main`.

## Use Cases

1. **Parallel feature development** — work on multiple features without stashing
2. **Prime analysis** — let Prime compare branches side-by-side
3. **Hotfixes** — create a quick fix worktree without disturbing your current work
4. **Experimentation** — try risky changes in an isolated worktree

## Manual Commands

```bash
# Create a worktree with a new branch
git worktree add -b feat/my-feature worktrees/feat/my-feature

# Create a worktree from an existing branch
git worktree add worktrees/feat/my-feature feat/my-feature

# List worktrees
git worktree list

# Remove a worktree
git worktree remove worktrees/feat/my-feature

# Prune stale worktree metadata
git worktree prune
```

## Tips

- Worktrees share the same `.git` directory, so commits in one worktree are
  visible in all others immediately.
- Don't nest worktrees inside each other.
- Run `make worktree-clean` periodically to remove stale worktrees.
