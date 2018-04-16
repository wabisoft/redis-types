#!/bin/bash
[[ $TRACE ]] && set -x


function errcho(){
  echo "$@" >&2
}

function diffstaged(){
  git diff --name-status --cached --exit-code || (errcho "Can't release with uncommited changes..." && exit 2)
}

function diffunstaged(){
  git diff --name-status --exit-code || (errcho "Can't release with unstaged changes..." && exit 1)
}

set -euo pipefail

VERSION="$(python -W ignore::UserWarning:distutils.dist setup.py --version)"
COMMIT="$(git log -1 --oneline)"

errcho "Releasing $COMMIT"

if [[ ! -f "$HOME/.pypirc" ]]; then
  errcho "~/.pypirc must be set up correctly to create a release (https://github.com/appfigures/libappfigures-python/blob/master/README.md#publishing-a-version)"
  exit 3
fi

diffunstaged
diffstaged

read -p"New version (was $VERSION): " NEWVERSION
read -p"Version message: " MESSAGE

echo "Making [$NEWVERSION] $MESSAGE at $COMMIT"
read -r -p "Are you sure? [Y/n]" response
if [[ $response =~ ^(yes|y|Y| ) ]] || [[ -z $response ]]; then
  sed -i "s/$VERSION/$NEWVERSION/" setup.py
  cat README.md | awk 'FNR==NR{ if (/# History/) p=NR; next} 1; FNR==p{ print "'"* $NEWVERSION\t$MESSAGE"'" }' README.md README.md > readme.tmp
  mv readme.tmp README.md
  git add -up
  diffunstaged
  git commit -m"[$NEWVERSION] $MESSAGE"
  git tag -a "$NEWVERSION" -m "$MESSAGE"
  git push origin "$NEWVERSION"
  git push origin master
  make publish
fi

