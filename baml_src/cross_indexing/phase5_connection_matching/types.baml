// Connection Matching Types for Phase 5

class ConnectionMatch {
  incoming_id string
  outgoing_id string
  match_confidence string
  match_reason string
}

class ConnectionMatchingResponse {
  matches ConnectionMatch[]?
}
