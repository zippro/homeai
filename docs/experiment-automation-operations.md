# Experiment Automation Operations

This runbook covers unattended execution of experiment guardrails + rollout automation.

## Command

Run once (live):

```bash
cd backend-api
source .venv/bin/activate
python3 scripts/run_experiment_automation.py \
  --hours 24 \
  --rollout-limit 200 \
  --actor scheduler \
  --reason daily_experiment_automation
```

Dry run:

```bash
python3 scripts/run_experiment_automation.py --dry-run --hours 24 --rollout-limit 200
```

## Optional controls

- `--notify-webhook-url <url>`: POST full JSON summary to your webhook.
- `--notify-dry-run`: allow notifications even when `--dry-run` is set.
- `--fail-on-breach`: exit code `2` if any guardrail breach detected.
- `--fail-on-rollout-blocked`: exit code `3` if any rollout was blocked.

Environment variable alternative:

- `EXPERIMENT_AUTOMATION_NOTIFY_WEBHOOK_URL=<url>`

## Cron example

Run every day at `00:15 UTC`:

```cron
15 0 * * * cd /opt/homeai/backend-api && . .venv/bin/activate && python3 scripts/run_experiment_automation.py --hours 24 --rollout-limit 200 --actor cron --reason daily_experiment_automation >> /var/log/homeai-experiment-automation.log 2>&1
```

## systemd example

`/etc/systemd/system/homeai-experiment-automation.service`

```ini
[Unit]
Description=HomeAI Experiment Automation Run
After=network.target

[Service]
Type=oneshot
WorkingDirectory=/opt/homeai/backend-api
Environment="EXPERIMENT_AUTOMATION_NOTIFY_WEBHOOK_URL=https://hooks.example.com/homeai"
ExecStart=/bin/bash -lc 'source .venv/bin/activate && python3 scripts/run_experiment_automation.py --hours 24 --rollout-limit 200 --actor systemd --reason scheduled_experiment_automation --fail-on-breach --fail-on-rollout-blocked'
```

`/etc/systemd/system/homeai-experiment-automation.timer`

```ini
[Unit]
Description=Run HomeAI Experiment Automation Daily

[Timer]
OnCalendar=*-*-* 00:15:00 UTC
Persistent=true

[Install]
WantedBy=timers.target
```

Enable:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now homeai-experiment-automation.timer
```

## Kubernetes CronJob example

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: homeai-experiment-automation
spec:
  schedule: "15 0 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          containers:
            - name: runner
              image: your-registry/homeai-backend:latest
              env:
                - name: EXPERIMENT_AUTOMATION_NOTIFY_WEBHOOK_URL
                  valueFrom:
                    secretKeyRef:
                      name: homeai-secrets
                      key: experiment_automation_webhook
              command:
                - /bin/bash
                - -lc
                - >
                  source .venv/bin/activate &&
                  python3 scripts/run_experiment_automation.py
                  --hours 24
                  --rollout-limit 200
                  --actor k8s-cron
                  --reason daily_experiment_automation
                  --fail-on-breach
                  --fail-on-rollout-blocked
```

## Monitoring checklist

- Track run status via:
  - script exit code
  - webhook notifications (if enabled)
  - `GET /v1/admin/experiments/automation/history?limit=50`
- Review for recurring blocked rollouts (`blocked_count > 0`) and guardrail breaches (`breached_count > 0`).
