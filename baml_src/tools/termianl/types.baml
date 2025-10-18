class TermianlParams {
  command string @description("The command to be executed in the terminal")
  cwd string? @description("Current working directory for command execution defaults to agent's cwd")
}
