#!/usr/bin/env bash
set -euo pipefail
umask 077

if (( EUID != 0 )); then
    echo 'Run as root to configure the MLflow swap file.' >&2
    exit 1
fi

swap_file=/swapfile-mlflow
exec 9>>/run/mlflow-swap.lock
flock 9

fstab_entry=$(awk -v path="$swap_file" '$1 == path { print $2, $3, $4, $5, $6 }' /etc/fstab)
if [[ -n $fstab_entry && $fstab_entry != 'none swap sw 0 0' ]]; then
    echo "Resolve the existing entries for $swap_file in /etc/fstab before continuing." >&2
    exit 1
fi

if [[ -L $swap_file || ( -e $swap_file && ! -f $swap_file ) ]]; then
    echo "Expected a regular file at $swap_file." >&2
    exit 1
fi

if [[ ! -e $swap_file ]]; then
    available_kib=$(df -k --output=avail / | tail -n 1)
    if (( available_kib < 3 * 1024 * 1024 )); then
        echo 'Need 3 GiB free on / to allocate 2 GiB of swap and leave 1 GiB available.' >&2
        exit 1
    fi

    temp=$(mktemp "$swap_file.XXXXXX")
    trap 'rm -f -- "$temp"' EXIT
    dd if=/dev/zero of="$temp" bs=1M count=2048 conv=fsync status=none
    mkswap -- "$temp" >/dev/null
    ln -T -- "$temp" "$swap_file"
    rm -- "$temp"
elif [[ $(stat -c '%u:%a:%s' -- "$swap_file") != 0:600:2147483648 ]]; then
    echo "Expected a root-owned, mode-0600, 2 GiB swap file at $swap_file." >&2
    exit 1
fi

active_swap=$(swapon --show=NAME --noheadings --raw)
if ! grep -Fxq -- "$swap_file" <<<"$active_swap"; then
    swapon -- "$swap_file"
fi
active_swap=$(swapon --show=NAME,SIZE --bytes --noheadings --raw)
if ! awk -v path="$swap_file" '$1 == path && $2 >= 2146435072 { found = 1 } END { exit !found }' <<<"$active_swap"; then
    echo "Expected about 2 GiB of active swap at $swap_file." >&2
    exit 1
fi
if [[ -z $fstab_entry ]]; then
    printf '\n%s none swap sw 0 0\n' "$swap_file" >>/etc/fstab
fi
