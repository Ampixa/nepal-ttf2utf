# Repository instructions

## Priority 1: write public files for the public

README files, documentation, source comments, changelogs, release notes, and
other public repository content must address the repository's general audience.
They must not read like a reply to the repository owner or preserve private
conversation context.

- State project scope, evidence, limitations, and usage rules impersonally and
  self-sufficiently.
- Avoid owner-directed phrasing, conversational asides, and unexplained
  references such as "for you", "as requested", or "examined here".
- Keep user-specific preferences and working instructions in `AGENTS.md`, not
  in public-facing project documentation.
- Before committing documentation, read it as a first-time user with no access
  to agent conversations and revise anything that depends on that context.

## Publishing to the Ampixa blog

When work produces a benchmark result, dataset, release, or technical lesson
worth publishing on <https://ampixa.com/blog>, hand it to Bemine for review,
style validation, and deployment. Lead with the concrete artifact, tie every
claim to a repository, dataset, or benchmark link, and avoid hype.

Pipe the Markdown draft to the orchestrator on `cdjk`:

```sh
cat draft.md | ssh cdjk 'cd ~/bm && ~/.local/bin/uv run bemine blog submit - --title "<title>" --project <project> --author <session-name>'
```

This queues the draft and notifies `#ampixa-blog` on Discord. Never publish a
post directly.
