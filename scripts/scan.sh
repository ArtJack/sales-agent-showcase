#!/usr/bin/env bash
# Lightweight secret/leak scan for the public showcase. Run before every push.
# Exits non-zero if anything suspicious is found.
#
# Project-specific tokens (client name, private repo name, real marketplace
# module names) belong in an untracked `.scan-denylist` (one regex per line) so
# they are never committed to this public repo. `.scan-denylist` is gitignored.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 2
fail=0
# Generic keyword scan skips docs/config that legitimately discuss security.
GEN_EXCLUDES=(--exclude-dir=.git --exclude-dir=.venv --exclude-dir=.pytest_cache \
  --exclude=scan.sh --exclude='*.md' --exclude=NOTICE --exclude=.gitignore --exclude=LICENSE)
# Denylist scan covers docs too (a client/repo name there WOULD be a leak),
# but not the ignore-rules file or the denylist itself.
DENY_EXCLUDES=(--exclude-dir=.git --exclude-dir=.venv --exclude-dir=.pytest_cache \
  --exclude=scan.sh --exclude=.gitignore --exclude=.scan-denylist)

echo "== generic secret patterns =="
if grep -RInE '(api[_-]?key|secret|passwd|password|authorization|bearer|cookie|-----BEGIN [A-Z ]*PRIVATE KEY-----|sk-[A-Za-z0-9]{16,}|AKIA[0-9A-Z]{16})' "${GEN_EXCLUDES[@]}" .; then
  echo "!! potential secret/keyword above"; fail=1
else
  echo "   clean"
fi

echo "== project denylist (.scan-denylist) =="
if [ -f .scan-denylist ]; then
  while IFS= read -r pat; do
    [ -z "$pat" ] && continue
    case "$pat" in \#*) continue ;; esac
    if grep -RInE "$pat" "${DENY_EXCLUDES[@]}" .; then
      echo "!! denylisted token '$pat' above"; fail=1
    fi
  done < .scan-denylist
  [ "$fail" = 0 ] && echo "   clean"
else
  echo "   (no .scan-denylist — create one with client/private-repo tokens)"
fi

echo "== sensitive files must not be tracked =="
if git ls-files 2>/dev/null | grep -iE '\.env$|\.db$|sqlite|session|browser_profile'; then
  echo "!! sensitive file is tracked"; fail=1
else
  echo "   clean"
fi

if [ "$fail" = 0 ]; then
  echo ""; echo "OK — no secrets or denylisted tokens found."
  echo "Also scan history before first push:  git log -p | grep -nE -f .scan-denylist"
fi
exit $fail
