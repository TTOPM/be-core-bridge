#!/bin/bash
# BELEL DAILY AUTONOMOUS TRAINING CRON JOB

cd /path/to/BELEL_DATABASE_ACADEMY

echo "$(date): Starting Belel daily autonomous training..."

# 1. Refresh training data
poetry run python src/belel_database_academy/pipelines/ingestion_pipeline.py --daily

# 2. Run autonomous training
poetry run python src/belel_database_academy/autopilot/daily_trainer.py

# 3. Evaluate and deploy best model
poetry run python src/belel_database_academy/pipelines/evaluation_pipeline.py --deploy-best

# 4. Update monitoring
poetry run python src/belel_database_academy/monitoring/prometheus_metrics.py --daily

echo "$(date): Daily training complete"
