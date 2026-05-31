#!/bin/bash
# Regenerate gdm-v0.2.json from a2ui_catalog.py and push to the catalogue repo.
set -e

echo "Regenerating spec from a2ui_catalog.py..."
source venv/bin/activate
python3 -c "import sys; sys.argv=['emit']; from app.a2ui_catalog import emit_json_catalog; emit_json_catalog()" > /dev/null

echo "Syncing to catalogue submodule..."
cp catalog/gdm-v0.2.json catalogue/spec/gdm-v0.2.json

echo "Pushing catalogue..."
cd catalogue
git add spec/gdm-v0.2.json
git commit -m "sync: regenerate gdm-v0.2.json from a2ui_catalog.py"
git push
cd ..

echo "Done — catalogue spec updated."
