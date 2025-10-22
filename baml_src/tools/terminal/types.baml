class TermianlParams {
  command string @description("The one-liner command to execute.")
  cwd string? @description("Working directory for the command. This must be one of the root directories of the project.")
}
