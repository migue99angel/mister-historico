#!/usr/bin/env bash
# Remove local branches (and their worktrees) whose pull request was merged.
#
# Rebase-merge rewrites SHAs, so `git branch --merged` cannot be used. A branch
# is only removed when its local tip equals the head commit of a merged PR, so
# commits added after the merge are never lost. Dirty worktrees are skipped.
#
# Usage: tools/clean_branches.sh [--apply]   (dry run by default)
set -euo pipefail

apply=false
[[ "${1:-}" == "--apply" ]] && apply=true

# Prune stale remote-tracking refs on the way; the decision itself uses gh only.
git fetch --prune --quiet

current=$(git branch --show-current)
merged=$(gh pr list --state merged --limit 500 --json headRefName,headRefOid \
  --jq '.[] | "\(.headRefName) \(.headRefOid)"')

worktree_of() {
  git worktree list --porcelain | awk -v ref="refs/heads/$1" '
    /^worktree /{path=substr($0, 10)} $0=="branch "ref{print path}'
}

found=false
while read -r branch; do
  [[ "$branch" == "main" || "$branch" == "$current" ]] && continue
  tip=$(git rev-parse "refs/heads/$branch")
  grep -qxF "$branch $tip" <<<"$merged" || continue
  found=true
  path=$(worktree_of "$branch")
  if ! $apply; then
    echo "would remove: $branch${path:+ (worktree $path)}"
    continue
  fi
  if [[ -n "$path" ]] && ! git worktree remove "$path"; then
    echo "skipped: $branch (could not remove worktree $path)" >&2
    continue
  fi
  git branch -D "$branch"
done < <(git for-each-ref --format='%(refname:short)' refs/heads)

$found || echo "nothing to clean"
$apply || ! $found || echo "run with APPLY=1 to remove them"
