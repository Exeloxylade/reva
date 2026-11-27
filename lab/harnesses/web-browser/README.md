# REVA Web-Browser & Ingredient Sourcing Harness

Headless Chromium/Edge (`web_capture.py`) harness for JS-rendered documentation, diagrams, and external asset discovery:

1. Standalone render & link extraction:
   ```cmd
   python browse.py https://example.org --screenshot --out-dir . --slug ref
   ```
2. Recommended REVA Study workflow (`skills/reva-browse/SKILL.md`):
   ```cmd
   python reva.py research shop <study> "<query>" --aisle all --download 1
   python reva.py research browse <study> <url> --discover-links
   ```
