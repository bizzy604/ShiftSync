CREATE TABLE audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_id UUID NOT NULL REFERENCES users(id),
  action_type VARCHAR(60) NOT NULL,
  entity_type VARCHAR(60) NOT NULL,
  entity_id UUID NOT NULL,
  before_state JSONB,
  after_state JSONB,
  reason TEXT,
  location_id UUID REFERENCES locations(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_location_time
  ON audit_logs(location_id, created_at DESC);

CREATE INDEX idx_audit_entity
  ON audit_logs(entity_type, entity_id, created_at DESC);

CREATE INDEX idx_audit_actor
  ON audit_logs(actor_id, created_at DESC);
