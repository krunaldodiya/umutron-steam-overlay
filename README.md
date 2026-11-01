# UmuTron Steam Overlay

Apply UmuTron `fixes/<Game>` folders to Steam-launched games through a
read-only `fuse-overlayfs` mount. The game's `common/<Game>` tree is never
modified, so Steam's **Verify integrity of game files** and updates cannot
erase fixes.

## How it works

```text
Steam launch option:
  umutron-steam-overlay run %command%
        |
        v
find .../umuapps/common/<Game> in %command%
        |
        v
mount fuse-overlayfs(lowerdir=fixes/<Game>:common/<Game>, ro)
        |
        v
rewrite the command's common/<Game> paths to the merged mount
        |
        v
exec Steam's Proton command
        |
        v
unmount and remove the temporary overlay when the game exits
```

If a game has no `fixes/<Game>` folder, the wrapper executes Steam's command
unchanged.

## Install

```bash
cd umutron-steam-overlay
python3 -m venv .venv
.venv/bin/pip install -e .
```

Check host requirements:

```bash
.venv/bin/umutron-steam-overlay doctor
```

`fuse-overlayfs` and `fusermount3` or `fusermount` must be installed.

## Configure Steam

For a game with fixes, open **Properties → General → Launch Options** and add:

```text
/path/to/umutron-steam-overlay run %command%
```

Or print the exact line:

```bash
umutron-steam-overlay launch-option
```

The wrapper detects the game from the executable path. No per-game
registration is required beyond the launch option.

Test without mounting:

```bash
umutron-steam-overlay inspect -- %command%
```

## Layout

Expected UmuTron library layout:

```text
<drive>/UmuLibrary/umuapps/
├── common/<Game>/       original Steam/install files
├── fixes/<Game>/        overlay files
└── ...
```

Only files in `fixes/<Game>` override `common/<Game>`. The merged view is
read-only.

## Lumen/LuaTools integration

The actual overlay must run at process-launch time. A Lumen UI plugin cannot
mount it from inside Steam's CEF UI. A Lumen/LuaTools menu can manage the
launch option and show status, while this binary performs the mount.

A future plugin can call:

```text
umutron-steam-overlay launch-option
```

and write the resulting value into the game's Steam launch options.

## Limitations

- Linux only.
- Requires `fuse-overlayfs`.
- Steam still owns the prefix and Steam API authorization.
- The wrapper does not bypass DRM or create Steam ownership.
- Steam launch-option editing is outside this project's scope; it is left to
  the UI/plugin layer.

## Tests

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```
