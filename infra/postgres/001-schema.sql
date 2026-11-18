CREATE TABLE investigation_case (
  case_id UUID PRIMARY KEY,
  transaction_id CHAR(64) NOT NULL UNIQUE,
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'reviewed', 'closed')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE api_principal (
  principal_id TEXT PRIMARY KEY,
  role TEXT NOT NULL CHECK (role IN ('reader', 'analyst')),
  token_hash CHAR(64) NOT NULL UNIQUE,
  active BOOLEAN NOT NULL DEFAULT true
);
CREATE TABLE analyst_decision (
  decision_id UUID PRIMARY KEY,
  case_id UUID NOT NULL REFERENCES investigation_case(case_id),
  analyst_id TEXT NOT NULL REFERENCES api_principal(principal_id),
  outcome TEXT NOT NULL CHECK (outcome IN ('suspicious', 'legitimate', 'uncertain')),
  reason TEXT NOT NULL CHECK (length(reason) BETWEEN 1 AND 2000),
  version INTEGER NOT NULL CHECK (version > 0),
  idempotency_key UUID NOT NULL UNIQUE,
  request_hash CHAR(64) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (case_id, version)
);
CREATE INDEX analyst_decision_created_idx ON analyst_decision (created_at, decision_id);
CREATE TABLE audit_event (
  event_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  principal_id TEXT REFERENCES api_principal(principal_id),
  action TEXT NOT NULL,
  resource_id TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE api_quota (
  principal_id TEXT NOT NULL REFERENCES api_principal(principal_id),
  action TEXT NOT NULL,
  minute TIMESTAMPTZ NOT NULL,
  used INTEGER NOT NULL CHECK (used > 0),
  PRIMARY KEY (principal_id, action, minute)
);
