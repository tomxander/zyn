# Sift

Requirements from a specification, each with the source words it came from.

**Input:** a specification as PDF, DOCX, Markdown or text.
**Output:** a reviewed requirement set as JSON, Excel and ReqIF, plus open questions for the spec author.

## How it works

1. The specification is converted and split into sections.
2. A model maps each section to a subsystem, then extracts requirements section by section. Every requirement carries the exact source words it came from.
3. Code checks each one: is the quote really in the section, was the modal verb kept, are there numbers the section never gives, are there vague words.
4. The AI reviewer checks each item against its section and says whether an objection concerns the text or only its labels.
5. A named person approves, rejects or edits each requirement.

Each section is claimed before extraction, so a second extraction of the same run (another tab, the command line) skips it.

## Clarification proposals

For requirements whose source wording is flagged (vague words, missing values), a model proposes testable wording. A value the source does not give comes back as a `<TBD: ...>` placeholder with a question for the spec author. A code check blocks any proposal that:

- invents a number
- changes "should" to "shall"
- keeps the vague word

Using a proposal counts as a human edit. Open questions go into the export.

## Commands

```powershell
.\.venv\Scripts\zyn sift start data\synthetic\icx100_srs.md
.\.venv\Scripts\zyn sift clarify <run>
.\.venv\Scripts\zyn sift export <run> --as NAME
```

Or use **Start new run** in the review screen.

Code: [harness/sift/](../../harness/sift/)
