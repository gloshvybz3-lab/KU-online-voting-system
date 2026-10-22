-- Non-destructive production hardening for the existing KU-OVS schema.
-- Apply with your migration runner, not at application startup.

-- MySQL 8+: add indexes used by election administration and tabulation.
CREATE INDEX idx_elections_status_window ON elections (status, start_time, end_time);
CREATE INDEX idx_positions_election_order ON positions (election_id, priority_order);
CREATE INDEX idx_candidates_election_position_status ON candidates (election_id, position_id, status);
CREATE INDEX idx_votes_election_position ON votes (election_id, position_id);
CREATE INDEX idx_participation_election_voted_at ON voter_participation (election_id, voted_at);
CREATE INDEX idx_audit_created_action ON audit_logs (created_at, action);
