CREATE TYPE swap_request_type AS ENUM ('swap', 'drop');
CREATE TYPE swap_request_status AS ENUM (
  'OPEN',
  'PENDING_ACCEPTEE',
  'PENDING_MANAGER',
  'APPROVED',
  'REJECTED',
  'CANCELLED',
  'EXPIRED'
);

CREATE TABLE swap_requests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  type swap_request_type NOT NULL,
  requester_assignment_id UUID NOT NULL REFERENCES shift_assignments(id) ON DELETE CASCADE,
  target_user_id UUID REFERENCES users(id),
  candidate_assignment_id UUID REFERENCES shift_assignments(id) ON DELETE CASCADE,
  pickup_user_id UUID REFERENCES users(id),
  status swap_request_status NOT NULL DEFAULT 'PENDING_ACCEPTEE',
  initiated_by UUID NOT NULL REFERENCES users(id),
  expires_at TIMESTAMPTZ,
  resolved_at TIMESTAMPTZ,
  resolved_by UUID REFERENCES users(id),
  resolution_note TEXT,
  version INTEGER NOT NULL DEFAULT 1,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT chk_swap_request_target CHECK (
    (type = 'swap' AND target_user_id IS NOT NULL)
    OR
    (type = 'drop' AND target_user_id IS NULL)
  )
);

CREATE INDEX idx_swap_status ON swap_requests(status);
CREATE INDEX idx_swap_target ON swap_requests(target_user_id);
CREATE INDEX idx_swap_expires ON swap_requests(expires_at);
CREATE INDEX idx_swap_initiated_by ON swap_requests(initiated_by);

CREATE TABLE notifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  type VARCHAR(60) NOT NULL,
  message TEXT NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  read_at TIMESTAMPTZ
);

CREATE INDEX idx_notif_user_created ON notifications(user_id, created_at DESC);
CREATE INDEX idx_notif_unread ON notifications(user_id, read_at)
  WHERE read_at IS NULL;
