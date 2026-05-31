#!/bin/bash
# Sync gdm-v0.2.json and push to the catalogue repo.
set -e

echo "Syncing to catalogue submodule..."
cp catalog/gdm-v0.2.json catalogue/spec/gdm-v0.2.json

echo "Pushing catalogue..."
cd catalogue
git add spec/gdm-v0.2.json
git commit -m "sync: update gdm-v0.2.json spec"
git push
cd ..

echo "Done — catalogue spec updated."
