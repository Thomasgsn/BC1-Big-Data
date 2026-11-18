-- Fixtures synthétiques exclusivement transactionnelles : toutes les insertions sont annulées.
\set ON_ERROR_STOP on
BEGIN;
SELECT gen_random_uuid() AS case_id \gset
SELECT set_config('bc1.test_case', :'case_id', true);
INSERT INTO investigation_case (case_id, transaction_id)
VALUES (:'case_id', encode(sha256(convert_to(:'case_id', 'UTF8')), 'hex'));
DO $$
DECLARE test_case UUID := current_setting('bc1.test_case')::uuid;
BEGIN
  IF NOT has_table_privilege('bc1app', 'investigation_case', 'INSERT') THEN
    RAISE EXCEPTION 'Droit applicatif attendu absent';
  END IF;
  IF has_table_privilege('bc1app', 'api_principal', 'INSERT') THEN
    RAISE EXCEPTION 'Privilège applicatif excessif';
  END IF;
  BEGIN
    INSERT INTO investigation_case (case_id, transaction_id)
    SELECT case_id, transaction_id FROM investigation_case WHERE case_id = test_case;
    RAISE EXCEPTION 'Doublon accepté';
  EXCEPTION WHEN unique_violation THEN NULL;
  END;
  BEGIN
    INSERT INTO analyst_decision (decision_id,case_id,analyst_id,outcome,reason,version,idempotency_key,request_hash,created_at) VALUES (gen_random_uuid(), gen_random_uuid(), 'demo-analyst', 'uncertain',
      'Fixture synthétique FK', 1, gen_random_uuid(), repeat('a',64), now());
    RAISE EXCEPTION 'Référence absente acceptée';
  EXCEPTION WHEN foreign_key_violation THEN NULL;
  END;
  BEGIN
    INSERT INTO analyst_decision (decision_id,case_id,analyst_id,outcome,reason,version,idempotency_key,request_hash,created_at) VALUES (gen_random_uuid(), test_case, 'demo-analyst', 'uncertain',
      '', 1, gen_random_uuid(), repeat('a',64), now());
    RAISE EXCEPTION 'Motif vide accepté';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
  INSERT INTO analyst_decision (decision_id,case_id,analyst_id,outcome,reason,version,idempotency_key,request_hash,created_at) VALUES (gen_random_uuid(), test_case, 'demo-analyst', 'uncertain',
    'Fixture synthétique valide ; sera annulée', 1, gen_random_uuid(), repeat('a',64), now());
END $$;
ROLLBACK;
SELECT 'postgres_constraints_and_rollback_passed' AS event;
