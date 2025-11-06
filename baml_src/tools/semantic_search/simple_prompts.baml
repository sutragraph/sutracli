template_string SimpleSemanticSearchToolTemplate() #"
## semantic_search

Find similar implementations and patterns in the codebase using semantic similarity. It:
1. Takes in a natural language description of the code you are looking for;
2. Uses a proprietary retrieval/embedding model suite that produces the highest-quality recall of relevant code snippets from across the codebase;
3. Maintains a real-time index of the codebase, so the results are always up-to-date and reflects the current state of the codebase;
4. Can retrieve across different programming languages;
5. Only reflects the current state of the codebase on the disk, and has no information on version control or code history.
"#
