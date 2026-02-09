# A/B Testing Plan: Pricing + AI Tool Usage

## Goal

Run controlled experiments to improve:
- paid conversion,
- render completion/success,
- retention,
- cost per successful render.

## Experiment guardrails

Always monitor guardrails during every experiment:
- `render_success_rate >= 85%`
- `p95_render_latency <= 12s`
- `avg_cost_per_render <= target` (set by finance)
- `crash_free_sessions >= 99.5%`
- no statistically significant increase in abuse/moderation incidents

Stop experiment early if any guardrail is violated for 2 consecutive days.

## Common setup for all tests

1. Randomization unit: `user_id` (sticky assignment).
2. Traffic split: start `10/10`, then `25/25`, then `50/50`.
3. Minimum run window: at least 7 full days, ideally 14 days for subscription tests.
4. Primary metric only one per test; others are secondary.
5. Sequential testing only for pricing (avoid overlapping pricing tests).

## Pricing experiments

### 1) Paywall cadence

- Hypothesis: showing paywall at the first successful preview increases upgrade conversion.
- Variant A (control): show paywall only on credit exhaustion.
- Variant B: show soft paywall after first successful preview + hard paywall on exhaustion.
- Primary metric: `upgrade_conversion_7d`.
- Secondary metrics: `preview_to_final_rate`, `D7 retention`, `refund_rate`.

### 2) Plan presentation

- Hypothesis: defaulting to yearly plan increases annual ARPU without harming conversion.
- Variant A: weekly highlighted.
- Variant B: yearly highlighted with annual savings badge.
- Primary metric: `net_revenue_per_visitor`.
- Secondary metrics: `checkout_completion_rate`, `refund_rate_14d`.

### 3) Credit packaging

- Hypothesis: larger free preview allowance improves activation and downstream paid conversion.
- Variant A: free plan daily credits = current baseline.
- Variant B: +1 preview credit/day, unchanged final-credit pricing.
- Primary metric: `first_day_activation_rate`.
- Secondary metrics: `paid_conversion_14d`, `avg_cost_per_new_user`.

## AI provider/model routing experiments

### 4) Preview model quality vs cost

- Hypothesis: slightly higher-quality preview model increases preview->final conversion enough to justify cost.
- Variant A: low-cost preview model (current baseline).
- Variant B: mid-quality preview model.
- Primary metric: `preview_to_final_rate`.
- Secondary metrics: `avg_cost_per_successful_final`, `p95_latency`.

### 5) Final model routing strategy

- Hypothesis: dynamic routing by room complexity reduces cost with no quality drop.
- Variant A: fixed final model for all jobs.
- Variant B: complexity-based route (simple rooms -> cheaper model, complex -> premium).
- Primary metric: `avg_cost_per_successful_final`.
- Secondary metrics: `user_rating_after_final`, `regeneration_rate_24h`.

### 6) Fallback chain strategy

- Hypothesis: optimized fallback ordering improves success rate during provider incidents.
- Variant A: `fal -> openai`.
- Variant B: `openai -> fal` for selected operations.
- Primary metric: `render_success_rate`.
- Secondary metrics: `p95_latency`, `failed_job_rate`.

### 7) Tool-specific provider routing

- Hypothesis: tool-level routing (Paint/Floor/Exterior) improves outcome quality.
- Variant A: common provider per operation.
- Variant B: tool-specific provider map from dashboard config.
- Primary metric: `tool_completion_rate`.
- Secondary metrics: `share_rate`, `regeneration_rate`.

## Events required (must be instrumented)

- `paywall_impression`, `paywall_cta_tap`, `checkout_started`, `checkout_completed`, `refund`.
- `render_dispatched`, `render_status_updated`, `render_canceled`.
- `experiment_assignment` with `{experiment_id, variant_id}`.
- `tool_selected`, `preview_completed`, `final_completed`.

## Statistical decision framework

- Use two-sided test at 95% confidence.
- Require both:
  - statistical significance for primary metric.
  - no guardrail regression.
- If primary improves but guardrail worsens, reject or re-run with narrower targeting.

## Admin execution support

- Use `GET /v1/admin/experiments/{experiment_id}/performance?hours=168` to compare variant lift and p-value.
- Tune decision sensitivity with variables:
  - `experiment_significance_alpha` (default `0.05`)
  - `experiment_primary_metric_min_sample_size` (default `100`)
- Keep guardrail runs active via `POST /v1/admin/experiments/guardrails/evaluate`.

## Rollout plan after winner

1. Ramp winner to 10% global traffic.
2. Verify metrics for 48 hours.
3. Ramp to 50%.
4. Ramp to 100%.
5. Archive experiment with final report (hypothesis, data window, winner, impact).
