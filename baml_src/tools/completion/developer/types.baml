class DeveloperCompletionParams {
  give_up bool @description("True if abandoning the task due to blockers or missing information; false if successfully completing the request")
  result string @description("A short summary of the changes you have made to the files or clarification on giving up")
}
