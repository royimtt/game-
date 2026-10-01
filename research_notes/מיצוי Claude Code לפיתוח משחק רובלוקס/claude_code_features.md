# Claude Code features, settings, and model/effort options for maximum output quality (state as of October 1, 2026)

Research date: October 1, 2026. The current Claude Code release is v2.1.286 (Sept 30, 2026) ([Changelog](https://code.claude.com/docs/en/changelog)). Most sources are the official Claude Code docs (code.claude.com), the Claude Platform docs (platform.claude.com), Anthropic engineering posts, one Claude blog post, and one Claude Help Center article. Version requirements are given as stated in the docs. A few Roblox-side facts come from Roblox's official creator-docs repo, because the user's MCP server is Roblox Studio.

---

## 1. Models and effort: what is available, what Anthropic recommends for maximum quality, how effort / `ultrathink` / `ultracode` work, where higher effort stops helping, and plan/billing caveats

### Takeaway
On a Pro plan, Claude Code starts on **Opus 5.5 at `medium` effort**. Anthropic's official advice is to start most work on Opus 5.5 and move to **Fable 5.1** (the most capable model, built for multi-hour autonomous work) only when Opus at `xhigh`/`max` still falls short.

On **Pro, every Fable request bills to pay-as-you-go usage credits**. Max includes Fable at up to 50% of the weekly limit. Effort controls how much work Claude does overall, not just how long it thinks. Anthropic's rule of thumb:
- If Claude "didn't try hard enough" (skipped a file, didn't run the tests), raise effort.
- If it "didn't know enough", use a bigger model.

Two more points:
- `max` is session-only and the docs warn it "may show diminishing returns and is prone to overthinking".
- `ultrathink` is a one-turn nudge added to the prompt; it doesn't change the effort sent to the API. `ultracode` is a separate setting that has Claude orchestrate multi-agent dynamic workflows, at a large token cost.

### Cited Findings

**Available models and aliases**
- Aliases in Claude Code:
  - `default`: clears overrides.
  - `best`: what `fable` resolves to where Fable is available, otherwise `opus`.
  - `fable`: "for your hardest and longest-running tasks".
  - `sonnet`: daily coding.
  - `opus`: "complex reasoning tasks".
  - `haiku`: simple tasks.
  - `sonnet[1m]`, `opus[1m]`: 1M context.
  - `opusplan`: Opus in plan mode, then Sonnet for execution.
  
  — [Model configuration](https://code.claude.com/docs/en/model-config)
- On the Anthropic API, `opus` → **Opus 5.5** and `sonnet` → **Sonnet 5.5**. Unless `ANTHROPIC_DEFAULT_FABLE_MODEL` is set, `fable` → **Fable 5.1** (Fable 5 in Claude apps gateway sessions). To pin a version, use the full ID, e.g. `claude-opus-5-5`. — [Model configuration](https://code.claude.com/docs/en/model-config)
- Minimum versions: Sonnet 5.5 needs v2.1.284+, Opus 5.5 needs v2.1.280+, Fable 5.1 needs v2.1.257+. Run `claude update` to upgrade. — [Model configuration](https://code.claude.com/docs/en/model-config)
- `default` resolves to **Opus 5.5 on Pro**, Max, Team, Enterprise and the API. Before v2.1.280 it resolved to Sonnet 5 on Pro and Team Standard. Fable is not the default on any plan; select it with `/model fable` or `claude --model fable`. — [Model configuration](https://code.claude.com/docs/en/model-config)
- Fable 5.1 and Fable 5 "are the most capable models in Claude Code, suited to tasks larger than a single sitting. They sustain long autonomous sessions, investigate before acting, and verify their work more often than smaller models." Official tips for Fable:
  - "Describe the outcome, not the steps", and set a goal with `/goal`.
  - "Hand it ambiguous problems" (root-cause investigations, architecture decisions).
  - "Skip the verification reminders".
  - "Size up larger tasks".
  
  — [Model configuration](https://code.claude.com/docs/en/model-config)
- Choosing a model (platform docs): "Most workloads start with Claude Opus 5.5". Fable 5.1 is for "The highest available capability", e.g. "Agent sessions that run for hours". The capability-first path is to implement with Opus 5.5, and "If your evals at `xhigh` or `max` effort still fall short on demanding reasoning or long-horizon agentic work, move to Claude Fable 5.1." — [Choosing a model](https://platform.claude.com/docs/en/about-claude/models/choosing-a-model)
  - **Conflict:** Fable 5.1's "What's new" page still says "For most workloads, start with Claude Opus 5". It appears to predate the Opus 5.5 launch and is stale. — [What's new in Fable 5.1](https://platform.claude.com/docs/en/models/fable-5-1/whats-new-fable-5-1); contradicted by [Choosing a model](https://platform.claude.com/docs/en/about-claude/models/choosing-a-model)
- Model specs and API prices:

  | Model | Input / output per MTok | Other |
  | --- | --- | --- |
  | Fable 5.1 | $10 / $50 | Cache reads $0.25/MTok. 1M context window, 128k max output. Tokenizer produces ~30% more tokens than models before Opus 4.7. |
  | Opus 5.5 | $4 / $20 | Cache reads $0.20/MTok. "more than 30 percent faster than Claude Opus 5" at generating output, and "tends to finish the same task with fewer tokens". |

  Sources: [What's new in Fable 5.1](https://platform.claude.com/docs/en/models/fable-5-1/whats-new-fable-5-1); [What's new in Opus 5.5](https://platform.claude.com/docs/en/models/opus-5-5/whats-new-opus-5-5); [Prompting Opus 5.5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5)

**Plan and billing caveats (important for a Pro user)**
- Official Help Center wording:
  - Pro: "On Pro plans, standard seats on Team plans, and standard seats on seat-based Enterprise plans, Fable models run on pay-as-you-go usage credits from the start, since they aren't included in your plan's usage limits."
  - Max: Fable 5/5.1 are included and you "can use up to 50% of your weekly usage limits on Fable models at no extra cost".
  - The one-time credit for the July 2026 change "applied to the Fable 5 change only… no equivalent credit for Fable 5.1". The rules are the same in Claude Code.
  
  — [Claude Fable models on your plan](https://support.claude.com/en/articles/15424964-claude-fable-models-on-your-plan)
- In Claude Code, the `/model` picker shows "Requires usage credits" on the Fable row, and an interactive consent prompt appears before Fable bills credits.
  - In background, agent-team or Remote Control sessions, the prompt waits `dialogExpiry` (5 minutes by default). If nobody answers, the turn ends without sending.
  - In `-p` (headless) mode, Claude Code "bills it without asking".
  
  — [Model configuration](https://code.claude.com/docs/en/model-config)
- Session and weekly limits are shared across all models, so switching models doesn't restore access. Opus and Sonnet limits apply per family. "A single burst of heavy activity, such as a large workflow fanout, can exhaust the weekly allowance before the session window resets." — [Errors: usage limits](https://code.claude.com/docs/en/errors)
- Other paid extras on subscriptions:
  - Fast mode (up to 2.5x faster, higher cost per token, not higher quality) is "available via usage credits only" — [Fast mode](https://code.claude.com/docs/en/fast-mode)
  - `/ultrareview` "Includes 3 free runs on Pro and Max, then requires usage credits" — [Commands](https://code.claude.com/docs/en/commands)

**How effort works**
- Effort controls adaptive reasoning, which "lets the model decide whether and how much to think on each step". Levels per model:
  - Fable 5.1/5, Opus 5.5, Sonnet 5.5, Opus 5, Sonnet 5, Opus 4.8 and 4.7: `low`, `medium`, `high`, `xhigh`, `max`.
  - Opus 4.6 and Sonnet 4.6: `low`, `medium`, `high`, `max`.
  - Models not listed, such as Haiku 4.5, don't support effort.
  
  — [Model configuration](https://code.claude.com/docs/en/model-config)
- Default effort in Claude Code: `high` on every model that supports effort, except Opus 5.5 and Sonnet 5.5 (`medium`) and Opus 4.7 (`xhigh`). — [Model configuration](https://code.claude.com/docs/en/model-config)
  - **Note:** the platform effort doc says `high` is Sonnet 5.5's default *on the Claude API*. Claude Code's default for it is `medium`. — [Effort](https://platform.claude.com/docs/en/build-with-claude/effort)
- Claude Code's official per-level guidance:

  | Level | When to use it |
  | --- | --- |
  | `low` | "Quick exchanges where you review each result". |
  | `medium` | "day-to-day engineering work with a clear scope". |
  | `high` | "Work where verification matters or edge cases are likely, such as fixing a bug in an existing codebase". |
  | `xhigh` | "Deeper reasoning at higher token spend". |
  | `max` | "Hard problems you want Claude to work through without you… `max` may show diminishing returns and is prone to overthinking, so test before adopting it broadly". |
  
  — [Model configuration](https://code.claude.com/docs/en/model-config)
- "In tests on Opus 5.5 and Fable 5.1, Claude at a higher level tested more edge cases and verified more of its work before answering. It also made more choices on its own. At a lower level, Claude returned a starting point sooner." Also: "The effort scale is calibrated per model". — [Model configuration](https://code.claude.com/docs/en/model-config)
- "In Anthropic's testing, Opus 5.5 at `medium` matches or exceeds Opus 5 at `high`". "At a given level, Opus 5.5 tends to think more per turn than Opus 5". — [Model configuration](https://code.claude.com/docs/en/model-config)
- Platform effort doc:
  - `xhigh` is aimed at "Long-running agentic and coding tasks (over 30 minutes) with token budgets in the millions".
  - "Effort is a behavioral signal, not a strict token budget".
  - Effort affects all output tokens, tool calls included. Higher effort means more tool calls, plans explained first, and detailed summaries.
  - For Fable 5.1: "Start with `high`, the default. Step up to `xhigh` or `max` for the most capability-sensitive agentic and coding work".
  
  — [Effort](https://platform.claude.com/docs/en/build-with-claude/effort)
- Opus 5.5 guide: "Reserve `xhigh` and `max` for work where you've measured a quality gain", and "To get less thinking, lower the effort level first". — [Prompting Claude Opus 5.5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5)

**Where higher effort stops helping (overthinking)**
- Fable 5.1 at `xhigh`/`max` "may draft much of that deliverable in its thinking and then write it out again as the reply, which means a longer wait and more output tokens". The guide says to run such requests at `high`. — [Prompting Claude Fable 5.1](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-1)
- Sonnet 5.5 at `xhigh`/`max`: "After it finishes a task, it can start its own rounds of review and verification… It can also make related fixes it noticed along the way". Routine work should run at `high` or below. — [Prompting Claude Sonnet 5.5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5-5)
- For Opus 4.7 (an older model), `max` "adds significant cost for relatively small quality gains, and on some structured-output or less intelligence-sensitive tasks it can lead to overthinking". — [Effort](https://platform.claude.com/docs/en/build-with-claude/effort)
- Claude blog (Claude Code team):
  - "for most tasks you should use the model's default effort level".
  - Higher effort "generally won't artificially inflate usage for simple tasks", and "our team pays close attention to 'overthinking' during model training as it degrades effectiveness".
  - Effort "controls how much work Claude does on your request overall including the number of files read, tools used, and how many steps it takes before it checks back in with you".
  
  — [Choosing a Claude model and effort level in Claude Code](https://claude.com/blog/claude-model-and-effort-level-in-claude-code)
- Same post, on what to change: "If Claude has all the pertinent context, clearly tried, and still got it wrong, that's a signal to pick a more capable model. If Claude got it wrong by skipping a file, not running the tests, or bailing on a refactor partway through, pick a higher effort level." The first instinct should be to "examine the context you have provided". Fable "finished jobs Opus and Sonnet can't reach at any effort level". — [Claude blog](https://claude.com/blog/claude-model-and-effort-level-in-claude-code)

**Setting effort in Claude Code**
- Resolution order:
  1. An explicit choice: `CLAUDE_CODE_EFFORT_LEVEL`, `--effort`, or `/effort`.
  2. Saved settings: per-model `modelSettings` or `effortLevel`.
  3. The model default.
  
  A top-level `effortLevel` in user settings "doesn't count for Opus 5.5". — [Model configuration](https://code.claude.com/docs/en/model-config)
- Other effort controls:
  - In the `/effort` slider or `/model` picker, `Enter` saves the level as your default; `s` applies it to this session only (v2.1.257+).
  - `/effort auto` clears the saved level for the active model.
  - **`max` lasts for the current session only unless set through `CLAUDE_CODE_EFFORT_LEVEL`.** `max` isn't accepted in the `effortLevel` or `modelSettings` keys.
  
  — [Model configuration](https://code.claude.com/docs/en/model-config)
- Skill and subagent frontmatter can set `effort`, which overrides the session level while that skill or subagent is active (but not the env var). `maxEffortLevel` caps all sources. — [Model configuration](https://code.claude.com/docs/en/model-config); [Settings reference](https://code.claude.com/docs/en/settings-reference)
- On most models, changing effort mid-session recomputes the whole request (each level has its own cache). "On Opus 5.5, Sonnet 5.5, and Fable 5.1 with an API key or a Claude subscription, the cache stays intact by default." — [Prompt caching](https://code.claude.com/docs/en/prompt-caching)

**`ultrathink` and thinking controls**
- "Include `ultrathink` anywhere in your prompt to request deeper reasoning on that turn without changing your session effort setting. Claude Code recognizes the keyword and adds an in-context instruction. The effort level sent to the API is unchanged." Phrases like "think", "think hard" and "think more" are passed through as ordinary prompt text, not keywords. — [Model configuration](https://code.claude.com/docs/en/model-config)
- Thinking can't be turned off on Opus 5.5, Sonnet 5.5 or the Fable models, which always use adaptive reasoning. "If you want Claude to think more or less often than the current level produces, you can say so directly in your prompt or in `CLAUDE.md`." — [Model configuration](https://code.claude.com/docs/en/model-config)
- Thinking display and billing:
  - `Alt+T` (Windows/Linux) toggles thinking per session on models that allow it.
  - `Ctrl+O` shows the reasoning.
  - Set `showThinkingSummaries: true` to see full summaries.
  - "You are charged for all thinking tokens generated, even when collapsed or redacted."
  
  — [Model configuration](https://code.claude.com/docs/en/model-config)

**`ultracode` / dynamic workflows**
- Ultracode "is a Claude Code setting rather than a model effort level: with it on, Claude orchestrates dynamic workflows for substantive tasks". Ways to turn it on:
  - `/effort ultracode` (session only; `/effort ultracode off` needs v2.1.284+).
  - `claude --effort ultracode` (also sets `xhigh`; v2.1.203+).
  - `"ultracode": true` in settings.
  
  It is unavailable when workflows are turned off or the model doesn't support `xhigh`. — [Model configuration](https://code.claude.com/docs/en/model-config); [Settings reference](https://code.claude.com/docs/en/settings-reference)
- Cost and scope: "A single request can turn into several workflows in a row: one to understand the code, one to make the change, and one to verify it… each request uses more tokens and takes longer… a session with ultracode on reaches a session or weekly limit sooner." To run a single task as a workflow, put the keyword `ultracode` in that prompt; it only triggers in prompts you type, not in `-p`. — [Workflows](https://code.claude.com/docs/en/workflows)
- "On Pro, turn them [dynamic workflows] on from the Dynamic workflows row in `/config`." — [Workflows](https://code.claude.com/docs/en/workflows)

**Other model-level levers**
- `opusplan` uses Opus in plan mode and Sonnet for execution. Each plan-mode toggle is a model switch and starts a fresh cache. — [Model configuration](https://code.claude.com/docs/en/model-config); [Prompt caching](https://code.claude.com/docs/en/prompt-caching)
- Advisor tool (experimental):
  - `/advisor opus|fable`, the `advisorModel` setting, or `--advisor`. Claude consults a stronger model "before committing to an approach, when stuck on a recurring error, or before declaring a task complete".
  - Suits "long, multi-step tasks where most turns are routine but plan quality determines the outcome".
  - For an Opus 5.5 main model, the accepted advisors are Fable and Opus 5 or later.
  - Fable as advisor needs the usage-credits consent first.
  
  — [Advisor](https://code.claude.com/docs/en/advisor)
- 1M context: "On the Anthropic API, Fable 5.1, Fable 5, Sonnet 5 and later, and Opus 4.7 and later run with the 1M window on every plan, including Pro", at "standard model pricing with no premium for tokens beyond 200K". — [Model configuration](https://code.claude.com/docs/en/model-config)
- Switching models mid-session means the next request re-reads the whole conversation "with no cache hits". — [Prompt caching](https://code.claude.com/docs/en/prompt-caching)
- `/model` also switches subagents that inherit the session model. — [Model configuration](https://code.claude.com/docs/en/model-config)
- Automatic content fallback: Fable, Opus 5.5 and Sonnet 5.5 run safety classifiers, mainly for cybersecurity and biology. Flagged requests re-run on a fallback model. `claude --safe-mode` helps tell whether CLAUDE.md, skills or MCP content triggered it. — [Model configuration](https://code.claude.com/docs/en/model-config)

### Inferences
- **Recommended default for this user:** Opus 5.5 (the Pro default) at `high` for work on the existing game: performance bugs (stutters, z-fighting, the 35-38 FPS scene) and edits to existing systems. This matches the doc's description of `high` ("fixing a bug in an existing codebase").
  - Use `xhigh` for long autonomous builds such as the cutscene system or the combat system.
  - Use `max` only per session for one-off hard investigations, and only after checking it helps.
  - Use `ultrathink` on a single hard turn (for example, diagnosing the root cause of a micro-stutter) instead of raising the whole session.
- **Using Fable 5.1 on Pro:** it is the quality ceiling, but every token goes to usage credits at API rates ($10/$50 per MTok). Since budget isn't a concern:
  - Option (a): turn on usage credits and run Fable for ambiguous, high-stakes work (combat architecture, frame-pacing root causes, the multi-hour reveal-sequence build).
  - Option (b): upgrade to Max, which includes Fable at up to 50% of weekly limits and raises base limits. This would also directly address the past usage-limit cutoff mid-task. This is a judgment based on the plan facts above, not an official recommendation.
- **Advisor as a middle path:** an Opus 5.5 main model with a Fable advisor puts Fable-level judgment at plan and "done" checkpoints without running every turn on Fable. On Pro, the advisor's Fable calls still bill credits.
- **Workflows on Pro:** ultracode and dynamic workflows give real quality gains (adversarial cross-checking) but use limits quickly, and on Pro they are off by default and sized "small". Use them for broad audits (e.g., "audit every LocalScript for per-frame allocations"), not as an always-on default.

### Gaps
- The Claude Code effort docs link a post with per-level task comparisons ("Spending your effort", claude.dev). It was unreachable from this environment, and the matching claude.com URL returned 404.
- No official per-plan numbers for Pro session or weekly limits were found; the docs only point to `/usage`.
- No Anthropic guidance specific to game development or Luau on model or effort choice.

---

## 2. Context and session management: plan mode, checkpoints/rewind, `/compact`, `/clear`, auto-compaction, 1M context, context rot

### Takeaway
Anthropic's core claim is that context is "the most important resource to manage" and "performance degrades as it fills". This holds even with 1M-token windows ("context rot").

The officially recommended habits:
- Plan mode for uncertain or multi-file work.
- `/clear` between unrelated tasks and after two failed corrections.
- `/compact <focus>` with explicit preserve instructions.
- `/rewind` checkpoints for safe experiments.
- Subagents to keep research out of the main context.

Two caveats matter for this user. Checkpoints only cover edits made with Claude's own file-editing tools, so Bash, external-process and (by inference) MCP-driven Studio changes can't be rewound. And only some content survives compaction.

### Cited Findings

**Why context is the binding constraint**
- "Most best practices are based on one constraint: Claude's context window fills up fast, and performance degrades as it fills… Claude may start 'forgetting' earlier instructions or making more mistakes." The docs suggest a custom status line to track context use. — [Best practices](https://code.claude.com/docs/en/best-practices)
- Context rot: "as the number of tokens in the context window increases, the model's ability to accurately recall information from that context decreases… Context, therefore, must be treated as a finite resource with diminishing marginal returns." Also: "context windows of all sizes will be subject to context pollution and information relevance concerns". The guiding principle is the "smallest possible set of high-signal tokens". — [Effective context engineering for AI agents (Sep 29, 2025)](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- Three long-horizon techniques: compaction, structured note-taking (e.g., a NOTES.md or to-do list), and sub-agent architectures. Subagents explore with "tens of thousands of tokens or more, but return… a condensed, distilled summary (often 1,000-2,000 tokens)". — [Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

**Plan mode**
- Ways in:
  - Press `Shift+Tab` until "⏸ plan mode on".
  - Launch with `claude --permission-mode plan`.
  - Prefix a prompt with `/plan`.
  
  `Ctrl+G` opens the plan in an editor. The recommended workflow is Explore → Plan → Implement → Commit. — [Best practices](https://code.claude.com/docs/en/best-practices); [Permission modes](https://code.claude.com/docs/en/permission-modes)
- When to skip it: "Planning is most useful when you're uncertain about the approach, when the change modifies multiple files, or when you're unfamiliar with the code being modified. If you could describe the diff in one sentence, skip the plan." — [Best practices](https://code.claude.com/docs/en/best-practices)

**`/clear`, `/compact`, rewind**
- "If you've corrected Claude more than twice on the same issue in one session, the context is cluttered with failed approaches. Run `/clear`… A clean session with a better prompt almost always outperforms a long session with accumulated corrections." — [Best practices](https://code.claude.com/docs/en/best-practices)
- Tools for trimming context:
  - `/compact <instructions>`, e.g. `/compact Focus on the API changes`.
  - `Esc`+`Esc` or `/rewind`, then **Summarize from here** or **Summarize up to here**.
  - Compaction rules in CLAUDE.md, e.g. "When compacting, always preserve the full list of modified files and any test commands".
  - `/btw` for side questions whose answers never enter history.
  
  — [Best practices](https://code.claude.com/docs/en/best-practices); [Checkpointing](https://code.claude.com/docs/en/checkpointing)
- `/compact` "reads the conversation it summarizes, so compacting a large context is itself a large request. When you want a fresh start instead of continuity, `/clear` costs nothing." — [Costs](https://code.claude.com/docs/en/costs)
- Checkpoints:
  - "Every prompt you send that starts a turn creates a checkpoint". Claude Code keeps file snapshots for the 100 most recent checkpoints.
  - Checkpoints are saved with the conversation, so `/rewind` still works after you resume.
  - You can restore code, conversation, or both.
  - **"Checkpoints only track changes made through Claude's file editing tools. Changes made through Bash commands or external processes are not captured. This isn't a replacement for git."**
  - Most subagent edits, and edits from background forked skills, are not restored by rewind.
  
  — [Best practices](https://code.claude.com/docs/en/best-practices); [Checkpointing](https://code.claude.com/docs/en/checkpointing)
- `/branch` (or `claude --continue --fork-session`) tries a different direction while keeping the original conversation. — [Checkpointing](https://code.claude.com/docs/en/checkpointing); [Commands](https://code.claude.com/docs/en/commands)

**Auto-compaction and 1M context**
- Models with a native 1M window (Fable, Opus 4.7+, Sonnet 5+ on the Anthropic API) auto-compact "at about 967K tokens by default".
  - `/autocompact <100K–1M>` changes the threshold and saves it to `autoCompactWindow`.
  - `--autocompact` overrides it for one launch; `CLAUDE_CODE_AUTO_COMPACT_WINDOW` overrides everything.
  - `CLAUDE_CODE_DISABLE_1M_CONTEXT=1` holds sessions at 200K.
  
  — [Model configuration](https://code.claude.com/docs/en/model-config)
- What survives compaction:

  | Content | After compaction |
  | --- | --- |
  | Project-root CLAUDE.md and unscoped rules | Re-injected from disk |
  | Auto memory | Re-injected |
  | The plan written in plan mode | Re-injected |
  | Rules with `paths:` and nested CLAUDE.md files | Reload only when Claude reads a matching file |
  | Files Claude read or edited | Up to five most recently modified are re-read; files over 5,000 tokens come back as path references |
  | Invoked skill bodies | Re-injected, "capped at 5,000 tokens per skill and 25,000 tokens total; oldest dropped first" |
  | Background tasks | Keep running |
  | `SessionStart` hooks with the `compact` source | Run, and their output is added |
  
  "If a rule must persist across compaction, drop the `paths:` frontmatter or move it to the project-root CLAUDE.md." — [Context window](https://code.claude.com/docs/en/context-window)
- Prompt-caching gotchas:
  - CLAUDE.md edits don't reach a running session until `/clear`, `/compact` or a restart.
  - Cache lifetime is one hour on a subscription, but "drops to five minutes once you're drawing on usage credits".
  
  — [Prompt caching](https://code.claude.com/docs/en/prompt-caching); [Costs](https://code.claude.com/docs/en/costs)
- Sessions:
  - Name sessions with `/rename` and "treat them like branches". Resume with `claude --continue` or `claude --resume`.
  - A resumed session keeps its model.
  - On Pro and Max, resuming a large session after a long break offers to "resume from a summary".
  
  — [Best practices](https://code.claude.com/docs/en/best-practices); [Model configuration](https://code.claude.com/docs/en/model-config); [Costs](https://code.claude.com/docs/en/costs)
- Why usage climbs in a long session: the full conversation is re-sent on every request and every tool round, plus cache misses after breaks, goal check-ins, subagents and workflows. — [Costs](https://code.claude.com/docs/en/costs)

**Fresh start vs. compaction (official prompting guidance)**
- "Starting fresh versus compacting: … Claude's latest models are extremely effective at discovering state from the local filesystem." Be prescriptive about how a new session starts: "Call pwd…", "Review progress.txt, tests.json, and the git logs.", "Manually run through a fundamental integration test before moving on". — [Prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)
- "Context anxiety": some models start wrapping up early near what they think is the context limit. Context resets with structured handoffs fixed this for Sonnet 4.5, and "Opus 4.5 largely removed that behavior on its own", so that harness relied on automatic compaction instead. — [Harness design for long-running application development (Mar 24, 2026)](https://www.anthropic.com/engineering/harness-design-long-running-apps)
- Fable 5 guide: avoid showing explicit context-budget counts to the model. If you must, use the reassurance "You have ample context remaining. Do not stop, summarize, or suggest a new session on account of context limits." — [Prompting Claude Fable 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5)
- Tension: for API harnesses, Fable 5.1's cheaper cache reads mean "compacting early to save cost may no longer be the right cost-intelligence tradeoff… experiment with later compaction points". That is cost advice and sits alongside, not against, the quality advice to keep context lean. — [Prompting Claude Fable 5.1](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-1)

### Inferences
- **For a long creative project:**
  - One named session per feature or workstream (e.g., `race-change-cutscene`, `capital-city-streaming`).
  - A written spec and a progress file in the repo.
  - `/clear` between features.
  - `/compact` with an explicit list of what to preserve when continuity matters.
  - Hard rules (perf budgets, race color palette) in the project-root CLAUDE.md so they survive compaction.
- **Studio changes can't be rewound.** Studio edits made through MCP tools (e.g., `execute_luau`, `multi_edit`) are not file edits by Claude's editing tools, so `/rewind` can't undo them. Snapshot the place or keep scripts in git (e.g., via a file-sync workflow) before risky experiments. This is inferred from the checkpoint limitations; Studio-side versioning was not researched here.
- **1M context doesn't remove context rot.** For quality-sensitive sessions, prefer earlier `/clear` and `/compact` over riding to ~967K. Setting `/autocompact` to e.g. 300–500K is an option, but the docs give no official quality-optimal threshold.

### Gaps
- No official quantitative data on quality loss versus context fill level for Opus 5.5 or Fable 5.1 inside Claude Code.
- No official recommended auto-compact threshold for quality, as opposed to cost.

---

## 3. Persistent instructions: CLAUDE.md and memory hierarchy, Skills, custom slash commands, output styles

### Takeaway
Each mechanism has a job:
- **CLAUDE.md:** short, always-loaded facts. Target under 200 lines and prune hard. Use "IMPORTANT" on single lines only.
- **`.claude/rules/` with `paths:`:** instructions that only apply to one area of the codebase.
- **Skills:** procedures and long reference material that load on demand. Keep `SKILL.md` under 500 lines, link reference files one level deep, put the most important instructions at the top (only the first 5,000 tokens survive compaction), and write a keyword-rich description.
- **Hooks:** anything that must happen every time.
- **Auto memory:** learned corrections.
- **Output styles:** change communication, not capability.

Custom slash commands have been merged into skills. Anthropic also warns that skills written for older models can be "too prescriptive" for Fable-class models.

### Cited Findings

**CLAUDE.md hierarchy and loading**
- Scopes, in load order:

  | Scope | Location |
  | --- | --- |
  | Managed policy | Windows: `C:\Program Files\ClaudeCode\CLAUDE.md` |
  | User | `~/.claude/CLAUDE.md` |
  | Project | `./CLAUDE.md` or `./.claude/CLAUDE.md` |
  | Local | `./CLAUDE.local.md` (add it to `.gitignore`) |

  — [Memory](https://code.claude.com/docs/en/memory)
- How files load:
  - Files in parent directories load at launch; files in subdirectories load on demand.
  - Files are concatenated, not overridden; files closer to the working directory are read last.
  - Block-level HTML comments are stripped and cost no tokens.
  - CLAUDE.md "is delivered as a user message after the system prompt… there's no guarantee of strict compliance". Use `--append-system-prompt` for system-level text.
  
  — [Memory](https://code.claude.com/docs/en/memory)
- Imports:
  - Syntax is `@path`, relative to the importing file, with "a maximum depth of four hops". Escape spaces with a backslash.
  - Imports "help you organize a long file but don't reduce its context cost, because imported files also load at launch".
  - External imports need a one-time approval.
  
  — [Memory](https://code.claude.com/docs/en/memory)
- Size and auditing:
  - "target under 200 lines per CLAUDE.md file. Longer files consume more context and reduce adherence." Files over 4 MiB are skipped.
  - `/doctor` proposes trims.
  - `/doctor prompt-audit` (v2.1.283+) checks CLAUDE.md, rules, skills, commands, subagents and output styles for "instructions written for older models", references that don't exist, and contradictions.
  
  — [Memory](https://code.claude.com/docs/en/memory)
- Writing guidance:
  - "For each line, ask: *'Would removing this cause Claude to make mistakes?'* If not, cut it. Bloated CLAUDE.md files cause Claude to ignore your actual instructions!"
  - Include: commands Claude can't guess, style rules that differ from defaults, test instructions, architecture decisions, gotchas.
  - Exclude: what Claude can learn from the code, standard conventions, long tutorials, file-by-file descriptions.
  - "If Claude keeps skipping one instruction, add emphasis such as 'IMPORTANT' to that line alone. If you emphasize many lines, none of them stands out."
  
  — [Best practices](https://code.claude.com/docs/en/best-practices)
- Write instructions concrete enough to verify ("Use 2-space indentation", not "Format code properly"). "If two instructions contradict each other, Claude may pick one arbitrarily." — [Memory](https://code.claude.com/docs/en/memory)
- `/init` generates a starter CLAUDE.md; with `CLAUDE_CODE_NEW_INIT=1` it also walks through skills and hooks. `/context` shows which memory files loaded. The `InstructionsLoaded` hook logs which files load, when and why. — [Memory](https://code.claude.com/docs/en/memory)

**Rules and auto memory**
- `.claude/rules/*.md` files are discovered recursively. A `paths:` glob in frontmatter (e.g., `"src/api/**/*.ts"`) makes a rule load only when Claude reads matching files. User-level rules live in `~/.claude/rules/`. — [Memory](https://code.claude.com/docs/en/memory)
- Auto memory:
  - On by default. Claude saves `user`, `feedback`, `project` and `reference` notes to `~/.claude/projects/<project>/memory/`.
  - The `MEMORY.md` index loads at the start of each session (first 200 lines or 25KB); topic files are read on demand.
  - `/memory` to audit. Turn off with `autoMemoryEnabled: false` or `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`.
  
  — [Memory](https://code.claude.com/docs/en/memory)

**Skills (SKILL.md) and custom commands**
- "Custom commands have been merged into skills": `.claude/commands/deploy.md` and `.claude/skills/deploy/SKILL.md` both create `/deploy`. "Unlike CLAUDE.md content, a skill's body loads only when it's used". Skills follow the Agent Skills open standard. — [Skills](https://code.claude.com/docs/en/skills)
- Frontmatter fields:
  - `name`, `description` (recommended), `when_to_use`, `argument-hint`, `arguments`.
  - `disable-model-invocation` (only you can invoke), `user-invocable: false` (only Claude can invoke).
  - `allowed-tools`, `disallowed-tools`.
  - `model` (applies for the rest of the current turn), `effort` (overrides session effort while active).
  - `context: fork` with `agent` and `background` (run in a subagent).
  - `hooks`, `paths` (auto-activate only for matching files), `shell` (`bash` or `powershell`), `metadata`.
  - Substitutions: `$ARGUMENTS`, `${CLAUDE_SKILL_DIR}`, `${CLAUDE_EFFORT}`, `${CLAUDE_PROJECT_DIR}`.
  
  — [Skills](https://code.claude.com/docs/en/skills)
- How skills trigger (progressive disclosure):
  - By default, "Description always in context, full skill loads when invoked".
  - The combined `description` + `when_to_use` is "truncated at 1,536 characters in the skill listing". "Put the key use case first."
  - The listing budget "scales at 1% of the model's context window". When it overflows, descriptions are dropped for the least-used skills first. Tunable with `skillListingBudgetFraction` or `SLASH_COMMAND_TOOL_CHAR_BUDGET`.
  
  — [Skills](https://code.claude.com/docs/en/skills)
- Supporting files: "Keep `SKILL.md` under 500 lines. Move detailed reference material to separate files", and say in `SKILL.md` what each file contains and when to load it. Scripts are "executed, not loaded". — [Skills](https://code.claude.com/docs/en/skills)
- Lifecycle:
  - Invoked skill content "stays in context across turns"; Claude Code "does not re-read the skill file on later turns, so write guidance that should apply throughout a task as standing instructions".
  - After compaction, each re-attached skill keeps only its first 5,000 tokens, within a 25,000-token shared budget.
  - "put the most important instructions near the top of `SKILL.md`".
  
  — [Skills](https://code.claude.com/docs/en/skills)
- Troubleshooting:
  - **Not triggering:** add keywords users would say; ask "What skills are available?"; check YAML errors with `--debug` or `claude plugin validate .claude/skills` (v2.1.233+).
  - **Triggers too often:** make the description more specific or set `disable-model-invocation`.
  - **Claude stops following it:** move must-hold rules into a hook (or `hooks` frontmatter), word guidance as standing rules, and re-invoke the skill after compaction.
  - `/skill-doctor` shows each skill's context cost and how often it's used.
  
  — [Skills](https://code.claude.com/docs/en/skills)
- Platform authoring best practices:
  - "Concise is key", with the default assumption that "Claude is already very smart".
  - Set appropriate degrees of freedom.
  - Write descriptions in the third person.
  - "Keep references one level deep from SKILL.md".
  - Give reference files over 100 lines a table of contents.
  - Use checklists for complex workflows and validator feedback loops ("Run validator → fix errors → repeat").
  - Avoid time-sensitive information; use consistent terminology.
  - "Create evaluations BEFORE writing extensive documentation" (three scenarios).
  - Iterate with "Claude A" writing the skill and "Claude B" testing it.
  - "Test with all models you plan to use".
  
  — [Skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
- Fable-specific: "Skills developed for prior models are often too prescriptive for Claude Fable 5 and can degrade output quality. Review and consider removing older instructions if default performance is better." Also, don't tell the model to reproduce its reasoning in the response; that can trigger a `reasoning_extraction` refusal. — [Prompting Claude Fable 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5)
- `/claude-api prompt-audit` (v2.1.221+) flags instructions written for older models in prompts, skills and tool descriptions. — [Skills](https://code.claude.com/docs/en/skills)

**Output styles**
- Built-in styles: Default, Proactive (starts work right away and makes reasonable assumptions), Concise (leads with the result and "does the engineering work as thoroughly as in the Default style"), Explanatory, Learning. Switch with `/output-style` (v2.1.269+).
- "An output style gives Claude instructions to follow. It doesn't guarantee that something always happens". Use CLAUDE.md for project facts and hooks for must-happen actions.

— [Output styles](https://code.claude.com/docs/en/output-styles)

### Inferences
- **For the user's design-playbook skill:**
  - Put non-negotiables at the top of `SKILL.md`: the six race signature colors, naming and Instance conventions, perf budgets, cinematic rules. Only the first ~5,000 tokens survive compaction.
  - Move lore, per-race details and the capital-city layout into reference files linked one level deep, with a table of contents.
  - Write a keyword-rich, third-person description (e.g., "Roblox isekai game design rules: races, race colors, cutscenes, entity/system voice, combat").
  - Run `/doctor prompt-audit` on it.
- Split procedural workflows (e.g., `/cutscene-review`, `/perf-pass`) into separate task skills with `disable-model-invocation: true`, and keep the playbook as a reference skill.
- Keep CLAUDE.md for facts needed every session (project layout, how Studio is reached, verification commands).
- Enforce mechanical rules with hooks, not CLAUDE.md wording.

### Gaps
- No official guidance on structuring very large creative or lore documents in skills, beyond the general rules (500 lines, references, TOC).
- The docs give the listing budget as "1% of the model's context window" without an explicit unit conversion. The exact budget for a 1M-context Opus 5.5 session isn't stated.

---

## 4. Delegation and parallelism: subagents, parallel subagents, worktrees, agent teams, background tasks, headless / Agent SDK — when they improve quality and when they waste tokens

### Takeaway
Subagents improve quality mainly by keeping research and verification out of the main context, and by giving a fresh-context reviewer. Anthropic finds "separate, fresh-context verifier subagents tend to outperform self-critique", and that a separate evaluator is "a strong lever".

Each tool has a cost:
- **Dynamic workflows:** scale to dozens of agents with adversarial cross-checking.
- **Agent teams:** experimental, about 7x the tokens in plan mode.
- **Worktrees:** isolate parallel file edits in git.

All of this draws on the same usage limits, so on Pro, parallelism trades directly against session and weekly limits. Delegation pays off for independent, sizeable tracks of work. For small tasks it multiplies cost.

### Cited Findings

**Subagents**
- Use a subagent "when a side task would flood your main conversation with search results, logs, or file contents you won't reference again". Each runs in its own context window with its own prompt, tools and permissions, and "count[s] toward the same usage limits". — [Subagents](https://code.claude.com/docs/en/sub-agents)
- Definitions:
  - Live in `.claude/agents/` (project) or `~/.claude/agents/` (user), and are hot-reloaded.
  - Frontmatter: `name`, `description` (both required), `tools`, `disallowedTools`, `model` (`sonnet`/`opus`/`haiku`/`fable`/full ID/`inherit`), `permissionMode`, `maxTurns`, `skills` (preloaded in full), `mcpServers`, `hooks`, `memory` (`user`/`project`/`local`), `background`, `omitClaudeMd`, `effort`, `isolation: worktree`, `color`, `initialPrompt`, and `experimental.cacheTtl`.
  
  — [Subagents](https://code.claude.com/docs/en/sub-agents)
- Model resolution order:
  1. The per-invocation `model` parameter.
  2. The frontmatter `model`.
  3. `CLAUDE_CODE_SUBAGENT_MODEL`.
  4. The main session's model.
  
  `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` forces one model on every subagent. Subagents inherit the session's thinking settings. — [Subagents](https://code.claude.com/docs/en/sub-agents)
- The built-in Explore and Plan subagents skip CLAUDE.md, and Explore is capped at Opus. Subagent descriptions over 15,000 tokens in total trigger a startup warning. — [Subagents](https://code.claude.com/docs/en/sub-agents)
- Limits:
  - Nesting depth defaults to 3 layers (`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`).
  - 20 subagents can run at once (`CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`); this limit is not enforced while ultracode is on.
  - `/subtask` forks the whole conversation into a background subagent.
  
  — [Subagents](https://code.claude.com/docs/en/sub-agents)
- Subagent vs. main conversation:
  - Stay in the main conversation for iterative back-and-forth, phases that share a lot of context, or quick targeted changes.
  - Use a subagent for verbose output, tool restrictions, or self-contained work that can return a summary.
  
  — [Subagents](https://code.claude.com/docs/en/sub-agents)
- Persistent subagent memory: `project` scope is recommended ("shareable via version control"). Ask the subagent to read its memory before starting and update it afterwards. — [Subagents](https://code.claude.com/docs/en/sub-agents)

**Fresh-context review and the generator/evaluator pattern**
- "A fresh context improves code review since Claude won't be biased toward code it just wrote." The Writer/Reviewer pattern uses two sessions. — [Best practices](https://code.claude.com/docs/en/best-practices)
- Adversarial review step: "Before treating a task as done, have a subagent review the diff in a fresh context and report gaps."
  - Caution: "A reviewer prompted to find gaps will usually report some, even when the work is sound… Chasing every finding leads to over-engineering". Tell it "to flag only gaps that affect correctness or the stated requirements".
  
  — [Best practices](https://code.claude.com/docs/en/best-practices)
- "Make self-verification explicit in long-run prompts. Separate, fresh-context verifier subagents tend to outperform self-critique." A suggested instruction: "Establish a method for checking your own work at an interval of [X]… verifying your work with subagents against the specification." — [Prompting Claude Fable 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5)
- "When asked to evaluate work they've produced, agents tend to respond by confidently praising the work." Separating the generator from the evaluator "proves to be a strong lever". "Out of the box, Claude is a poor QA agent", and the evaluator prompt needed several tuning rounds. Cost example (Opus 4.5): a solo run took 20 min and $9; the full harness took 6 hr and $200, "over 20x more expensive, but the difference in output quality was immediately apparent". The evaluator "is worth the cost when the task sits beyond what the current model does reliably solo". — [Harness design for long-running application development](https://www.anthropic.com/engineering/harness-design-long-running-apps)
- Cost-side counterpoint: Opus 5 "delegates to subagents more readily than prior models… it multiplies cost and time when applied to small tasks". Anthropic's sample damping prompt includes "do not use subagents to verify or double-check your own work". Deterministic caps are the env vars above. — [Prompting Claude Opus 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5)

**Dynamic workflows (`ultracode`)**
- How they compare: "A workflow moves the plan into code". Subagents handle a few tasks per turn, agent teams "a handful of long-running peers", workflows "Dozens to hundreds of agents per run".
  - Quality patterns: "have independent agents adversarially review each other's findings… or draft a plan from several angles". The bundled `/deep-research` workflow is an example.
  - Example prompt shapes:
    - "keep fixing until a check passes… or two rounds in a row make no progress".
    - "adversarially verify each finding before reporting it".
  
  — [Workflows](https://code.claude.com/docs/en/workflows)
- Limits:
  - Up to 16 concurrent agents by default (`CLAUDE_CODE_WORKFLOW_MAX_CONCURRENT_AGENTS`), 1,000 agents per run, and no mid-run user input.
  - A `Large workflow` warning appears above 25 agents or 1.5M projected tokens.
  - Size guideline (`workflowSizeGuideline`) defaults to `medium`, or "`small` when you're signed in on a Pro plan" (v2.1.271+).
  - Saved workflows go in `.claude/workflows/` and run as `/<name>`.
  
  — [Workflows](https://code.claude.com/docs/en/workflows)

**Agent teams, worktrees, background agents, headless**
- Agent teams "are experimental and disabled by default"; enable with `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`.
  - Best for parallel research and review, separate new modules, debugging with competing hypotheses, and cross-layer changes.
  - Not suited to "sequential tasks, same-file edits, or work with many dependencies".
  - "Agent teams use approximately 7x more tokens than standard sessions when teammates run in plan mode".
  
  — [Agent teams](https://code.claude.com/docs/en/agent-teams); [Costs](https://code.claude.com/docs/en/costs)
- Worktrees: `claude --worktree <name>` (or `-w`) creates an isolated checkout under `.claude/worktrees/<name>/` on branch `worktree-<name>`. Subagents can use `isolation: worktree`. `/batch` splits work into 5–30 units, each in its own worktree, and needs git or a `WorktreeCreate` hook. — [Worktrees](https://code.claude.com/docs/en/worktrees); [Commands](https://code.claude.com/docs/en/commands)
- Agent view (`claude agents`, research preview) manages background sessions from one screen; `/background` detaches the current session. — [Agent view](https://code.claude.com/docs/en/agent-view); [Commands](https://code.claude.com/docs/en/commands)
- Headless: `claude -p "…"` with `--output-format json` or `stream-json --verbose`; `--allowedTools` limits what unattended runs can do; `claude --permission-mode auto -p` runs with classifier-checked autonomy. `/goal` works in `-p`. — [Best practices](https://code.claude.com/docs/en/best-practices); [Goal](https://code.claude.com/docs/en/goal)
- Fable 5: "significantly more dependable at dispatching and sustaining parallel subagents". The guide recommends asynchronous orchestration: "keep working while they run". — [Prompting Claude Fable 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5)

### Inferences
- **Studio is shared live state.** Parallel agents that all drive the same open Studio place through MCP will likely collide (play-mode toggles, simultaneous edits).
  - Keep Studio-mutating work in one agent.
  - Parallelize read-only exploration, review and on-disk code (if scripts are file-synced) in worktrees.
  - Roblox's built-in MCP server supports several Studio instances addressed by `studio_id` (see Q6), which could isolate agents per instance; this is untested.
- **Best quality-per-token delegation for this project:**
  1. An Explore-style subagent for "where is X implemented / what's causing Y" investigations.
  2. A read-only "cinematic QA" evaluator subagent with Studio screenshot and console tools and an explicit rubric (see Q7), run before marking cutscene work done.
  3. Occasional workflows for whole-codebase audits.
- Agent teams are unlikely to be worth their ~7x token cost for a solo Pro developer, and are experimental.

### Gaps
- No official Anthropic guidance on multi-agent work against a single GUI application or game editor like Roblox Studio.

---

## 5. Automation and verification: hooks, permissions, review commands, and other verification features

### Takeaway
The single most emphasized practice is to "Give Claude a check it can run". There are four ways to make that check gate the end of a turn:
1. Ask for it in the prompt.
2. Use `/goal`: a separate evaluator model re-checks a stated condition after every turn.
3. Use a Stop hook: a deterministic script that blocks ending the turn.
4. Use a fresh-context reviewer subagent or workflow.

Hooks (`PreToolUse`/`PostToolUse`/`Stop`, etc.) enforce lint, format and custom validators "with zero exceptions", and they can target MCP tools by name. The review commands are `/code-review` (bugs; effort levels; `--fix`; `ultra`), `/simplify` (cleanup), `/security-review`, `/ultrareview` (cloud; 3 free runs on Pro), and `/verify` / `/run` (run the real app).

Caveat: on Opus 5-class and Fable models, Anthropic advises giving *checks* rather than generic "double-check" reminders, which cause over-verification.

### Cited Findings

**Verification loop (official)**
- "Claude stops when the work looks done. Without a check it can run, 'looks done' is the only signal available, and you become the verification loop." Valid checks include tests, build exit codes, linters, a script diffing output against a fixture, or "a browser screenshot compared against a design". — [Best practices](https://code.claude.com/docs/en/best-practices)
- Four gates, from least to most setup:
  1. In one prompt.
  2. `/goal`: "A separate evaluator re-checks it after every turn".
  3. A Stop hook: "runs your check as a script and blocks the turn from ending until it passes".
  4. A verification subagent or workflow, "so the agent doing the work isn't the one grading it".
  
  "Have Claude show evidence rather than asserting success". — [Best practices](https://code.claude.com/docs/en/best-practices)
- `/goal <condition>`:
  - After each turn, a small fast model (Haiku by default) judges the condition: not yet met, met, or impossible. The evaluator "doesn't run commands or read files independently, so write the condition as something Claude's own output can demonstrate".
  - A good condition has "One measurable end state", "A stated check", and "Constraints that matter"; it can be up to 4,000 characters. Bound it with e.g. "or stop after 20 turns".
  - The goal pauses on usage limits and resumes after the reset when auto-continue is on.
  - `/goal` doesn't change permission mode; run it in auto mode for unattended turns.
  
  — [Goal](https://code.claude.com/docs/en/goal)

**Hooks**
- "Use hooks for actions that must happen every time with zero exceptions… Unlike CLAUDE.md instructions which are advisory, hooks are deterministic". Claude can write hooks for you; `/hooks` lists them. — [Best practices](https://code.claude.com/docs/en/best-practices)
- Events: `SessionStart`, `Setup`, `UserPromptSubmit`, `UserPromptExpansion`, `PreToolUse` (can block), `PermissionRequest`, `PermissionDenied`, `PostToolUse`, `PostToolUseFailure`, `PostToolBatch`, `Notification`, `MessageDisplay`, `SubagentStart`/`SubagentStop`, `TaskCreated`/`TaskCompleted`, `Stop`, `StopFailure`, `TeammateIdle`, `InstructionsLoaded`, `ConfigChange`, `CwdChanged`, `DirectoryAdded`, `FileChanged`, `WorktreeCreate`/`WorktreeRemove`, `PreCompact`/`PostCompact`, `PreModelSwitch`/`PostModelSwitch`, `Elicitation`/`ElicitationResult`, `SessionEnd`. — [Hooks reference](https://code.claude.com/docs/en/hooks)
- Exit codes and output:
  - Exit 2 blocks ("the one outcome JSON can't override").
  - JSON on stdout gives structured control.
  - To show a warning to Claude from `PostToolUse`, "exit 2 instead so Claude sees the stderr".
  - Stop hooks get `stop_hook_active`. After 8 consecutive Stop-hook continuations the turn ends anyway (`CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`).
  
  — [Hooks reference](https://code.claude.com/docs/en/hooks)
- Hook types: `command`, `http`, `mcp_tool`, `prompt` (LLM decides) and `agent` (experimental; a subagent with Read/Grep/Glob, "up to 50 turns", default timeout 60s). `"async": true` runs a hook in the background, and its result is delivered next turn. — [Hooks reference](https://code.claude.com/docs/en/hooks)
- MCP tools follow the pattern `mcp__<server>__<tool>`. "To match every tool from a server, append `.*`… a matcher like `mcp__memory`… matches no tool." — [Hooks reference](https://code.claude.com/docs/en/hooks)
- Windows: set `"shell": "powershell"` on command hooks. Reference the project root as `$env:CLAUDE_PROJECT_DIR` or `${CLAUDE_PROJECT_DIR}`, never bare `$CLAUDE_PROJECT_DIR`. — [Hooks reference](https://code.claude.com/docs/en/hooks)
- Hooks can also save context, e.g. a `PreToolUse` hook that rewrites test commands to show only failures. — [Costs](https://code.claude.com/docs/en/costs)

**Permissions**
- With v2.1.283+, auto mode is the default starting permission mode for interactive terminal sessions: "a separate classifier model reviews most actions… and blocks only what looks risky". `/permissions` allowlists and `/sandbox` cut down prompts. — [Best practices](https://code.claude.com/docs/en/best-practices)

**Review and verification commands**
- `/code-review [low|medium|high|xhigh|max|ultra] [--fix] [--comment] [target]`:
  - Reviews the branch's commits plus uncommitted changes "for correctness bugs".
  - Runs as a background subagent.
  - `ultra` runs a deep cloud review.
  - `/review` is an alias.
  
  — [Commands](https://code.claude.com/docs/en/commands); [Code review](https://code.claude.com/docs/en/code-review)
- Other review commands:
  - `/simplify`: "Four review agents run in parallel" on reuse, simplification, efficiency and abstraction; "doesn't look for correctness bugs".
  - `/security-review`: needs an `origin` remote.
  - `/ultrareview`: cloud multi-agent review, "Includes 3 free runs on Pro and Max".
  
  — [Commands](https://code.claude.com/docs/en/commands)
- `/run` and `/verify` launch and drive the actual app rather than relying on tests or type checks. Inference about how to launch "gets unreliable for projects that need anything beyond a standard launch". `/run-skill-generator` records a working recipe as `.claude/skills/run-<name>/`. — [Skills](https://code.claude.com/docs/en/skills)
- `/insights` generates an HTML report of "where things go wrong" across recent sessions. — [Commands](https://code.claude.com/docs/en/commands)

**Verification prompting (model-specific)**
- Opus 5: "If your prompt contains explicit verification instructions… remove them: instructions like these cause over-verification". Also avoid "double-check your answer". — [Prompting Claude Opus 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5)
- Fable: "Skip the verification reminders: it verifies its own work with less prompting". — [Model configuration](https://code.claude.com/docs/en/model-config)
- Sonnet 5.5 at `low` effort "sometimes reports a change as done without running a check". There is an official prompt telling it to "run a real check that exercises the change before reporting it done". — [Prompting Claude Sonnet 5.5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5-5)
- Long-running harness: Claude tended "to mark a feature as complete without proper testing". Browser automation "dramatically improved performance". Limitation: Claude "can't see browser-native alert modals through the Puppeteer MCP". — [Effective harnesses for long-running agents (Nov 26, 2025)](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)

### Inferences
- **The Roblox equivalent of browser verification** is the built-in Studio MCP's play and inspection tools (see Q6): `start_stop_play`, `get_console_output`, `screen_capture`, `character_navigation`, input simulation, and the `playtest` subagent. Write concrete checks such as:
  - "no errors or warnings in console output during the reveal shot";
  - "a Luau probe logs frame times; the 95th-percentile frame time stays under 16.7 ms across the cutscene";
  - "a screenshot at t=3s shows no flicker on overlapping parts".
  
  Then use one as a `/goal` condition or have an agent-type Stop hook check it.
- **Diff-based commands need files on disk.** `/code-review`, `/simplify`, `/security-review` and checkpoints work on a git diff on disk. They only reach game code if scripts are synced to files (e.g., a Rojo-style workflow). Scripts that live only inside Studio are invisible to them.
- **Hooks around the Studio MCP:**
  - A `PreToolUse` hook matching `mcp__Roblox_Studio__.*` (adjust to the configured server name) can log or block risky Luau (e.g., mass `:Destroy()`).
  - A `PostToolUseFailure` hook can log intermittent MCP failures for diagnosis.
- **Reconciling the verification advice:** give Claude checks to run and require evidence, rather than writing "double-check" or "verify carefully" reminders into CLAUDE.md or the skill.

### Gaps
- No official Anthropic recipe for verifying game or real-time rendering quality (frame pacing, z-fighting). The verification guidance is generic or web-focused.

---

## 6. MCP in Claude Code: configuration, scopes, timeouts, output limits, tool search / deferred tools, troubleshooting intermittent failures

### Takeaway
Add servers with `claude mcp add` (scopes: local is the default, project, or user). For Roblox, the original standalone Rust MCP server "is no longer being actively developed", and Roblox recommends the **MCP server built into Roblox Studio**. On Windows it is set up as `cmd.exe /c %LOCALAPPDATA%\Roblox\mcp.bat` or via Studio's quick-connect for Claude Code.

Key controls:

| Control | Default |
| --- | --- |
| `MCP_TIMEOUT` (server startup) | 30s |
| `MCP_TOOL_TIMEOUT` (tool execution) | ~28h; HTTP/SSE requests also time out at 60s |
| `CLAUDE_CODE_MCP_TOOL_IDLE_TIMEOUT` | 30 min for stdio, 5 min for network servers |
| Per-server `timeout` field | Overrides `MCP_TOOL_TIMEOUT` for that server |
| `MAX_MCP_OUTPUT_TOKENS` | 25,000 (warning above 10,000; bigger outputs are saved to a file) |
| Tool search | On; MCP tools are deferred by default (`ENABLE_TOOL_SEARCH`, `alwaysLoad`) |

Important for intermittent failures: Claude Code does **not** auto-reconnect stdio servers, and long tool calls move to the background after 2 minutes. Diagnose with `claude mcp list`/`get`, `/mcp`, `/doctor`, `/debug`, `--debug` and `--safe-mode`.

### Cited Findings

**Configuration and scopes**
- Syntax: `claude mcp add [options] <name> -- <command> [args...]`. The `--` separates Claude's own flags from the server's arguments. With `--env`, put another option between it and the server name. Manage servers with `claude mcp list` / `get` / `remove` and `/mcp` inside a session. — [MCP](https://code.claude.com/docs/en/mcp)
- Scopes:

  | Scope | Where it's stored | Notes |
  | --- | --- | --- |
  | Local (default) | `~/.claude.json`, under the project | Private, this project only |
  | Project | `.mcp.json`, checked into git | Approval prompt before first use |
  | User | `~/.claude.json` | All your projects |

  Precedence is local > project > user > plugin > claude.ai connectors, using "The entire server entry from that source"; fields are not merged. — [MCP](https://code.claude.com/docs/en/mcp)
- `CLAUDE_PROJECT_DIR` is set in a stdio server's environment. — [MCP](https://code.claude.com/docs/en/mcp)

**Timeouts and connection behavior** (from the env-vars reference)
- `MCP_TIMEOUT`: "Timeout in milliseconds for MCP server startup (default: 30000, or 30 seconds)". — [Environment variables](https://code.claude.com/docs/en/env-vars)
- `MCP_TOOL_TIMEOUT`: "Timeout in milliseconds for MCP tool execution (default: 100000000, about 28 hours). For an HTTP, SSE, or claude.ai connector server, each request also times out after 60 seconds by default". A per-server `timeout` in `.mcp.json` overrides it. — [Environment variables](https://code.claude.com/docs/en/env-vars)
- `CLAUDE_CODE_MCP_TOOL_IDLE_TIMEOUT`: aborts a call when the server sends "no response and no progress notification" for this long. Defaults are 5 minutes for network servers and 30 minutes for stdio (v2.1.187+). — [Environment variables](https://code.claude.com/docs/en/env-vars)
- Startup settings: `MCP_CONNECTION_NONBLOCKING` (startup doesn't wait for servers by default), `MCP_CONNECT_TIMEOUT_MS` (5000), `MCP_SERVER_CONNECTION_BATCH_SIZE` (3 stdio servers in parallel). — [Environment variables](https://code.claude.com/docs/en/env-vars)
- Reconnection:
  - Remote servers are reconnected with backoff, up to 5 attempts.
  - **"Stdio servers are local processes, and Claude Code doesn't reconnect them automatically."** Retry manually from `/mcp` or with `/mcp reconnect <server>`.
  - With tool search on, Claude Code tells Claude which server failed and its connection error.
  
  — [MCP](https://code.claude.com/docs/en/mcp); [Commands](https://code.claude.com/docs/en/commands)
- Automatic backgrounding: "An MCP tool call in the main conversation that is still running after two minutes moves to a background task" (v2.1.212+; `CLAUDE_CODE_MCP_AUTO_BACKGROUND_MS`, `0` disables). This doesn't apply to calls made by subagents, or to `-p` unless `CLAUDE_AUTO_BACKGROUND_TASKS=1`. — [MCP](https://code.claude.com/docs/en/mcp)
- Status output: `claude mcp list` shows `✔ Connected`, `! Needs authentication`, or `✘ Failed to connect` with failure detail (v2.1.219+). Configuration warnings cover hidden whitespace, the same name in several scopes, reserved names, and missing env vars. — [MCP](https://code.claude.com/docs/en/mcp)

**Output limits**
- A warning appears when an MCP output exceeds 10,000 tokens; the default maximum is 25,000 (`MAX_MCP_OUTPUT_TOKENS`, e.g. `export MAX_MCP_OUTPUT_TOKENS=50000`). Larger results are "save[d]… to a file and replace[d]… with a message that names the file path". Server authors can raise one tool's limit with `_meta["anthropic/maxResultSizeChars"]`, up to 500,000 characters. — [MCP](https://code.claude.com/docs/en/mcp)
- Images: the inline copy "may be scaled down or compressed". Since v2.1.283, Claude Code also saves the original bytes so Claude "can then crop, convert, or reuse the full-resolution file". Image results are always subject to `MAX_MCP_OUTPUT_TOKENS`. — [MCP](https://code.claude.com/docs/en/mcp)
- Tool and server descriptions are truncated at 2,048 characters (`CLAUDE_CODE_MAX_MCP_DESCRIPTION_LENGTH`, v2.1.280+). — [MCP](https://code.claude.com/docs/en/mcp)
- Tool-design guidance (for anyone building or customizing an MCP server): "For Claude Code, we restrict tool responses to 25,000 tokens by default". Use pagination, filtering and truncation with "helpful instructions", give "specific and actionable" error messages instead of opaque codes, and offer a `response_format` of concise or detailed. — [Writing effective tools for agents (Sep 11, 2025)](https://www.anthropic.com/engineering/writing-tools-for-agents)

**Tool search / deferred tools**
- "Tool search keeps MCP context usage low by deferring tool definitions until Claude needs them. Only tool names and server instructions load at session start." `ENABLE_TOOL_SEARCH` values:
  - unset: defer all MCP tools.
  - `true`: always defer.
  - `auto` / `auto:N`: load tools upfront while their definitions fit under 10% (or N%) of context.
  - `false`: load everything upfront.
  
  — [MCP](https://code.claude.com/docs/en/mcp)
- `alwaysLoad: true` on a server (or `anthropic/alwaysLoad` on a single tool) exempts it from deferral, "for a small number of tools that Claude needs on every turn". It also makes startup wait up to 5s for that server. — [MCP](https://code.claude.com/docs/en/mcp)
- Context hygiene: prefer CLI tools where they exist, and disable unused servers in `/mcp`. — [Costs](https://code.claude.com/docs/en/costs)

**Roblox Studio MCP specifics**
- The standalone Rust server repository says: "This MCP Server is no longer being actively developed… We've shifted ongoing engineering investment to the built-in MCP Server included with Roblox Studio". Its architecture was "A web server built on `axum` that a Studio plugin long polls" plus an `rmcp` stdio server. Its tools were `run_code`, `insert_model`, `get_console_output`, `start_stop_play`, `run_script_in_play_mode`, and `get_studio_mode`. — [Roblox/studio-rust-mcp-server README](https://raw.githubusercontent.com/Roblox/studio-rust-mcp-server/main/README.md)
- The built-in Studio MCP server (official Roblox docs):
  - It is "built into Roblox Studio" and uses stdio.
  - Enable it under Assistant → … → Manage MCP Servers → "Enable Studio as MCP server". Quick connect supports Claude Code.
  - Windows command: `cmd.exe /c %LOCALAPPDATA%\Roblox\mcp.bat`.
  - Tools:
    - Scripts: `script_read`, `multi_edit`, `script_search`, `script_grep`.
    - Luau execution: `execute_luau`, with `datamodel_type` Edit/Client/Server.
    - Exploration: `search_game_tree`, `inspect_instance`.
    - Playtesting: `get_studio_state`, `start_stop_play`, `get_console_output`, `screen_capture` (optional camera position).
    - Player input: `character_navigation`, `user_keyboard_input`, `user_mouse_input`.
    - Agents and docs: a `subagent` tool (`explore`, `playtest`), `http_get`, `skill`.
    - Assets: `generate_mesh`, `generate_material`, `search_asset`, `insert_asset`, and others.
    - Session: `list_roblox_studios`. "Every tool call takes a `studio_id` parameter".
  - Troubleshooting is listed as: restart both Studio and the client, verify the binary path, check JSON syntax.
  
  — [Roblox creator-docs: Connect to the Roblox Studio MCP server](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/studio/mcp.md) (published at create.roblox.com/docs/studio/mcp)

**General troubleshooting tools**
- `/doctor` runs a setup checkup and `/mcp` shows server status. `claude --safe-mode` disables CLAUDE.md, skills, plugins, hooks and MCP servers to isolate a culprit. `/debug [description]` turns on debug logging mid-session and reads the log. — [Troubleshooting](https://code.claude.com/docs/en/troubleshooting); [Commands](https://code.claude.com/docs/en/commands)

### Inferences
- **Likely causes of "the MCP tool intermittently failed"** for this setup, roughly in order:
  1. Still using the deprecated long-polling Rust server.
  2. Studio being restarted or crashing while the stdio server stays disconnected, since Claude Code doesn't auto-reconnect stdio (fix: `/mcp reconnect <server>`).
  3. Long play-mode or Luau runs hitting the idle timeout, or being auto-backgrounded after 2 minutes.
  4. Very large outputs (game-tree dumps, screenshots) hitting `MAX_MCP_OUTPUT_TOKENS`.
  5. Several Studio windows open without explicit `studio_id` targeting.
- **Practical settings to try:**
  - Migrate to the built-in server; use user or local scope.
  - Raise `MCP_TIMEOUT` (e.g., 60000) if Studio starts slowly.
  - Raise `MAX_MCP_OUTPUT_TOKENS` (e.g., 50000) for screenshots and tree dumps.
  - Consider `alwaysLoad: true` for the Studio server, since it is used almost every turn. That trades some context for no search step.
  - Log failures with a `PostToolUseFailure` hook, and reproduce with `--debug`.
- **Screenshots as verification input:** `screen_capture` together with full-resolution image saving (v2.1.283+) lets Claude crop and zoom on cutscene frames to check for flicker or z-fighting. Anthropic's Opus 5.5 and Fable 5.1 guides say crop and zoom tools improve accuracy on dense images (see Q7).

### Gaps
- No official data on the built-in Studio MCP server's reliability, its timeouts, or the size of `screen_capture` payloads.
- The last-updated date of the Roblox doc page couldn't be retrieved (the GitHub API was blocked).

---

## 7. Official best practices for agentic coding and model-specific prompting (Opus 5.5, Fable 5.1): ambition, emphasis/ALL-CAPS, verification, avoiding premature "done"

### Takeaway
Anthropic's playbook:
- Give Claude a way to verify its work.
- Explore → plan → code → commit.
- Give specific context and rich inputs (screenshots as visual targets).
- Course-correct early, and manage context aggressively.
- For larger features, have Claude interview you, write a self-contained spec, then implement in a fresh session.
- For multi-session work, keep a structured feature or test list (JSON), a progress file, an init script and git commits, and work one feature at a time.
- For subjective quality, separate the generator from a skeptical, rubric-driven evaluator.

Prompting rules:
- Ask explicitly for ambitious output ("Go beyond the basics…").
- Explain why a rule matters.
- Dial back aggressive "CRITICAL: You MUST" language; use "IMPORTANT" on one line only.
- To avoid premature "done", use Anthropic's grounding and finish-the-task prompts, and treat a text-only end of turn as a report, not proof of completion.

### Cited Findings

**Agentic coding workflow**
- The opening table of the best-practices doc has three before/after examples:
  - Verification criteria: example test cases plus "run the tests after implementing".
  - "Verify UI changes visually": "[paste screenshot] implement this design. take a screenshot of the result and compare it to the original. list differences and fix them".
  - "Address root causes, not symptoms… don't suppress the error".
  
  — [Best practices](https://code.claude.com/docs/en/best-practices)
- Being specific: scope the task, point to sources and existing patterns, and "Describe the symptom… and what 'fixed' looks like". Rich input: `@file` references, pasted or dragged images, URLs, and piped data. — [Best practices](https://code.claude.com/docs/en/best-practices)
- Interview-first: "Interview me in detail using the AskUserQuestion tool… then write a complete spec to SPEC.md", then "start a fresh session to execute it". "The most useful specs are self-contained: they name the files and interfaces involved, state what is out of scope, and end with an end-to-end verification step." — [Best practices](https://code.claude.com/docs/en/best-practices)
- Course-correct: `Esc` to stop, `Esc Esc` or `/rewind`, "Undo that", `/clear`.
- Common failure patterns:
  - The kitchen-sink session.
  - Correcting over and over.
  - The over-specified CLAUDE.md.
  - The trust-then-verify gap ("If you can't verify it, don't ship it").
  - Infinite exploration.
  
  — [Best practices](https://code.claude.com/docs/en/best-practices)
- Note: `https://www.anthropic.com/engineering/claude-code-best-practices` now serves the docs "Best practices for Claude Code" page, so the docs version is the current source. — [Anthropic engineering URL](https://www.anthropic.com/engineering/claude-code-best-practices)

**Long-running work and harnesses**
- Two failure modes: trying to "one-shot the app", and a later session that "would look around, see that progress had been made, and declare the job done". The fixes:
  - An initializer session writes `init.sh`, `claude-progress.txt`, an initial commit, and a feature list where every item starts as `"passes": false` (200+ features in their example).
  - Coding sessions work on "only one feature at a time", commit with descriptive messages, and update the progress file.
  - Each session starts by running `pwd`, reading the progress file and git log, picking the highest-priority unfinished feature, and running a basic end-to-end test.
  - JSON was chosen because "the model is less likely to inappropriately change or overwrite JSON files compared to Markdown files".
  - The instruction used: "It is unacceptable to remove or edit tests".
  
  — [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- Platform guidance for multi-window work: use a different first-window prompt that sets up tests and scripts; keep structured test state (`tests.json`) and unstructured progress notes; "Use git for state tracking"; "Provide verification tools"; "Encourage complete usage of context". — [Prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)
- Subjective quality: turn "is this design good?" into gradable criteria. Their four were design quality, originality, craft and functionality, weighted toward design and originality. They "explicitly penalized highly generic 'AI slop' patterns" and calibrated the evaluator "using few-shot examples with detailed score breakdowns".
  - The evaluator used Playwright to interact with the live page before scoring; runs took 5–15 iterations.
  - "The wording of the criteria steered the generator… phrases like 'the best designs are museum quality' pushed designs toward a particular visual convergence."
  - The planner was "prompted… to be ambitious about scope" and to stay at the product level.
  - "every component in a harness encodes an assumption about what the model can't do on its own".
  
  — [Harness design for long-running application development](https://www.anthropic.com/engineering/harness-design-long-running-apps)
- Anthropic's Product Design team gives Claude Code Figma files and runs "autonomous loops where Claude Code writes the code for the new feature, runs tests, and iterates continuously". Teams also feed Claude screenshots to diagnose problems. — [How Anthropic teams use Claude Code](https://www.anthropic.com/news/how-anthropic-teams-use-claude-code)

**Prompting for ambitious, high-quality output**
- "If you want 'above and beyond' behavior, explicitly request it". Example: "Create an analytics dashboard. Include as many relevant features and interactions as possible. Go beyond the basics to create a fully-featured implementation." Request animations and interactive elements explicitly. — [Prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)
- Give the reason: "NEVER use ellipses" is less effective than explaining the text-to-speech reason, because "Claude is smart enough to generalize from the explanation". The Fable 5 template is "I'm working on [the larger task] for [who it's for]. They need [what the output enables]." — [Prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices); [Prompting Claude Fable 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5)
- Examples: "curate a set of diverse, canonical examples… For an LLM, examples are the 'pictures' worth a thousand words". Don't stuff in "a laundry list of edge cases". — [Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- Creative and visual defaults:
  - Without guidance, models default to "generic patterns", and "a general instruction such as 'avoid a generic AI look' mostly swaps one default for another". Name specific patterns to avoid and iterate.
  - The frontend-aesthetics prompt covers typography, a cohesive committed palette, high-impact motion moments, and atmospheric backgrounds.
  
  — [Prompting Claude Opus 5.5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5); [Prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)

**ALL-CAPS and aggressive emphasis**
- "If your prompts were designed to reduce undertriggering on tools or skills, these models may now overtrigger. The fix is to dial back any aggressive language. Where you might have said 'CRITICAL: You MUST use this tool when...', you can use more normal prompting like 'Use this tool when...'". This was measured on Opus 4.5 and 4.6; the doc says its general techniques apply to current models but should be re-checked per model. Also: "Tune anti-laziness prompting… dial back that guidance". — [Prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)
- Claude Code: use "IMPORTANT" on one line only. "If you emphasize many lines, none of them stands out." — [Best practices](https://code.claude.com/docs/en/best-practices)
- Fable 5: "Instruction-following is improved enough that you can steer most behaviors with a brief instruction rather than enumerating each behavior by name." — [Prompting Claude Fable 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5)
- Nuance: the skill-authoring guide's iteration loop expects a helper Claude may suggest stronger wording ("MUST filter" instead of "always filter") when an observed rule keeps being skipped. Escalate emphasis based on what you observe, not by default. — [Skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)

**Avoiding premature "done" and fabricated progress**
- Fable 5, ground progress claims: "Before reporting progress, audit each claim against a tool result from this session. Only report work you can point to evidence for; if something is not yet verified, say so explicitly…" In Anthropic's testing this "nearly eliminated fabricated status reports". — [Prompting Claude Fable 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5)
- Fable 5.1, finishing the whole task. Without a nudge, the model "sometimes describes what it would do next instead of doing it ('Next, I'll …') or stops to ask permission". The official block begins: "You are operating autonomously. The user is not watching in real time… Before ending your turn, check your last paragraph. If it is a plan, an analysis, a question, a list of next steps, or a promise about work you have not done… do that work now with tool calls." A second block defines scope: "The user's request… sets the scope, and the scope is the deliverable: don't quietly narrow, widen, or swap it…" — [Prompting Claude Fable 5.1](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-1)
- Opus 5.5 in unattended runs: "Treat a text-only end of turn as a report rather than as proof the task is done." Keep a checklist the model updates. If items are still open, send a short continuation naming them, and "stop after two or three automatic continuations". There is also an official system-prompt paragraph listing four unwanted kinds of early stop. — [Prompting Claude Opus 5.5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5)
- Keeping changes in scope (Fable 5.1): "If… you find a pre-existing bug, a performance concern, or behavior the task doesn't mention, don't fix, optimize or extend it in this change unless the requested behavior cannot work without it; report it as a follow-up…" — [Prompting Claude Fable 5.1](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-1)
- Avoid test-gaming and hard-coding: "Implement a solution that works correctly for all valid inputs, not just the test cases… If the task is unreasonable or infeasible, or if any of the tests are incorrect, please inform me". Investigate before answering: "Never speculate about code you have not opened." — [Prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)

**Model-specific notes (Opus 5.5 and Fable 5.1)**
- Opus 5.5's strengths: "multistep work in a real repository… until its tests pass", sustained "multi-hour" autonomous work "with parallel subagents and little oversight", stronger code review, and much better reading of charts, diagrams and screenshots. For the densest visuals, "Higher-resolution images help" and so do crop and zoom tools, which the model "uses… more effectively at higher effort levels". — [Prompting Claude Opus 5.5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5)
- Fable 5.1:
  - Writes fewer user-facing updates during long runs; ask for them if wanted.
  - May rewrite whole files; the targeted-edit instruction fixes this.
  - Tends to add unrequested fixes or tests; use the scope instruction.
  - Prose can be dense; "Please remove all mannered prose."
  - Leave room for long outputs at `xhigh` and `max`.
  - Vision work is best "when it can iteratively analyze, crop, and visually verify".
  
  — [Prompting Claude Fable 5.1](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-1)
- Fable 5:
  - "When you have enough information to act, act."
  - Build a memory system: "Store one lesson per file with a one-line summary at the top."
  - "Start at the top of your difficulty range."
  - Final summaries should read as "a re-grounding, not a continuation of your working thread".
  
  — [Prompting Claude Fable 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5)
- Overthinking control: "When you're deciding how to approach a problem, choose an approach and commit to it. Avoid revisiting decisions unless you encounter new information…" Lowering effort is the more reliable lever. — [Prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices); [Prompting Claude Opus 5.5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5)
- Visual verification on Windows: CLI computer use is "a research preview on macOS that requires a Pro or Max plan". "On Windows, use computer use in Desktop instead." — [Computer use](https://code.claude.com/docs/en/computer-use)

### Inferences
- **The ambitious-project recipe applied to this game:**
  1. Interview, then `SPEC-<feature>.md` per system (race-change cutscene, capital reveal, guiding entity/system, combat). Include out-of-scope items and an end-to-end Studio verification step.
  2. A `feature_list.json` with `passes: false` acceptance items, e.g. "reveal shot holds ≥60 FPS", "no z-fighting on the capital gate at any camera distance", "race color matches palette hex".
  3. A `progress.md` plus git commits.
  4. One feature per session, with `/goal` built on those checks.
  5. A separate rubric-driven "cinematic evaluator" subagent using `screen_capture` frames compared against reference images or mood boards. Possible criteria: cinematic coherence, originality vs. "generic Roblox" look, technical craft (frame pacing, no flicker, streaming readiness), and readability of race identity colors.
- **For the user's prompts and the SKILL.md:**
  - Replace ALL-CAPS rules with short reasons ("race colors are the player's main identity cue, so…").
  - Keep "IMPORTANT" for one or two truly critical lines.
  - Explicitly ask for "go beyond the basics" ambition on creative pieces (cutscenes, entity dialogue).
  - Add the Fable or Opus finish-and-ground prompts to CLAUDE.md or a skill for long unattended runs.

### Gaps
- Anthropic's docs have no Roblox, Luau or game-engine-specific agentic workflow guidance; mapping the web-app harness lessons to Studio is inference.
- The ALL-CAPS guidance was explicitly measured on Opus 4.5/4.6. No newer statement specific to Opus 5.5 or Fable 5.1 was found beyond "brief instructions suffice" (Fable 5) and the general principle that techniques apply to current models.
