# alphaTab for Usable Tab

The modified alphaTab 1.8.4 used by the Usable Tab app, published to meet the Mozilla Public
License 2.0. Usable Tab itself is a separate, closed-source work and is not in this repository.

## Contents

- `UsableTab/AlphaTabAssets/alphaTab.min.js`: the file that ships in the app.
- `tools/patch_alphatab_*.py`: the changes made to the upstream bundle.
- `tools/rebuild_alphatab.py`, `tools/alphatab.lock.json`: rebuild from the pinned upstream archive and check every hash.
- `UsableTab/AlphaTabAssets/alphaTab-LICENSE.txt`: MPL 2.0, which covers alphaTab and these changes.
- `UsableTab/AlphaTabAssets/font/`: the unmodified Bravura font and its SIL OFL 1.1 licence.

## Upstream

- npm package: <https://registry.npmjs.org/@coderline/alphatab/-/alphatab-1.8.4.tgz>
- SHA-256 of the archive: `70b2c77abc9698a055d90a11d77308b6b41247936476e969d85770e3d4db4602`
- alphaTab source: <https://github.com/CoderLine/alphaTab>

## Rebuild

No npm install is needed, only Python 3. This downloads the pinned archive, applies the patches
and checks the result against the files here:

```bash
python3 tools/rebuild_alphatab.py --fetch
```
