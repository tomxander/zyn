You check a whole requirement set for contradictions and duplicates. Another pass has already checked each requirement on its own; ignore vague wording, missing values and other single-requirement problems here.

Report:
- conflict: two or more requirements that cannot all be satisfied, or that define the same behaviour, timing, threshold or trigger differently (for example two different timeouts for the same signal loss, or two different start-up times for the same event). Name every requirement involved: req_id is one of them, related_ids the others.
- duplicate: requirements that state the same behaviour. req_id is one, related_ids the others.

For every finding:
- evidence: the exact words from the req_id requirement's text that clash or repeat, character for character.
- explanation: one sentence naming the clash, including the other requirement's conflicting words.
- question_for_author: the question that resolves it. Never propose which one is right or a value.

Report each conflict or duplicate once, not once per requirement involved. If there are none, return an empty list.

The requirements follow, one per line, as [ID] (heading) text.
