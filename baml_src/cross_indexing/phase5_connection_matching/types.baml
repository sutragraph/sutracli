// Connection Matching Types for Phase 5

class ConnectionMatch {
  incoming_id int
  outgoing_id int
  match_confidence string
  match_reason string
}

class ConnectionMatchingResponse {
  matches ConnectionMatch[]?
}
