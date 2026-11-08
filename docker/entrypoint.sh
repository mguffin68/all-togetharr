#!/bin/sh
set -eu

# Validate UMASK (shared by root and non-root paths)
case "$UMASK" in
    [0-7][0-7][0-7]|[0-7][0-7][0-7][0-7]) ;;
    *)
        printf '{"level":"ERROR","logger":"entrypoint","message":"UMASK must be 3 or 4 octal digits"}\n' >&2
        exit 1
        ;;
esac

if [ "$(id -u)" = "0" ]; then
    case "$PUID" in
        ''|*[!0-9]*)
            printf '{"level":"ERROR","logger":"entrypoint","message":"PUID must be a number"}\n' >&2
            exit 1
            ;;
    esac

    case "$PGID" in
        ''|*[!0-9]*)
            printf '{"level":"ERROR","logger":"entrypoint","message":"PGID must be a number"}\n' >&2
            exit 1
            ;;
    esac

    mkdir -p /config /data
    chown -R "$PUID:$PGID" /config
    chown "$PUID:$PGID" /data
    umask "$UMASK"
    exec setpriv --reuid="$PUID" --regid="$PGID" --clear-groups python -m all_togetharr.serve
else
    umask "$UMASK"
    exec python -m all_togetharr.serve
fi
