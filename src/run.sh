#!/usr/bin/env bash 

HEADLESS=0

ARGS=()

while [ ${#} -gt 0 ]; do 
    case "${1}" in 
        --headless)
            HEADLESS=1
            ;;
        *)
            ARGS+=("${1}")
            ;;
    esac

    shift
done

set -eux

if [ ${HEADLESS} -eq 1 ]; then
    xvfb-run -a --server-args="-screen 0 1920x1080x24 -ac -nolisten tcp -dpi 96 +extension RANDR" \
        python -B -m pytest -p no:cacheprovider --exitfirst --record-screen "${ARGS[@]}"
else
    python -B -m pytest -p no:cacheprovider --exitfirst "${ARGS[@]}"
fi
