# Android API Notes

Use backend bootstrap endpoint at app launch to configure:
- active plans,
- daily limit behavior,
- provider defaults and fallback metadata.

Render flow:
1. Create job (`POST /v1/ai/render-jobs`)
2. Poll status (`GET /v1/ai/render-jobs/{job_id}`)
3. Cancel job if user exits (`POST /v1/ai/render-jobs/{job_id}/cancel`)
4. Send analytics event (`POST /v1/analytics/events`)
