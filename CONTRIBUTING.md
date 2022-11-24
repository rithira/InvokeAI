# Contributing

## Contribution Domains

### Web UI

We welcome contributions to the web UI, but request that you read through this
section before hacking on anything in it.

#### Frontend Stack

The web UI is a single-page React app written in Typescript:

- Redux (via Redux Toolkit)
- Chakra UI (plus a component or two with Radix UI)
- SCSS with some of Chakra's style props for layout

We hope to move to a fully headless UI library at some point (e.g. Radix) but
haven't made any significant process yet.

Similarly, we want to use a CSS-in-JS solution (Chakra's system if we stick with
it, or Stitches if we move to Radix) but have focused on getting the MVP out of
the door so far. SCSS was chosen because we hoped it would be more approachable
for contributors, but we are getting held back by it at this point.

#### Server Stack

The server is a Flask app using mostly socket.io for communication. It uses
InvokeAI's `Generate()` class directly; it does not send commands to the CLI
(the CLI also uses `Generate()` directly).

The server is mostly a placeholder until we our proper backend system is in
place (see [#1047](https://github.com/invoke-ai/InvokeAI/pull/1047)). It is ugly
but it works fine for now.

#### Workflow

InvokeAI has a main branch (final releases) and development branch (WIP and
release candidates). Development is merged into main when we are ready to
release a new version.

For work on the Web UI, somebody (usually @psychedelicious) creates a PR against
development for the next release and work on the Web UI takes place against that
PR branch, either via PRs or direct commits (only feasible because there are
just a couple of us who work on it).

#### How to Contribute

If you want to add a feature, improve, or fix something, please check in with us
first before doing any work, either on discord (make a topic in
[contributor-forums](https://discord.com/channels/1020123559063990373/1020839344170348605))
or by creating a feature request on Github and tagging @psychedelicious and
@blessedcoolant.

We do not want to reject any contributions for any of these reasons:

- The PR was against main or development, but we were working from a different
  branch which has diverged substantially, and so it is more work to rebase the
  code than it is to just re-implement it.
- The PR did not meet our style or code standards.
- The PR does not align with our vision for the project and the difference is
  irreconciliable.
- The PR is a duplicate of existing work of which the contributor was unaware.

So, please make contact first. We are very responsive and just quickly checking
in will ensure your time and energy (thank you!) does not go to waste.
