#!/bin/bash

# create a new directory and init a git repository
mkdir -p merkle-demo && cd merkle-demo
git init
echo "hello" > a.txt
git add a.txt
git commit -m "initial commit"

# inspect merkle tree for the initial commit
git cat-file -p HEAD^{tree}

# change a.txt
echo "world" >> a.txt
git add a.txt && git commit -m "change a.txt"

# inspect which files are changed
git diff --name-only HEAD~1 HEAD

# inspect merkle tree to prove hash diff
git cat-file -p HEAD^{tree}
git cat-file -p HEAD~1^{tree}

# add a directory
mkdir -p tests && echo "test hello world" > tests/b.txt
git add tests/b.txt && git commit -m "add tests/b.txt"

# inspect merkle tree to prove hash diff
git cat-file -p HEAD^{tree}
git cat-file -p HEAD~1^{tree}

# inspect sub-tree for tests/
git cat-file -p HEAD^{tree}:tests
