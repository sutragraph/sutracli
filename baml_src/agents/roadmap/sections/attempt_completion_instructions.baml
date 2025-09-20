template_string AttemptCompletionInstructions() #"
## DECISION TREE: Evaluate Before Completion
Think: 'Type? Traced? Analyzed?'

1. For greeting/info: Use attempt_completion(result: 'Response').
2. For impl/bug/change: Ensure full tracing first.

Check all elements: needs=[] & traced=true? All internals traced? Multi-probs/projects all? Relevance: All needs query-relevant, <20 total?
Pre-call: Memory audit – for each: needs empty & traced=true? All to finals, no partials, matches history (e.g., all bugs)?

Proceed only if yes: attempt_completion(projects:[...], summary:'...').
Example: 'Found func → Trace internals first.'
"#
