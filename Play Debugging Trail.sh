#!/usr/bin/env bash
set -Eeuo pipefail

exec 3>&2

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
project_dir=$PWD
cache_root="${XDG_CACHE_HOME:-$HOME/.cache}/tuxemon-debugging-trail"
export TUXEMON_STORAGE_DIR="${TUXEMON_STORAGE_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/tuxemon-debugging-trail}"
mkdir -p "$cache_root" "$TUXEMON_STORAGE_DIR"
log_file="$TUXEMON_STORAGE_DIR/launcher.log"

show_error() {
    local status=$?
    if (( BASH_SUBSHELL )); then
        exit "$status"
    fi
    local message="Debugging Trail couldn't start. See $log_file"
    printf '%s\n' "$message" >&3
    if [[ -n "${DISPLAY:-}" ]] && command -v xmessage >/dev/null; then
        xmessage -center "$message"
    fi
    exit "$status"
}
trap show_error ERR

prepare_runtime() {
    local python="${TUXEMON_PYTHON:-python3}"
    local runtime_key
    runtime_key=$("$python" -c 'import platform; print(platform.python_version(), platform.machine(), sep="-")')
    local runtime="$cache_root/$runtime_key"
    local expected
    expected=$(sha256sum pyproject.toml | cut -d ' ' -f 1)
    if [[ ! -x "$runtime/bin/python" ]]; then
        "$python" -m venv "$runtime"
    fi
    if [[ ! -f "$runtime/.dependencies" ]] || [[ $(<"$runtime/.dependencies") != "$expected" ]]; then
        "$runtime/bin/python" -m pip install --disable-pip-version-check "$project_dir"
        printf '%s\n' "$expected" > "$runtime/.dependencies"
    fi
    game_python="$runtime/bin/python"
}

printf 'Preparing Debugging Trail. Log: %s\n' "$log_file"
{
    flock 9
    prepare_runtime
} 9>"$cache_root/setup.lock" >"$log_file" 2>&1
"$game_python" "$project_dir/run_tuxemon.py" --debug-campaign >>"$log_file" 2>&1
