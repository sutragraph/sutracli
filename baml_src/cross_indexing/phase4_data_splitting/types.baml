enum TechnologyType {
  HTTP_HTTPS @alias("HTTP/HTTPS")
  WebSockets
  GRPC @alias("gRPC")
  GraphQL
  MessageQueue
  Unknown
  @@dynamic
}

class ConnectionDetail {
  snippet_lines string
  description string
}

class ConnectionSplittingResponse {
  incoming_connections map<TechnologyType, map<string, ConnectionDetail[]>>?
  outgoing_connections map<TechnologyType, map<string, ConnectionDetail[]>>?
  summary string?
}
