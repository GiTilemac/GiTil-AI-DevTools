#!/usr/bin/env bash
# Uploads ../prometheus/rules/*-alerts.yml to Grafana Cloud's Prometheus
# (Mimir ruler), so the deployed environments get the same alerts as the
# local stack. Idempotent: each run replaces the rule groups in the
# `snake-arena` namespace.
#
# Needs (from the Grafana Cloud portal → your stack → Prometheus → Details):
#   GRAFANA_CLOUD_PROMETHEUS_URL   e.g. https://prometheus-prod-24-prod-eu-west-2.grafana.net
#   GRAFANA_CLOUD_PROMETHEUS_USER  the instance ID (a number)
#   GRAFANA_CLOUD_TOKEN            an access policy token with rules:write
#   GRAFANA_URL                    e.g. https://<stack>.grafana.net, for dashboard links
set -euo pipefail

: "${GRAFANA_CLOUD_PROMETHEUS_URL:?}" "${GRAFANA_CLOUD_PROMETHEUS_USER:?}" "${GRAFANA_CLOUD_TOKEN:?}" "${GRAFANA_URL:?}"
here=$(cd "$(dirname "$0")" && pwd)
namespace=snake-arena

for file in "$here"/../prometheus/rules/*-alerts.yml; do
  # The ruler API takes one group per request. Split the file into
  # groups and point dashboard links at Grafana Cloud instead of the
  # local Grafana.
  uv run --quiet --with pyyaml python - "$file" "$GRAFANA_URL" <<'PY' |
import json, sys, yaml
path, grafana_url = sys.argv[1], sys.argv[2].rstrip("/")
for group in yaml.safe_load(open(path))["groups"]:
    text = yaml.safe_dump(group, sort_keys=False).replace("http://localhost:3000", grafana_url)
    print(json.dumps({"name": group["name"], "yaml": text}))
PY
  while read -r line; do
    name=$(jq -r .name <<<"$line")
    jq -r .yaml <<<"$line" | curl -fsS -u "$GRAFANA_CLOUD_PROMETHEUS_USER:$GRAFANA_CLOUD_TOKEN" \
      -H "Content-Type: application/yaml" --data-binary @- \
      "$GRAFANA_CLOUD_PROMETHEUS_URL/api/prom/config/v1/rules/$namespace" > /dev/null
    echo "Uploaded rule group $name from $(basename "$file")"
  done
done
