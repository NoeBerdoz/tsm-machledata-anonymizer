#!/usr/bin/env bash
set -euo pipefail
umask 077

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ $EUID -ne 0 || $# -ne 2 || ! $1 =~ ^([0-9]{1,3}-){3}[0-9]{1,3}\.(sslip|nip)\.io$ ||
      ! $2 =~ ^(open|closed)$ ]]; then
    echo 'Run as root with the dashed-IP hostname and the HTTPS firewall state (open or closed).' >&2
    exit 1
fi
host=$1
https_firewall=$2
mapfile -t passwords
if [[ ${#passwords[@]} -ne 4 ]]; then
    echo 'Send four password lines on stdin in this order: admin, team, training, actions.' >&2
    exit 1
fi
for password in "${passwords[@]}"; do
    if [[ ! $password =~ ^[[:xdigit:]]{64}$ ]]; then
        echo 'Each password must be 32 bytes encoded as hex.' >&2
        exit 1
    fi
done
unset password

install -d -m 0755 /etc/mlflow
exec 9>/etc/mlflow/install.lock
flock 9

if [[ ! -s /var/lib/mlflow/auth.db || -e /etc/mlflow/bootstrap.env ]]; then
    if [[ $https_firewall != closed ]] || systemctl is-active --quiet caddy.service; then
        echo 'Close the public TCP 443 firewall rule and disable and stop Caddy before bootstrapping. See the HTTPS recovery step.' >&2
        exit 1
    fi
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl openssl python3
if [[ $(dpkg-query -W -f='${Status}' caddy 2>/dev/null || true) != 'install ok installed' ]]; then
    # Hold Caddy until the loopback checks pass and the HTTPS firewall is open.
    systemctl mask caddy.service
    apt-get install -y caddy
fi

if ! id mlflow >/dev/null 2>&1; then
    useradd --system --user-group --home-dir /var/lib/mlflow --no-create-home \
        --shell /usr/sbin/nologin mlflow
fi
install -d -m 0755 /opt/mlflow
uv_version=0.13.5
if [[ ! -x /opt/mlflow/bin/uv || $(/opt/mlflow/bin/uv --version) != "uv $uv_version "* ]]; then
    curl -fsSL "https://astral.sh/uv/$uv_version/install.sh" | UV_UNMANAGED_INSTALL=/opt/mlflow/bin sh
fi
export UV_PYTHON_INSTALL_DIR=/opt/mlflow/python
export UV_CACHE_DIR=/opt/mlflow/cache
if [[ ! -x /opt/mlflow/venv/bin/python ]]; then
    /opt/mlflow/bin/uv venv --python 3.13 /opt/mlflow/venv
fi
/opt/mlflow/bin/uv pip sync --require-hashes --only-binary :all: \
    --python /opt/mlflow/venv/bin/python mlflow-server-requirements.txt
# uv may install Python under a 0700 directory when the installer has a tight umask.
chmod -R a+rX /opt/mlflow/python /opt/mlflow/venv

cat >/etc/mlflow/auth.ini <<'EOF'
[mlflow]
default_permission = NO_PERMISSIONS
database_uri = sqlite:////var/lib/mlflow/auth.db
admin_username = admin
grant_default_workspace_access = true
EOF
chmod 0644 /etc/mlflow/auth.ini
printf 'MLFLOW_SERVER_CORS_ALLOWED_ORIGINS=https://%s\n' "$host" >/etc/mlflow/origin.env

make_secret_file() {
    local target=$1 key=$2 value tmp
    value=$(openssl rand -hex 32)
    tmp=$(mktemp /etc/mlflow/.env.XXXXXX)
    printf '%s=%s\n' "$key" "$value" >"$tmp"
    mv -f -- "$tmp" "$target"
}
if [[ ! -s /etc/mlflow/service.env ]]; then
    make_secret_file /etc/mlflow/service.env MLFLOW_FLASK_SERVER_SECRET_KEY
fi
if [[ ! -s /var/lib/mlflow/auth.db && ! -s /etc/mlflow/bootstrap.env ]]; then
    make_secret_file /etc/mlflow/bootstrap.env MLFLOW_AUTH_ADMIN_PASSWORD
fi

install -m 0644 mlflow.service /etc/systemd/system/mlflow.service
systemctl daemon-reload
systemctl enable mlflow.service
systemctl restart mlflow.service

printf '%s\n' "${passwords[@]}" | /usr/bin/python3 /dev/fd/3 3<<'PY'
import base64
import json
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import ProxyHandler, Request, build_opener

base_url = "http://127.0.0.1:5000/api"
opener = build_opener(ProxyHandler({}))
bootstrap_file = Path("/etc/mlflow/bootstrap.env")
users = dict(zip(("admin", "team", "training", "actions"), sys.stdin.read().splitlines(), strict=True))
experiments = {"team": "tsm-team", "training": "tsm-training", "actions": "tsm-gates"}


def request(path, *, auth=None, method="GET", body=None, query=None, expected=(200,)):
    headers = {}
    if auth is not None:
        encoded = base64.b64encode(":".join(auth).encode()).decode()
        headers["Authorization"] = f"Basic {encoded}"
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    suffix = "?" + urlencode(query) if query else ""
    req = Request(base_url + path + suffix, data=data, headers=headers, method=method)
    try:
        with opener.open(req, timeout=5) as response:
            status, payload = response.status, response.read()
    except HTTPError as exc:
        status, payload = exc.code, b""
    if status not in expected:
        raise RuntimeError(f"{method} {path} returned {status}, expected {expected}")
    return status, json.loads(payload) if payload else None


def account(username, auth, expected=(200,)):
    return request("/2.0/mlflow/users/get", auth=auth, query={"username": username}, expected=expected)


def wait_for_admin(expected):
    deadline = time.monotonic() + 120
    while True:
        try:
            status, _ = account("admin", admin, expected=expected)
            return status
        except (URLError, TimeoutError):
            if time.monotonic() >= deadline:
                raise
            time.sleep(2)


admin = ("admin", users["admin"])
if bootstrap_file.exists():
    bootstrap_password = bootstrap_file.read_text().strip().split("=", 1)[1]
    bootstrap = ("admin", bootstrap_password)
    if wait_for_admin((200, 401)) == 401:
        account("admin", bootstrap)
        request(
            "/2.0/mlflow/users/update-password", auth=bootstrap, method="PATCH",
            body={"username": "admin", "password": admin[1], "current_password": bootstrap_password},
        )
    account("admin", admin)
    account("admin", bootstrap, expected=(401,))
    bootstrap_file.unlink()
    # Drop the bootstrap environment from the running process, too.
    subprocess.run(["systemctl", "restart", "mlflow.service"], check=True)
wait_for_admin((200,))

search_path = "/2.0/mlflow/experiments/search"
request(search_path, method="POST", body={}, expected=(401,))

ids = {}
for username, name in experiments.items():
    status, response = request(
        "/2.0/mlflow/experiments/get-by-name", auth=admin, query={"experiment_name": name},
        expected=(200, 404),
    )
    if status == 404:
        _, response = request(
            "/2.0/mlflow/experiments/create", auth=admin, method="POST", body={"name": name},
        )
        ids[username] = response["experiment_id"]
    else:
        experiment = response["experiment"]
        if experiment["lifecycle_stage"] != "active":
            raise RuntimeError(f"Restore experiment {name} before rerunning setup")
        ids[username] = experiment["experiment_id"]

    status, response = account(username, admin, expected=(200, 404))
    if status == 404:
        request(
            "/2.0/mlflow/users/create", auth=admin, method="POST",
            body={"username": username, "password": users[username]},
        )
    elif response["user"]["is_admin"]:
        raise RuntimeError(f"{username} must be a non-admin user")

def ensure_grant(username, experiment_id, permission):
    grant = {"username": username, "resource_type": "experiment", "resource_id": experiment_id}
    _, current = request("/3.0/mlflow/users/permissions/get", auth=admin, query=grant)
    if current["permission"] == "NO_PERMISSIONS":
        request(
            "/3.0/mlflow/users/permissions/grant", auth=admin, method="POST",
            body={**grant, "permission": permission},
        )
    elif current["permission"] != permission:
        raise RuntimeError(f"Review the existing permission for {username} on experiment {experiment_id}")


for username, experiment_id in ids.items():
    ensure_grant(username, experiment_id, "EDIT")
    if username != "team":
        ensure_grant("team", experiment_id, "READ")

for username, experiment_id in ids.items():
    auth = (username, users[username])
    for other_user, other_id in ids.items():
        request(
            "/2.0/mlflow/experiments/get", auth=auth, query={"experiment_id": other_id},
            expected=(200,) if username in (other_user, "team") else (403,),
        )
        if username != other_user:
            request(
                "/2.0/mlflow/runs/create", auth=auth, method="POST",
                body={"experiment_id": other_id}, expected=(403,),
            )
    for resource in ("experiments", "registered-models"):
        request(
            f"/2.0/mlflow/{resource}/create", auth=auth, method="POST",
            body={"name": "setup-permission-check"}, expected=(403,),
        )
print("MLflow accounts and experiment permissions verified.")
PY
unset passwords

rendered=$(mktemp)
trap 'rm -f -- "$rendered"' EXIT
sed "s/__HOST__/$host/g" Caddyfile >"$rendered"
caddy validate --adapter caddyfile --config "$rendered"
install -m 0644 "$rendered" /etc/caddy/Caddyfile
# A previous package install may have finished while Caddy was still masked.
if [[ $(readlink /etc/systemd/system/caddy.service) == /dev/null ]]; then
    systemctl unmask caddy.service
    systemctl disable --now caddy.service
fi
echo 'MLflow is enabled. Open TCP 443 and start Caddy from the setup guide.'
