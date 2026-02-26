CREATE TYPE shift_status AS ENUM ('draft', 'published', 'cancelled');
CREATE TYPE assignment_status AS ENUM ('assigned', 'swap_pending', 'dropped', 'removed');

CREATE TABLE shifts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  location_id UUID NOT NULL REFERENCES locations(id),
  required_skill_id UUID NOT NULL REFERENCES skills(id),
  shift_date DATE NOT NULL,
  start_utc TIMESTAMPTZ NOT NULL,
  end_utc TIMESTAMPTZ NOT NULL,
  headcount_needed INTEGER NOT NULL DEFAULT 1 CHECK (headcount_needed >= 1),
  status shift_status NOT NULL DEFAULT 'draft',
  week_start DATE NOT NULL,
  published_at TIMESTAMPTZ,
  edit_cutoff_utc TIMESTAMPTZ,
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT chk_shift_times CHECK (end_utc > start_utc)
);

CREATE INDEX idx_shifts_location_week ON shifts(location_id, week_start);
CREATE INDEX idx_shifts_location_date ON shifts(location_id, shift_date);
CREATE INDEX idx_shifts_start_utc ON shifts(start_utc);
CREATE INDEX idx_shifts_status ON shifts(status);

CREATE TABLE shift_assignments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  shift_id UUID NOT NULL REFERENCES shifts(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id),
  status assignment_status NOT NULL DEFAULT 'assigned',
  version INTEGER NOT NULL DEFAULT 1,
  assigned_by UUID NOT NULL REFERENCES users(id),
  override_reason TEXT,
  assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (shift_id, user_id)
);

CREATE INDEX idx_assignments_user ON shift_assignments(user_id);
CREATE INDEX idx_assignments_shift ON shift_assignments(shift_id);
CREATE INDEX idx_assignments_user_active ON shift_assignments(user_id, status)
  WHERE status = 'assigned';
