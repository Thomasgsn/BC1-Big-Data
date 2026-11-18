-- psql lit les secrets depuis son environnement, sans arguments ni script exécutable monté.
\getenv app_password POSTGRES_APP_PASSWORD
\getenv reader_token API_TOKEN_READER
\getenv analyst_token API_TOKEN_ANALYST
SELECT format('CREATE ROLE bc1app LOGIN PASSWORD %L', :'app_password')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'bc1app') \gexec
GRANT CONNECT ON DATABASE bc1 TO bc1app;
GRANT USAGE ON SCHEMA public TO bc1app;
GRANT SELECT ON api_principal TO bc1app;
GRANT SELECT, INSERT, UPDATE ON investigation_case, api_quota TO bc1app;
GRANT SELECT, INSERT ON analyst_decision TO bc1app;
GRANT SELECT, INSERT ON audit_event TO bc1app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO bc1app;
INSERT INTO api_principal VALUES
  ('demo-reader', 'reader', encode(sha256(convert_to(:'reader_token', 'UTF8')), 'hex'), true),
  ('demo-analyst', 'analyst', encode(sha256(convert_to(:'analyst_token', 'UTF8')), 'hex'), true)
ON CONFLICT (principal_id) DO NOTHING;
