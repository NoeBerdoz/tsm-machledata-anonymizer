#!/usr/bin/env bash
set -uo pipefail

project=tsmmachledata-projet
account=tsmmachledata@gmail.com
region=us-central1
zone=us-central1-a
vm=mlflow
bucket=gs://tsmmachledata-projet-mlflow
job_account="mlflow-training@$project.iam.gserviceaccount.com"
iap_record="$HOME/.config/tsm-mlflow/iap-condition"

gc() { gcloud --configuration=tsm-machledata "$@"; }

listed() {
    local target=$1 entries=$2
    [[ $'\n'$entries$'\n' == *$'\n'"$target"$'\n'* ]]
}

delete_if_listed() {
    local target=$1 entries=$2
    shift 2
    if listed "$target" "$entries"; then
        gc "$@" --quiet
    fi
}

delete_compute() {
    local resource=$1 name=$2 target=$2 fields=name scope entries
    shift 2
    if [[ $# -gt 0 ]]; then
        scope=${1%%=*}
        fields+=",${scope#--}.basename()"
        target+=$'\t'"${1#*=}"
    fi
    entries=$(gc compute "$resource" list --filter="name=$name" --format="value($fields)") || return
    delete_if_listed "$target" "$entries" compute "$resource" delete "$name" "$@"
}

close_https() {
    delete_compute firewall-rules mlflow-https
}

read_iap_condition() {
    local entries name instance_zone address expression
    local pattern="^destination[.]port == 22 && destination[.]ip == '([0-9]{1,3}[.]){3}[0-9]{1,3}'$"
    if [[ -e $iap_record ]]; then
        if ! IFS= read -r expression <"$iap_record" || [[ ! $expression =~ $pattern ]]; then
            echo "Check the saved IAP condition in $iap_record." >&2
            return 1
        fi
        printf '%s\n' "$expression"
        return
    fi

    # Older deployments can use the live VM to reconstruct the condition.
    entries=$(gc compute instances list --filter="name=$vm" \
        --format='value(name,zone.basename(),networkInterfaces[0].networkIP)') || return
    while IFS=$'\t' read -r name instance_zone address; do
        if [[ $name == "$vm" && $instance_zone == "$zone" ]]; then
            expression="destination.port == 22 && destination.ip == '$address'"
            if [[ ! $expression =~ $pattern ]]; then
                echo 'Could not read the MLflow VM internal IPv4 address.' >&2
                return 1
            fi
            printf '%s\n' "$expression"
            return
        fi
    done <<< "$entries"
}

remove_iap_binding() {
    local condition entries
    condition=$(read_iap_condition) || return
    if [[ -n $condition ]]; then
        entries=$(gc projects get-iam-policy "$project" --flatten='bindings[].members' \
            --filter="bindings.role='roles/iap.tunnelResourceAccessor' AND bindings.members='user:$account' AND bindings.condition.title='mlflow-ssh'" \
            --format='value(bindings.condition.expression)') || return
        delete_if_listed "$condition" "$entries" projects remove-iam-policy-binding "$project" \
            --member="user:$account" --role=roles/iap.tunnelResourceAccessor \
            --condition="title=mlflow-ssh,expression=$condition"
    fi
}

stop_caddy() {
    local entries
    entries=$(gc compute instances list --filter="name=$vm" \
        --format='value(name,zone.basename())') || return
    if listed "$vm"$'\t'"$zone" "$entries"; then
        gc compute ssh "$vm" --tunnel-through-iap --zone="$zone" \
            --command='state=$(systemctl show --property=LoadState --value caddy.service) &&
                { [ "$state" = not-found ] || sudo systemctl disable --now caddy.service; }' -- -T
    fi
}

teardown() {
    local entries
    remove_iap_binding || return
    delete_compute instances "$vm" --zone="$zone" || return
    delete_compute disks "$vm" --zone="$zone" || return
    delete_compute addresses mlflow-ip --region="$region" || return
    entries=$(gc storage buckets list --format='value(name)') || return
    delete_if_listed "${bucket#gs://}" "$entries" storage rm --recursive "$bucket" || return
    entries=$(gc secrets list --format='value(name.basename())') || return
    delete_if_listed mlflow-training-password "$entries" secrets delete mlflow-training-password || return
    entries=$(gc iam service-accounts list --format='value(email)') || return
    delete_if_listed "$job_account" "$entries" iam service-accounts delete "$job_account" || return
    delete_compute firewall-rules mlflow-iap || return
    delete_compute networks mlflow-net || return
    delete_compute resource-policies mlflow-daily --region="$region"
}

main() {
    local active_account active_project
    if [[ $# -gt 1 || ( $# -eq 1 && $1 != --close-https ) ]]; then
        echo 'Usage: bash ops/mlflow/teardown.sh [--close-https]' >&2
        return 2
    fi
    active_account=$(gc config get-value core/account) || return
    active_project=$(gc config get-value core/project) || return
    if [[ $active_account != "$account" || $active_project != "$project" ]]; then
        echo 'Check the account and project in the tsm-machledata configuration.' >&2
        return 1
    fi
    close_https || return
    if [[ $# -eq 1 ]]; then
        stop_caddy
    else
        teardown
    fi
}

main "$@"
