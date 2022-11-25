# Would you like to help?

InvokeAI is an open source application licensed under the MIT license. With the help of community input and contributions, it is being developed by a core team of people from varied artistic and professional backgrounds, including fine arts, software development, videogame development, and design and creative industries. We have a clear vision for what we want InvokeAI to be, but we will always welcome input from contributors, whether to support our efforts or to offer different skills or different ideas to complement our project and direction.

There are a number of different pathways in to contributing. You don't need to know how to code &mdash; there are plenty of other things that we could use help with &mdash; but of course code contributions are always welcome, too. If you'd be interested in contributing to the project in the longer term, perhaps even joining the core team, you can get started on this path by helping us out with something concrete. That way we can begin to get to know you, and you can begin to get to know us, and we can all better decide if we want to work together in the longer term.

<a name="talk-to-us"></a>
## If you'd like to talk first

The best way to reach us is to join our discord (link on [the front page](https://github.com/invoke-ai)) and write to us there, either by posting a message in [#invoke-chat](https://discord.com/channels/1020123559063990373/1020123559831539744), or if you have a more concrete idea you want to walk through, you can open a new thread under [💬﹚Contributor Forums](https://discord.com/channels/1020123559063990373/1020839344170348605). We are an international team with members in very different timezones, so we may not reply immediately. We do try to read and respond to all messages in a timely manner but if it's been a day or two and nobody has responded, please ping someone on the list below.

If you like, you can approach one of the section specialists directly:
* For .ckpt loading, the `invoke>` CLI, documentation, safety, and diffusion engineering: **@lstein**
* For community and product management, and non-engineering enquiries: **@hipsterusername** 
* For prompting, training, performance, macOS compatibility, and diffusion engineering: **@damian0815**
* For installers: **@tildebyte**
* For CI/CD and devops: **@mauwii**
* For invoke web server and incoming node-based UI: **@Kyle0654**
* For the web UI design and engineering: **@psychedelicious** or **@blessedcoolant**
* For design work more generally: **@netsvetaev**

Or, if you're unsure, or you just want someone to talk with you through your idea, I'm available on Discord as **@damian0815** to chat, publicly or privately, as you prefer. I know from my own experience that the initial approach to an open source project can sometimes be confusing and a even little nerve-wracking, and I would be happy to do whatever I can make it easier for you to help us out. 

## What you can contribute

### Documentation, guides, and tutorials

Everybody likes better documentation. You can edit the documentation [right here on GitHub](https://github.com/invoke-ai/InvokeAI/tree/main/docs) - click through to one of the `.md` files and click the edit button on the top right (looks like a pencil). After saving your edits you'll be prompted to enter a commit message and open a pull request. Feel free to [ask for help in Discord](#talk-to-us) if you get stuck.

If you want to make a user guide or tutorial, or a video about how you're using InvokeAI, we would love that &mdash; please [tell us about it](#talk-to-us)! We will be more than happy to share the link on our Discord and other social media. 

### Design and styling

Although the Web UI design is being handled entirely within the team by our own very talented designers, we're always looking for help illustrating, designing, and styling for other parts of the project, such as our documentation and website, to make it even more attractive and welcoming for everyone. If you'd like to contribute style guides, graphic design, typography or layout suggestions, please [reach out to us on Discord](#talk-to-us) &mdash; **@netsvetaev** is the person you most likely want to talk to.  

### Artist Outreach

Our vision for InvokeAI is to make it the best possible tool for artists to use Stable Diffusion and related technologies like a digital paintbrush: a sophisticated but very usable tool to have at hand in their artistic toolbox. We are always looking for feedback and collaboration with artists and other creative folk. [Reach out to us on Discord](#talk-to-us) and show us how you're using InvokeAI, to help us to make it a better tool for you.

### QA and devops

Stable Diffusion is an immensely complicated system that is moving at a breakneck pace, and good testing is critical to ensure that we are able to maintain a high quality codebase and user experience. We will always welcome help with testing, from helping us test out pre-release code to building automated testing systems that ensure we don't break things as we continue to move forward. We always announce new pre-release test code on the Discord, but if you would like to help out with specific QA or testing improvements, please [reach out to us on Discord](#talk-to-us).        

## If you just want to just get stuck into writing code

### Fix a bug

Bugfixes are always welcome. Check out [the InvokeAI bug tracker](https://github.com/invoke-ai/InvokeAI/issues) for open bugs, and see if you might be interested in fixing them. If you want to pick one up, please leave a comment and ideally tag the section specialist for the bug you're looking at, or you can tag me @damian0815 right in the GitHub comment if you don't know who that might be.

### Implement a new features

If you've got an awesome feature you'd like to contribute, that's great! Please [open a feature request](https://github.com/invoke-ai/InvokeAI/issues/new?assignees=&labels=enhancement&template=FEATURE_REQUEST.yml&title=%5Benhancement%5D%3A+) to propose your idea, just to ensure that we understand what you want to do and that it doesn't overlap with work that is already in progress. We strongly suggest however that you take the time to [talk to us](#talk-to-us) about what you want to do before spending too much time on something.

### Making a Pull Request

If you're new to using git, we can help out. We do require some standards for pull requests, but we will of course be able to help you get your pull request into the right shape before we accept it.

As is usual on GitHub, we accept code contributions primarily through [Pull Requests](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-pull-requests). The code will be reviewed, and although we are thankful for any contributions, it's very likely you'll get some feedback about your work and you may have to change things. This is the way that we ensure that the code quality remains as high as we can make it, across the whole project.

The following are some basic things that we will be looking out for in submitted Pull Requests:

- The PR (Pull Request) was made against the appropriate branch, usually `development`, and has been kept in sync with the parent branch as much as possible. 
  - This is to avoid merge conflicts and the need for heavy rebasing work.
    - InvokeAI has a `main` branch (final releases) and `development` branch (WIP and
  release candidates). `development` is merged into `main` when we are ready to
  release a new version.
- The code meets our style and quality standards. 
  - We will provide constructive feedback if needed to help you achieve this.
- The PR does not duplicate of existing work.
  - Not all of the development and planning of InvokeAI happens on publically visible forums. This is one reason why it's best to talk to us first before putting in too much effort. 
- The PR is in line with where we want InvokeAI to be headed. 
  - If the difference is minor we can of course help you resolve it. This is another reason why it's best to talk to us first.

So, please [make contact](#talk-to-us) first. We are very responsive and just quickly checking in will ensure your time and energy (thank you!) does not go to waste.


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

For work on the Web UI, somebody (usually @psychedelicious) creates a PR against
development for the next release and work on the Web UI takes place against that
PR branch, either via PRs or direct commits (only feasible because there are
just a couple of us who work on it).
