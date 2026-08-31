# Disaster Recovery & Emergency Protocols

## Critical Recovery Scenarios

### Scenario A: Model Corruption / Bad Deployment
- **Symptom**: Spikes in false-positive submissions or degraded accuracy.
- **Immediate Mitigation**: Activate the Kill Switch by setting `AUTO_RESPOND_CONFIDENCE = 1.0` in `response_generator.py` or via environment variable.
- **Effect**: 100% of incoming disputes are routed to `HUMAN_REVIEW`. No automated representments are submitted.

### Scenario B: Database Storage Failure
- **Symptom**: SQLite database locked or corrupted.
- **Immediate Mitigation**: The API layer catches DB exceptions gracefully and continues to process and return response packages to webhooks.
- **Recovery**: Restore `data/chargebacks.db` from backup or run `init_db()` to recreate schema.

### Scenario C: High Volume / Denial of Service
- **Symptom**: High incoming dispute traffic causing Vercel serverless timeout.
- **Mitigation**: Scale serverless execution concurrency via Vercel dashboard; rate-limit endpoints.
