# Automated-Lunch-Free CLI Starter Harness

`Automated-Lunch-Free` exposes full GUI-parity CLI workflows via Electron/Node (`npm.cmd run make`, `npm.cmd run map`, `npm.cmd run gfx`, `npm.cmd run style-test`, `node scripts/style-check.js`):

- List styles / presets: `python run_bench.py list-styles` | `python run_bench.py list-presets`
- Check style: `python run_bench.py check <style-id>`
- Run 8-beat gate: `python run_bench.py style-test <style-id>`
- Run full video: `python run_bench.py make --topic "..." --style <id> [--topic-override] [--stop-after plan]`
- Run standalone map / graphic: `python run_bench.py map ...` | `python run_bench.py gfx --type stat --data '{"value":42,"label":"Test"}'`
