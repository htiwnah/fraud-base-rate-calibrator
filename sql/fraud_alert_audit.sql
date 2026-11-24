CREATE TABLE IF NOT EXISTS fraud_verdicts (tx_id TEXT PRIMARY KEY, channel TEXT, outcome TEXT);
SELECT channel, COUNT(*) AS fp_count FROM fraud_verdicts WHERE outcome = 'FP' GROUP BY channel;
