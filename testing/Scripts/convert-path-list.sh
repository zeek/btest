#!/usr/bin/env bash

# This script is used by tests.environment-windows to convert a semi-colon
# separated list of Windows-style paths into a colon-separate list of
# POSIX-style paths.

new_list=""

IFS=';' read -ra PARTS <<<"$1"
for i in "${PARTS[@]}"; do
    p=$(cygpath "${i}" | sed 's/\/$//')
    new_list+=$p
    new_list+=":"
done

echo "${new_list%?}"
