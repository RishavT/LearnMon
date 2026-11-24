#!/usr/bin/env bash
set -euo pipefail

if [[ $# != 2 ]]; then
    echo "Usage: $0 <release-tag> <output-directory>" >&2
    exit 2
fi

tag=$1
if [[ ! "$tag" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ || $(uname -m) != x86_64 ]]; then
    echo "Use a vMAJOR.MINOR.PATCH tag and an x86-64 Linux builder." >&2
    exit 2
fi

repo=$(git -C "$(dirname -- "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)
commit=$(git -C "$repo" rev-parse --verify "refs/tags/$tag^{commit}")
mkdir -p -- "$2"
output=$(cd -- "$2" && pwd)
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT

app="$work/LearnMon.AppDir"
game="$app/usr/share/learnmon"
mkdir -p "$game"
git -C "$repo" archive "$commit" | tar -x -C "$game"

uv python install --no-bin --install-dir "$work/pythons" 3.12.14
mv "$work/pythons/cpython-3.12.14-linux-x86_64-gnu" "$app/usr/python"
uv pip install --python "$app/usr/python/bin/python3.12" \
    --target "$app/usr/python/lib/python3.12/site-packages" \
    --requirements "$game/pyproject.toml"

cat >"$app/AppRun" <<'APP_RUN'
#!/bin/sh
set -eu
APPDIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
export TUXEMON_STORAGE_DIR="${TUXEMON_STORAGE_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/tuxemon-debugging-trail}"
unset PYTHONHOME PYTHONPATH
cd "$APPDIR/usr/share/learnmon"
exec "$APPDIR/usr/python/bin/python3.12" run_tuxemon.py --debug-campaign "$@"
APP_RUN
chmod 755 "$app/AppRun"

cat >"$app/learnmon.desktop" <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=LearnMon
Comment=Play Debugging Trail
Exec=learnmon
Icon=learnmon
Terminal=false
Categories=Game;RolePlaying;
DESKTOP
cp "$game/mods/tuxemon/gfx/icon_128.png" "$app/learnmon.png"
chmod -R a+rX "$app"

curl -fsSL --retry 2 https://github.com/AppImage/appimagetool/releases/download/1.9.1/appimagetool-x86_64.AppImage -o "$work/appimagetool"
curl -fsSL --retry 2 https://github.com/AppImage/type2-runtime/releases/download/20251108/runtime-x86_64 -o "$work/runtime"
(
    cd "$work"
    sha256sum --check <<'SHA256'
ed4ce84f0d9caff66f50bcca6ff6f35aae54ce8135408b3fa33abfc3cb384eb0  appimagetool
2fca8b443c92510f1483a883f60061ad09b46b978b2631c807cd873a47ec260d  runtime
SHA256
)
chmod 755 "$work/appimagetool"
ARCH=x86_64 "$work/appimagetool" --appimage-extract-and-run \
    --no-appstream --runtime-file "$work/runtime" \
    --mksquashfs-opt -processors --mksquashfs-opt 4 \
    "$app" "$output/LearnMon-$tag-x86_64.AppImage"
