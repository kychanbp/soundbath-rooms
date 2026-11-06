#!/bin/zsh
# Publish to GitHub: sources on main, the site on gh-pages. Uses a clean history with the GitHub noreply address.
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd); T=$(mktemp -d); REPO=https://github.com/kychanbp/soundbath-rooms.git
export GIT_AUTHOR_NAME=kychanbp GIT_COMMITTER_NAME=kychanbp GIT_AUTHOR_EMAIL=17669769+kychanbp@users.noreply.github.com GIT_COMMITTER_EMAIL=17669769+kychanbp@users.noreply.github.com
MSG="Update Sound Bath Rooms

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
cd "$ROOT"; mkdir "$T/src"
git ls-files -z | grep -zvE '^(renders/|scripts/runpod/on\.sh$|web/)' | xargs -0 -I{} rsync -R {} "$T/src/"
cd "$T/src"; git init -q -b main; git add -A; git commit -qm "$MSG"; git push -q -f "$REPO" main
mkdir "$T/site"; rsync -a "$ROOT/web/" "$T/site/"; cd "$T/site"; git init -q -b gh-pages; git add -A; git commit -qm "$MSG"; git push -q -f "$REPO" gh-pages
rm -rf "$T"; echo published
