# Roblox + AI-coding-agent tooling ecosystem and a professional pipeline that lets Claude Code build, test and verify a Roblox game (state as of 1 October 2026)

Research method note: Primary sources were read in full where reachable: Roblox/creator-docs source files on raw.githubusercontent.com, tool READMEs and CHANGELOGs, and the Claude Code MCP docs. The proxy blocked create.roblox.com and devforum.roblox.com, so DevForum announcement and bug-report content comes from WebSearch summaries. Each such claim cites the DevForum result URL. Treat dates and details from summaries as slightly less certain than READMEs and docs.

## Q1. Roblox Studio's built-in MCP server (and the deprecated Roblox/studio-rust-mcp-server): tools, Claude Code connection on Windows, limitations, timeouts, recent updates; Roblox Assistant agentic features

### Takeaway
Since March 2026, Studio ships a built-in, Roblox-maintained MCP server. It replaces the now-unmaintained Rust reference server. Its tool set is far broader than the old server's:
- script read, edit and grep
- `execute_luau` in the Edit, Server or Client datamodel
- start and stop playtest, console output, `screen_capture` with camera control
- simulated keyboard, mouse and character navigation
- explore and playtest subagents, asset search and insert, AI mesh, material and model generation
- docs fetching, and multi-Studio routing via `studio_id`

Its tools stay in lockstep with Studio's Assistant. Known 2026 bugs line up with the user's intermittent "Execute Luau" failures. Play-mode calls can fail with "Target is not reachable" on Windows, connections drop every few minutes, and connection order between Studio, Assistant and the MCP process matters.

### Cited Findings
**What it is and how it runs**
- The Roblox Studio MCP server is built into Studio. It "runs as a local process on your machine" and talks to the AI client over **stdio transport**. All actions start from the AI client — [Roblox creator-docs: studio/mcp.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/studio/mcp.md)

**Exact tool list (official doc, current file)** — all from [studio/mcp.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/studio/mcp.md):
- *Scripts:*
  - `script_read`: dot-notation paths such as `game.ServerScriptService.MyScript`, either the whole script or a line range.
  - `multi_edit`: several edits to a script in one operation, and it creates the script if the path doesn't exist. Requires `datamodel_type` (Edit).
  - `script_search`: fuzzy match by name, up to 10 results.
  - `script_grep`: string pattern across all scripts, up to 50 matches.
- *Asset/content generation:*
  - `generate_mesh`: textured mesh from a text prompt.
  - `generate_material`: returns the base material plus a variant name.
  - `generate_procedural_model`: a ProceduralModel built from primitive parts, with reference images and custom part schemas.
  - `wait_job_finished`
  - `search_asset`: Creator Store plus the user's, group's or universe's inventory, with type, price and tag filters.
  - `insert_asset`: by numeric asset ID. Covers models, meshes, images, audio, video, animations and packages.
  - `upload_image`: from HTTP URLs.
  - `store_image`: a local file to an image URI.
- *Data model exploration:*
  - `subagent`: types `explore` (codebase investigation and game-state queries) and `playtest` (runs gameplay scenarios and verifies outcomes).
  - `search_game_tree`: a flat JSON array, filterable by path, type and keywords, with a depth limit.
  - `inspect_instance`: all readable properties, attributes, and a summary of children and descendants.
- *Luau execution:*
  - `execute_luau`: "Returns either the result or an error. Requires specifying a `datamodel_type` (Edit, Client, or Server)."
- *Playtesting:*
  - `get_studio_state`: play state and available datamodel types.
  - `start_stop_play`
  - `get_console_output`
  - `screen_capture`: "Captures the current Studio viewport and returns the image data. Optionally accepts a custom camera position and look-at target."
- *Player input simulation:*
  - `character_navigation`: to a position or instance path, with a speed multiplier.
  - `user_keyboard_input`: key down, up or press, text input, wait, and targeting UI instances.
  - `user_mouse_input`: move, click, button down/up, scroll, wait, and targeting instances or screen coordinates.
- *Docs/skills:*
  - `http_get`: limited to allowed Roblox documentation URLs (Engine API reference, Creator docs, Cloud API, performance optimization guides), with keyword search.
  - `skill`: best-practice and reference material for debugging, device simulation and documentation search.
- *Session:*
  - `list_roblox_studios`: name, Studio instance ID and place ID.
  - Every tool call takes a `studio_id` parameter.

**Enabling it and connecting Claude Code**
- To enable it: **Assistant → … → Manage MCP Servers → turn on "Enable Studio as MCP server"**. A green indicator shows how many clients are connected — [studio/mcp.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/studio/mcp.md)
- **Quick connect** supports Antigravity, Codex CLI, **Claude Code**, Claude Desktop, Cursor, Gemini CLI and VS Code. The path is Assistant Settings → MCP Servers → Quick connect dropdown → toggle the client. If the client isn't listed, install it and restart Studio — [studio/mcp.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/studio/mcp.md)
- **Windows JSON configuration (official):** `{"mcpServers":{"Roblox_Studio":{"command":"cmd.exe","args":["/c","%LOCALAPPDATA%\\Roblox\\mcp.bat"]}}}`. The **Windows CLI command (official):** `cmd.exe /c %LOCALAPPDATA%\Roblox\mcp.bat`. On macOS it is `/Applications/RobloxStudio.app/Contents/MacOS/StudioMCP` — [studio/mcp.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/studio/mcp.md)
- Official troubleshooting steps: restart both Studio and the MCP client, check that the command or binary path exists, and check the JSON syntax. The doc also warns: "MCP clients can read and modify content in your open Roblox places. Make sure to only connect clients you trust." — [studio/mcp.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/studio/mcp.md)

**Claude Code MCP mechanics (official Claude Code docs)**
- Syntax and scopes:
  - Stdio syntax is `claude mcp add [options] <name> -- <command> [args...]`. Everything after `--` goes to the server untouched.
  - Scopes are local (the default, stored in `~/.claude.json` for the current project), project (`.mcp.json` in the repo, which needs approval) and user (all projects).
  - `claude mcp add-json <name> '<json>'` takes the object *inside* `mcpServers`.
  - Check status with `claude mcp get <name>` or `/mcp`.
  - Source: [Claude Code MCP docs](https://code.claude.com/docs/en/mcp)
- Timeouts:
  - Startup timeout is set via `MCP_TIMEOUT`, for example `MCP_TIMEOUT=10000 claude`.
  - A per-server tool-call timeout is set by adding `"timeout": <ms>` to that server's `.mcp.json` entry, which overrides `MCP_TOOL_TIMEOUT`. With `MCP_TOOL_TIMEOUT` unset, the wall-clock default is about 28 hours.
  - The **idle timeout for stdio servers is 30 minutes** (v2.1.203+), configurable with `CLAUDE_CODE_MCP_TOOL_IDLE_TIMEOUT`.
  - A main-conversation call running past 2 minutes is moved to a background task.
  - Source: [Claude Code MCP docs](https://code.claude.com/docs/en/mcp)
- Output limits and images:
  - MCP output above 10,000 tokens triggers a warning, and output is capped at **25,000 tokens by default**. Raise the cap with `MAX_MCP_OUTPUT_TOKENS`.
  - **Tools that return images remain subject to `MAX_MCP_OUTPUT_TOKENS`.**
  - Images from MCP tools (PNG, JPEG, GIF, WebP) are shown inline, possibly downscaled. The originals are saved to the session's `tool-results` dir (v2.1.283+), so Claude can crop or reuse them with Bash.
  - Source: [Claude Code MCP docs](https://code.claude.com/docs/en/mcp)
- With tool search (on by default), Claude Code tells Claude which server failed to connect and why. Without it, failed connections aren't reported — [Claude Code MCP docs](https://code.claude.com/docs/en/mcp)
- `claude mcp add-from-claude-desktop` "only works on macOS and Windows Subsystem for Linux (WSL)". It is not available on native Windows — [Claude Code MCP docs](https://code.claude.com/docs/en/mcp)

**Deprecated Rust server (Roblox/studio-rust-mcp-server)**
- The README warns: "This MCP Server is no longer being actively developed… We've shifted ongoing engineering investment to the built-in MCP Server included with Roblox Studio". The source and releases stay up for reference only — [Roblox/studio-rust-mcp-server README](https://github.com/Roblox/studio-rust-mcp-server)
- Architecture: an axum web server that a Studio plugin long-polls, plus an rmcp stdio server. Its tools were `run_code`, `insert_model`, `get_console_output`, `start_stop_play`, `run_script_in_play_mode` (which auto-stops play and returns logs, errors and duration) and `get_studio_mode`. The manual config was `rbx-studio-mcp.exe --stdio`. The README's Claude Code example is `claude mcp add --transport stdio Roblox_Studio -- '<path>/rbx-studio-mcp' --stdio` — [README](https://github.com/Roblox/studio-rust-mcp-server)

**Timeline of updates (from DevForum and newsroom search results)**
- **Feb 2026:** Roblox added `get_console_output`, `start_stop_play` and `run_script_in_play_mode` to the open-source server, plus "External LLM Support for Assistant" — [DevForum: Studio MCP Server Updates and External LLM Support for Assistant](https://devforum.roblox.com/t/studio-mcp-server-updates-and-external-llm-support-for-assistant/4415631)
- **5 Mar 2026:** Roblox announced the built-in server as "the recommended way to connect external AI tools to Studio". Tools are "in sync with Assistant automatically… reflected in the MCP Server in lockstep" — [DevForum: Assistant Updates: Studio Built-in MCP Server and Playtest Automation](https://devforum.roblox.com/t/assistant-updates-studio-built-in-mcp-server-and-playtest-automation/4474643)
- **Apr 2026 (Studio Beta):** a **Playtest Agent** subagent. It "spawns a test character and runs through gameplay scenarios in its own context" and offloads compute "to a separate model run by Roblox, so it's not your tokens". Only the instructions and the report enter the caller's context. Enable it via **File → Beta Features → Playtest Agent** — [DevForum: [Studio Beta] Studio Assistant & MCP Playtest Agent](https://devforum.roblox.com/t/studio-beta-studio-assistant-mcp-playtest-agent/4566767)
- **15 Apr 2026:** "Roblox Studio is Going Agentic" covered Planning Mode, the Playtesting Agent, Procedural Models, MCP Quick Connect and a Data Model Search Subagent. It stated that 44% of the top 1,000 creators use Assistant or third-party AI tools via MCP — [Roblox newsroom](https://about.roblox.com/newsroom/2026/04/roblox-studio-going-agentic); [DevForum: Data Model Search Subagent and Quick Connect for MCP Clients](https://devforum.roblox.com/t/assistant-updates-the-data-model-search-subagent-and-quick-connect-for-mcp-clients/4596579)
- **Aug 2026 multi-agent update:**
  - Explicit `studio_id` on every call. The **`set_active_studio` tool was removed**, so callers must pass `studio_id` instead.
  - `list_roblox_studios` now returns the Place ID.
  - Studio shows a connected-clients indicator, and Roblox shipped stability fixes and told users to restart AI clients after the update.
  - Sources: [DevForum: Studio MCP: Multi-Agent Improvements and Connected AI Clients](https://devforum.roblox.com/t/studio-mcp-multi-agent-improvements-and-connected-ai-clients/4820583); [BloxBot summary](https://bloxbot.ai/guide/roblox-studio-mcp-multi-agent-update-2026); [X post summarizing the update](https://x.com/HelloItsVG/status/2090196227321155849)

**Known limitations and bugs (DevForum bug-report titles and summaries)**
- On Windows, `execute_luau` fails with **"Target is not reachable" during Play Mode**. `screen_capture` and `user_keyboard_input` also fail, while `start_stop_play`, `get_console_output` and `list_roblox_studios` keep working. `execute_luau` works again after play stops — [DevForum: Studio MCP Play Mode tools fail with Target is not reachable on VSCode](https://devforum.roblox.com/t/studio-mcp-play-mode-tools-fail-with-target-is-not-reachable-on-vscode/4648112)
- "MCP keeps disconnecting every 5–10 minutes" (reported with Claude and Codex CLI). The workaround cited is to disable and re-enable the MCP server — [DevForum](https://devforum.roblox.com/t/mcp-keeps-disconnecting-every-5-10-minutes/4717243); [DevForum: MCP frequently dropping connections and not listing all, or any, open instances](https://devforum.roblox.com/t/mcp-frequently-dropping-connections-and-not-listing-all-or-any-open-instances/4737086)
- If Studio opens after StudioMCP.exe is already running, `list_roblox_studios` returns empty with "previously active Studio instance has disconnected" — [DevForum](https://devforum.roblox.com/t/studiomcp-fails-to-list-studio-instances-after-new-studio-window-opens-while-studiomcp-is-already-running/4729586). A related report: "Studio windows sometimes fail to connect to MCP when place opens before Assistant" — [DevForum](https://devforum.roblox.com/t/studio-windows-sometimes-fail-to-connect-to-mcp-when-place-opens-before-assistant/4858349)
- "StudioMCP.exe drops connection (EOF) on server/discover initialization request after recent update" — [DevForum](https://devforum.roblox.com/t/studiomcpexe-drops-connection-eof-on-serverdiscover-initialization-request-after-recent-update/4808970). There is also a feature request, "Fix Debugging API access for studio MCP" — [DevForum](https://devforum.roblox.com/t/fix-debugging-api-access-for-studio-mcp/4527431)
- A rodeo issue reports that rodeo's `test:*` and `edit:elevated` commands, which call StudioMCP, hang "when Studio's Assistant hasn't connected to StudioMCP" — [rodeo issue #4](https://github.com/rodeo-rbx/rodeo/issues/4)

**Roblox Assistant agentic features and how they relate to external agents**
- Assistant combines an LLM with "a run-command system that can act directly on your data model". It covers chats, branching, cloud chat history scoped per place, and a **screen-capture subagent** that describes the viewport. "If you're using a third-party client via MCP or your own API key, you continue to have direct access to the underlying screenshot tool." — [creator-docs assistant/guide.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/assistant/guide.md)
- **Planning Mode** (`/plan`) produces editable Markdown plans. They are stored in the cloud per experience and creator, and execution needs an explicit **Build** click ("Plans never auto-execute") — [assistant/guide.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/assistant/guide.md)
- Generation limits: procedural models are capped at **50 per rolling 24-hour window**. `generate_mesh` defaults to a 10,000-triangle cap, and segmentation allows up to 8 parts per generated model — [assistant/guide.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/assistant/guide.md)
- Bring-your-own key: "Open **Assistant** → **…** → **Manage API Keys** to configure your preferred model from Anthropic, OpenAI, or Google" — [creator-docs ai/accelerated-workflows.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/ai/accelerated-workflows.md)

### Inferences
- **Likely explanation of the user's intermittent "Execute Luau" failures:** The symptom matches the documented 2026 bugs: play-mode routing errors, periodic disconnects, and startup-order problems. Practical mitigations:
  1. Before each batch, call `get_studio_state` and `list_roblox_studios`, and pass the right `studio_id` and `datamodel_type`. Use Edit for building, and Server or Client only while playtesting.
  2. Start Studio and open Assistant before starting Claude Code, and restart Claude Code after Studio updates.
  3. If calls start failing, toggle "Enable Studio as MCP server" off and on.
  4. Keep executed snippets short, idempotent and free of infinite loops or long yields. The docs give no execute timeout for the built-in server, but Claude Code's stdio idle timeout is 30 minutes.
- **Recommended Claude Code setup on Windows.** First choice is Studio's **Quick connect → Claude Code** toggle. If configuring by hand, a project-scoped `.mcp.json` avoids PowerShell quoting problems:
  `{"mcpServers":{"Roblox_Studio":{"command":"cmd.exe","args":["/c","%LOCALAPPDATA%\\Roblox\\mcp.bat"],"timeout":600000}}}`.
  The CLI equivalent, built from the documented Roblox command and Claude Code syntax but not tested on Windows, is:
  `claude mcp add --transport stdio --scope user Roblox_Studio -- cmd.exe /c "%LOCALAPPDATA%\Roblox\mcp.bat"`. Here `cmd.exe` expands `%LOCALAPPDATA%` at launch.
  Set `MAX_MCP_OUTPUT_TOKENS` higher if `screen_capture` images or large `search_game_tree` results get truncated.
- The playtest subagent runs on Roblox's model, not the user's Claude tokens, and returns only a report. It is a cheap way for a Pro-plan user to get gameplay QA without filling Claude's context.
- Don't run the deprecated Rust server alongside the built-in one. Both register as "Roblox_Studio"-style servers with overlapping tools, which risks confusion. The docs say nothing about whether they conflict.

### Gaps
- Could not open DevForum posts. Exact release dates, version numbers and bug-fix status for the built-in server (for example, whether "Target is not reachable" is fixed as of October 2026) are unverified beyond search summaries.
- No official documentation was found for `execute_luau` timeout, output-size limits, or behaviour when a script yields or loops forever in the built-in server.
- No public changelog or version numbering for the built-in server was found. It is not clear which scope or file Studio's Quick Connect writes into Claude Code's config.

## Q2. Community MCP servers for Roblox Studio: extra capabilities, maturity, safety

### Takeaway
The most popular community server, boshyxd/robloxstudio-mcp, was **archived on 6 June 2026**. Its author recommends the actively maintained **Chrrxs/robloxstudio-mcp** fork. That fork adds things the built-in server lacks: per-peer server and client runtime eval, multi-client playtests, ScriptProfiler and MicroProfiler capture, memory and scene-cost analysis, non-pausing breakpoints, and asset security scans.

Other servers (EL4CTEO/rbx-studio-mcp, rodeo CLI, paralov, IDKDeadXD) are newer and less proven. Some, notably EL4CTEO's Open Cloud "live" tools, can touch the *published* game. Treat them as optional add-ons next to the official server, not replacements.

### Cited Findings
**boshyxd/robloxstudio-mcp — archived**
- Archived 6 June 2026. The author lost NPM account access and recommends switching to the Chrrxs fork. The last README version line reads v2.7.0-next.6, "43 tools, inspector edition". Setup needed a Studio plugin and **Allow HTTP Requests**. The command was `claude mcp add robloxstudio -- npx -y robloxstudio-mcp@latest`, and Windows users were told to use `"command":"cmd","args":["/c","npx",...]` if they hit issues — [boshyxd README](https://github.com/boshyxd/robloxstudio-mcp)
- Its read-only "Inspector Edition" exposed 31 tools, including `get_output_log`, `get_playtest_output`, `capture_screenshot`, `grep_scripts` and `search_by_property` — [boshyxd README](https://github.com/boshyxd/robloxstudio-mcp)

**Chrrxs/robloxstudio-mcp (npm `@chrrxs/robloxstudio-mcp`), based on boshyxd v2.7.0**
- Runtime: `eval_server_runtime` and `eval_client_runtime` share the game's `require` cache. `breakpoints` records hits "without pausing the playtest", and `get_runtime_logs` reads edit, server or per-client logs, including startup messages — [Chrrxs README](https://github.com/Chrrxs/robloxstudio-mcp)
- Playtests: `solo_playtest` and `multiplayer_playtest` run multi-client sessions. `manage_instance` opens or closes Studio with a baseplate, a local file, a published place or an older revision — [Chrrxs README](https://github.com/Chrrxs/robloxstudio-mcp)
- Performance: `capture_script_profiler`, `capture_micro_profiler`, `get_memory_breakdown` and `get_scene_analysis` ("attribute scene cost") — [Chrrxs README](https://github.com/Chrrxs/robloxstudio-mcp)
- Edit mode: `execute_luau`, `set_properties` and `find_and_replace_in_scripts`, plus a "verified chunk-staging workflow" for large generated Luau with UTF-8 byte/hash readback. `selection` frames a part before `capture_screenshot`, and keyboard and mouse input are supported — [Chrrxs README](https://github.com/Chrrxs/robloxstudio-mcp)
- Assets: `insert_asset` "removes scripts and package links, verifies the cleaned result", and `preview_asset` shows a security scan before insert. `get_roblox_docs` and `get_roblox_skills` provide docs — [Chrrxs README](https://github.com/Chrrxs/robloxstudio-mcp)
- Claude Code install: `claude mcp add robloxstudio -- npx -y @chrrxs/robloxstudio-mcp@latest --auto-install-plugin`. Studio must be fully restarted, and the plugin shows "Connected". A read-only Inspector edition is `@chrrxs/robloxstudio-mcp-inspector`, and only one variant can be installed at a time — [Chrrxs README](https://github.com/Chrrxs/robloxstudio-mcp)
- Security and transport:
  - The HTTP bridge binds to `127.0.0.1`.
  - Tool-invoking HTTP endpoints need a shared-secret token stored at `~/.robloxstudio-mcp/auth-token`.
  - Studio traffic runs over an authenticated WebSocket, and reconnection uses backoff of 0.5→5 s with 20 s phase deadlines.
  - Setting `ROBLOX_STUDIO_HOST` to a non-loopback address exposes the bridge, which the docs say to do only on trusted networks.
  - Source: [Chrrxs docs/configuration.md](https://github.com/Chrrxs/robloxstudio-mcp/blob/main/docs/configuration.md)
- Token discipline: the serialized tool catalog is capped at 43,000 characters, tool descriptions at 120 characters, and detailed guides are fetched on demand (`robloxstudio://tool-guides`) — [Chrrxs docs/token-efficiency.md](https://github.com/Chrrxs/robloxstudio-mcp/blob/main/docs/token-efficiency.md)
- Signs of active maintenance and rough edges: PR #91 adds an `execute_luau` output budget, queue metrics and dedupe — [PR #91](https://github.com/Chrrxs/robloxstudio-mcp/pull/91). Issue #94 covers "repeated capture_script_profiler timeout" — [issue #94](https://github.com/Chrrxs/robloxstudio-mcp/issues/94)

**EL4CTEO/rbx-studio-mcp (npm `@el4cteo/rbx-studio-mcp`)**
- MIT licensed with "35 tools" (search snippets say 34). Install the plugin with `npx -y @el4cteo/rbx-studio-mcp --install-plugin` and the server with `claude mcp add roblox-studio -- npx -y @el4cteo/rbx-studio-mcp`. It uses loopback port 44755 and has a `doctor` command — [EL4CTEO README](https://github.com/EL4CTEO/rbx-studio-mcp)
- Tool groups: session, discover, scripts (including `sync`), instances, world (`geometry`, `terrain`, `collision`, `undo`), run and debug (`playtest`, `execute_luau`, `input`, `console`, `debug`, `performance`) and look (`screenshot`, `viewport`, `device`). "Write tools take arrays — ten script edits is one call, one Ctrl+Z, and all-or-nothing." — [EL4CTEO README](https://github.com/EL4CTEO/rbx-studio-mcp)
- Its `sync` tool mirrors scripts to disk in a Rojo-style layout with pull, push and watch modes. It detects conflicts, sends deleted scripts to `.rbx-sync/trash`, and can export UI or instance trees as `.build.json` — [EL4CTEO README](https://github.com/EL4CTEO/rbx-studio-mcp)
- **Risk surface:** With an Open Cloud key it can `execute_luau target="live"` on the published place, read and write live DataStores, and use `universe` to restart servers, ban players and sell products. Keys are stored at `~/.rbx-studio-mcp/credentials.json` — [EL4CTEO README](https://github.com/EL4CTEO/rbx-studio-mcp)
- Known issues: screenshots during playtest returned a black screen ([issue #1](https://github.com/EL4CTEO/rbx-studio-mcp/issues/1)), and a non-integer timeout crashed the server process in the `input` tool ([issue #4](https://github.com/EL4CTEO/rbx-studio-mcp/issues/4)). There is a DevForum thread: [Open Source Studio MCP — safe script edits, real playtest input, screenshots, batched undo](https://devforum.roblox.com/t/open-source-studio-mcp-%E2%80%94-safe-script-edits-real-playtest-input-screenshots-batched-undo/4823085)

**rodeo (rodeo-rbx/rodeo): a terminal automation CLI, not MCP**
- rodeo executes code "in any Studio environment" from the terminal. Options include `--mode edit|run|test|play`, `--dom edit|server|client` and `--context plugin|server|client|elevated|cmdbar`, where `elevated` goes "via StudioMCP". It pipes stdin and stdout, can export and import `.rbxm`, and can "bake" runtime data into `.luau` — [rodeo README](https://github.com/rodeo-rbx/rodeo)
- Status: "macOS and Windows are fully supported… Breaking changes to API may happen." — [rodeo README](https://github.com/rodeo-rbx/rodeo)

**Other servers (maturity unverified)**
- `lolofuk123/rbx-mcp`: an execute tool with `timeoutMs` from 1,000 to 600,000 ms, default 30 s — [glama listing](https://glama.ai/mcp/servers/lolofuk123/rbx-mcp)
- `paralov/roblox-studio-opencode-mcp` — [GitHub](https://github.com/paralov/roblox-studio-opencode-mcp)
- `IDKDeadXD/roblox-studio-mcp` ("Production… build, test and debug Roblox games autonomously") — [GitHub](https://github.com/IDKDeadXD/roblox-studio-mcp)
- Multiple re-uploads and forks exist, for example `bgd4141221/robloxstudio-mcp` and `Codder13/rbx-studio-mcp` — [search results](https://github.com/bgd4141221/robloxstudio-mcp), [Codder13](https://github.com/Codder13/rbx-studio-mcp)

### Inferences
- **For a solo developer seeking quality**, use the **official built-in server as the primary bridge**. It is supported, in lockstep with Assistant, and includes the playtest agent and screen capture. Add **Chrrxs/robloxstudio-mcp** only for gaps: profiler capture, scene-cost analysis, per-peer client and server eval, and multi-client tests.
- Start with the **Inspector (read-only)** edition if the goal is diagnostics only. That lowers the risk of two write-capable servers editing the same place.
- Avoid granting any community MCP an Open Cloud key that can act on the live game. EL4CTEO's `target="live"` and `universe` tools could hit real players.
- Re-uploads and forks of popular repos (for example `bgd4141221/…`, which reuses Chrrxs's description) are a supply-chain risk. Install only from the canonical repo or npm scope. Pin versions instead of `@latest` once the setup is stable.

### Gaps
- No independent security audit was found for any community server. Star counts, download counts and issue-response times were not collected because the GitHub API was blocked.
- No source compares the reliability of Chrrxs's `execute_luau` with the built-in one.

## Q3. File-based workflows (Script Sync, Rojo, Argon) with git, combined with Studio MCP; pros and cons for AI-driven development

### Takeaway
Roblox now officially recommends a "coding harness" setup: **Studio Script Sync**, which became generally available on 17 June 2026, for code-as-files; the **built-in MCP** for everything Script Sync can't reach (UI, StarterPack, instances, playtests); and **Git**. The guide names Claude Code explicitly.

Rojo 7.7.0 (1 July 2026) remains the choice when the *whole project* should live on disk. Argon 2.0.29 offers two-way instance sync. For this user, who builds a large world by hand in Studio, Script Sync plus MCP plus Git is the lowest-friction path. Code gets diffs and rollback, and the map stays Studio-native.

### Cited Findings
**Roblox's official "Build with a coding harness" guide** — all from [creator-docs ai/coding-harness.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/ai/coding-harness.md):
- Prerequisites are an AI editor, Studio and Git. It names VS Code with the **Claude Code** extension or Cursor, and the Windows install is `winget install --id Git.Git -e --source winget`.
- Save the place as `.rbxlx` inside the project folder. The starter `.gitignore` excludes `.rbxlx`.
- Script Sync maps ServerScriptService, ReplicatedStorage and StarterPlayerScripts to matching folders.
- MCP "covers anything Script Sync cannot reach, such as **StarterGui** and **StarterPack**".
- For verification, the agent runs `game:GetService("InstanceFileSyncService"):GetStatus(instance)` and starts a playtest to confirm output. The final step is a git commit.
- The guide still calls Script Sync a "beta" to enable under File → Beta Features. That looks out of date given the June 2026 full release.

**Script Sync** — all from [creator-docs scripting/sync.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/scripting/sync.md) unless noted:
- Full release was announced on **17 June 2026**, adding conflict resolution, safer deletion, a simpler workflow and Team Create indicators — [DevForum: [Full Release] Studio Script Sync](https://devforum.roblox.com/t/full-release-studio-script-sync/4688454); [Weekly Recap June 15–18, 2026](https://devforum.roblox.com/t/weekly-recap-june-15-june-18-2026/4691531)
- Behaviour:
  - It syncs **only Script, LocalScript, ModuleScript and Folder**.
  - Limits are 10,000 scripts per top-level synced instance and 128 top-level synced instances.
  - A conflict dialog offers Keep Studio or Keep Disk.
  - Naming: `name.luau` → ModuleScript, `.server.luau`, `.client.luau`, `.local.luau`, `.legacy.luau`, `.plugin.luau`, and `init.*.luau` for a script with children.
  - "Don't sync scripts that have attributes or tags… can lead to data loss."
  - Names must be filesystem-compatible, with no duplicates.
  - "It is currently not possible to control Roblox Studio's debugger from an external development environment."
- The doc recommends the Luau Language Server extension **plus** the Luau Language Server Companion Studio plugin, as well as selene and StyLua. It also says to use Script Sync if you want only code in version control, and Rojo-style tools if the file system should be the source of truth for the whole project.

**Rojo**
- Rojo works on scripts and models from the filesystem, versions with Git, streams `rbxm`/`rbxmx`, and packages and deploys from the CLI. `rojo syncback` pulls instances from place files into a project, and the plugin has an optional two-way sync. "Fully automatic conversion of every existing game into a Rojo project [is] still limited and may require manual project configuration." — [Rojo README](https://github.com/rojo-rbx/rojo)
- **7.7.0 (1 July 2026)** changes:
  - `inf` and `nan` properties now sync.
  - Syncback now handles actors and remotes as JSON.
  - Instances that share a name are matched more robustly.
  - Clear errors replace panics.
  - `rojo serve` validates Host and Origin against DNS rebinding.
  - Unreleased fixes cover Windows `\\?\` verbatim-path bugs that broke `rojo sourcemap`, silently stopped `rojo serve` syncing, and broke luau-lsp require types.
  - Source: [Rojo CHANGELOG](https://github.com/rojo-rbx/rojo/blob/master/CHANGELOG.md)
- Official Roblox docs flow: install via **Rokit** (`rokit.toml` example: `rojo = "rojo-rbx/rojo@7.6.1"`, `wally = "upliftgames/wally@0.3.2"`, `lune = "lune-org/lune@0.10.4"`), then `rojo plugin install`, `rojo init`, `rojo build -o x.rbxl`, `rojo serve`. Wally `Packages` are mapped into `default.project.json`. "No part of this workflow involves any lock-in." — [creator-docs projects/external-tools.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/projects/external-tools.md)

**Argon**
- A CLI, VS Code extension and Studio plugin with "Two-Way sync of code and other instances with their properties", rbxl and rbxlx builds, and "Workflow automation (CI/CD)" — [Argon README](https://github.com/argon-rbx/argon). The latest release is **2.0.29 (18 May 2026)** — [Argon CHANGELOG](https://github.com/argon-rbx/argon/blob/main/CHANGELOG.md)

**Third-party comparison (vendor blog, weigh accordingly)**
- In this framing the Rojo approach "integrates more naturally with Git", while the Script Sync plus MCP route is official tooling. The vendor's `npx roxlit setup` installs Rojo and generates AI context files — [Roxlit blog](https://roxlit.dev/blog/how-to-connect-claude-code-to-roblox-studio)

### Inferences
**Pros for AI-driven work.** Files give Claude its native Read, Edit and Grep tools, which are cheaper in context than MCP `script_read` and `multi_edit`. They also give git diffs for every AI change, cheap rollback (`git restore` or `git revert`), and the ability to run luau-lsp, selene, StyLua and tests on every edit, for example from Claude Code hooks. Committing before each agent session acts as a safety checkpoint.

**Cons and risks:**
- Script Sync leaves non-script content outside git: maps, the capital city, lighting, cutscene rigs, UI instances. Keep dated `.rbxl` backups, Studio version history, or `.rbxm` exports of key models. rodeo's `exportInstances`, EL4CTEO's `.build.json` export and Rojo `syncback` can each produce these.
- Never let Claude edit the same script both through MCP `multi_edit` and through the synced file in one session. Pick files as the source of truth for code, to avoid sync conflicts.
- Avoid tags and attributes on synced scripts because of the documented data-loss risk.

**Recommendation for this user:**
1. Adopt Script Sync for all script folders.
2. Initialise git with `.rbxl` and `.rbxlx` ignored, and keep separate place backups.
3. Keep MCP for instance building, UI, playtests and measurement.
4. Move to Rojo (partially managed) or Argon later only if UI and configuration instances need to be versioned as files.
5. Note that luau-lsp CLI analysis needs a `sourcemap.json`. A small Rojo `default.project.json` that mirrors the Script Sync folders, used only for `rojo sourcemap`, is a common trick, but it is not documented by Roblox.

### Gaps
- No source compares the performance of Script Sync with Rojo, or Script Sync's reliability on very large codebases, beyond the documented limits.
- The details of Rojo `syncback` (which property types round-trip) and the maturity of two-way sync were not documented on reachable pages, because rojo.space was blocked.
- It is unclear whether Script Sync writes a sourcemap usable by `luau-lsp analyze`. The doc only mentions the editor plugin route.

## Q4. Luau verification tooling Claude can run itself: luau-lsp analyze, selene, StyLua, --!strict, Wally and pesde, Jest and TestEZ, Lune, run-in-roblox, Open Cloud Luau Execution, CI

### Takeaway
Claude can run a full local quality gate from the terminal:
- `luau-lsp analyze` (1.70.1, 27 September 2026) with Roblox type definitions and a sourcemap
- `selene` (0.31.0) with `std = "roblox"`
- `stylua --check` (2.5.2)
- **Jest Roblox** tests, executed in a real engine via `jest-roblox-cli`'s headless `studio-cli` backend (local, no API key) or via the **Open Cloud Luau Execution API** (cloud; rate-limited)

Studio's own `--task RunScript` CLI and rodeo give one-shot scripted runs. Lune runs Luau and manipulates place files outside Roblox, but it does not run games. Rokit manages all these tool versions. jsdotlua/jest-lua, TestEZ and run-in-roblox look legacy.

### Cited Findings
**luau-lsp (latest 1.70.1, 2026-09-27, synced to upstream Luau 0.740)** — [luau-lsp CHANGELOG](https://github.com/JohnnyMorganz/luau-lsp/blob/main/CHANGELOG.md)
- Standalone analysis is `luau-lsp analyze`, which provides "type and lint warnings in CI, with full Rojo resolution and API types support". Rojo sourcemaps come from `rojo sourcemap --watch default.project.json --output sourcemap.json`, and `.luaurc` configures strictness, lints and aliases — [luau-lsp README](https://github.com/JohnnyMorganz/luau-lsp)
- **Limitation:** in diagnostics, DataModel instance types resolve to `any` by default "to reduce false positives". Enable `luau-lsp.diagnostics.strictDatamodelTypes` to type-check them. A companion Studio plugin supplies DataModel info for instances outside the Rojo tree — [luau-lsp README](https://github.com/JohnnyMorganz/luau-lsp)
- CLI flags found in the changelog:
  - `--platform` (a warning appears if `--platform=roblox` is used without definitions)
  - `--definitions:@roblox=path/to/globalTypes.d.luau` (the name prefix has been required since about 1.56)
  - `--sourcemap`, `--settings=settings.json` (honors `luau-lsp.fflags.enableNewSolver` and `strictDatamodelTypes`), `--base-luaurc=PATH`, `--ignore=GLOB` and `--no-strict-dm-types`
  - Exit code is non-zero on errors.
  - `luau-lsp require-graph` emits JSON or DOT.
  - Source: [luau-lsp CHANGELOG](https://github.com/JohnnyMorganz/luau-lsp/blob/main/CHANGELOG.md)
- Roblox type definitions are served at `https://luau-lsp.pages.dev/type-definitions/globalTypes.{None|PluginSecurity|LocalUserSecurity|RobloxScriptSecurity}.d.luau`, and API docs at `.../api-docs/en-us.json`. The default security level is PluginSecurity — [luau-lsp CHANGELOG](https://github.com/JohnnyMorganz/luau-lsp/blob/main/CHANGELOG.md)
- The older luau-analyze-rojo was merged into luau-lsp, so `luau-lsp analyze` is the replacement — [luau-lsp CHANGELOG](https://github.com/JohnnyMorganz/luau-lsp/blob/main/CHANGELOG.md)

**selene (0.31.0, 2026-05-20)**
- Configure with `std = "roblox"` in `selene.toml`. The Roblox std is auto-generated and refreshed every 6 hours, and can be forced with `selene update-roblox-std`. It can be pinned with `roblox-std-source = "pinned"` into `roblox.yml`, and there is a `roblox+testez` std — [selene Roblox guide](https://github.com/Kampfkarren/selene/blob/main/docs/src/roblox.md)
- 0.30 and 0.31 added parser support for recent Luau, including `const`, string `require` and `Enum:FromName()` — [selene CHANGELOG](https://github.com/Kampfkarren/selene/blob/main/CHANGELOG.md). selene's stated priority is "okay to not diagnose every problem, as long as the diagnostics that are made are never wrong" — [selene README](https://github.com/Kampfkarren/selene)

**StyLua (2.5.2, 2026-05-16)**
- A deterministic formatter for Luau that follows the Roblox Lua Style Guide. `--check` reports files needing formatting without writing them, and `--verify` checks the output. Configure with `.stylua.toml` (`syntax = ...`). Install via GitHub releases, `npx @johnnymorganz/stylua-bin`, Aftman/Rokit or the `stylua-action` GitHub Action — [StyLua README](https://github.com/JohnnyMorganz/StyLua); [StyLua CHANGELOG](https://github.com/JohnnyMorganz/StyLua/blob/main/CHANGELOG.md)

**Toolchain and packages**
- **Rokit** is the "next-generation toolchain manager", drop-in compatible with Foreman and Aftman. Windows install: `Invoke-RestMethod https://raw.githubusercontent.com/rojo-rbx/rokit/main/scripts/install.ps1 | Invoke-Expression` — [Rokit README](https://github.com/rojo-rbx/rokit)
- **Wally** is the Roblox package manager with a CLI and registry. Rokit is "preferred" for installing it (`rokit init`, `rokit add wally`) — [Wally README](https://github.com/UpliftGames/wally)
- **pesde** is "a package manager for the Luau programming language, designed to prevent runtime lock-in", with docs at docs.pesde.dev — [pesde README](https://github.com/pesde-pkg/pesde)

**Testing frameworks**
- **Jest Roblox** (Roblox/jest-roblox) is a Roblox port of Jest 27.4.7 that "can run within Roblox itself, including via Roblox's OCALE (Open Cloud API for Luau Execution) for testing on CI systems". Install with Wally: `Jest = "roblox/jest@=3.20.0"`, `JestGlobals = "roblox/jest-globals@=3.20.0"` — [Roblox/jest-roblox README](https://github.com/Roblox/jest-roblox)
- **jsdotlua/jest-lua** "can currently only run inside of Roblox". Its last listed release is **3.10.0 (2024-10-02)** — [jest-lua README](https://github.com/jsdotlua/jest-lua); [jest-lua CHANGELOG](https://github.com/jsdotlua/jest-lua/blob/main/CHANGELOG.md)
- **TestEZ** is a BDD framework that "can run within Roblox itself, as well as inside Lemur for testing on CI systems" — [TestEZ README](https://github.com/Roblox/testez)
- **jest-roblox-cli** (`npm i @isentinel/jest-roblox`, or a standalone binary via `rokit add christopher-buss/jest-roblox-cli`) — [jest-roblox-cli README](https://github.com/christopher-buss/jest-roblox-cli):
  - Three backends: **open-cloud** (remote), **studio** (attached) and **studio-cli**. The studio-cli backend "launches Roblox Studio headless via Studio's `--task RunScript` interface… No API key, no upload", needs Studio logged in and `rojo` on PATH, and caches under `%LOCALAPPDATA%\jest-roblox` on Windows.
  - Output formatters include **"agent"**, JSON and GitHub Actions. It also does coverage.
  - Open Cloud needs `ROBLOX_OPEN_CLOUD_API_KEY`, `ROBLOX_UNIVERSE_ID` and `ROBLOX_PLACE_ID`, with scopes `universe-places:write` and `universe.place.luau-execution-session:write`.
  - "Roblox allows about **30 task creates per rolling hour per account**", so the tool never retries task creation.

**Running Luau in a real engine**
- **Studio CLI (official):** `RobloxStudioBeta.exe` lives at `%localappdata%\Roblox\Versions\[version]\`. `--task RunScript --runScriptFile <path> [--outputFile <path>] [--quitAfterExecution]` runs a script after a place loads, at command-bar permission level. It works with `--placeId` and `--universeId`, or `--localPlaceFile`, and otherwise uses the default Baseplate. When launched from the CLI, Studio pipes verbose logs to stdout. Example: `RobloxStudio.exe --task RunScript --placeId … --universeId … --runScriptFile smokeTest.luau --outputFile out.log --quitAfterExecution` — [creator-docs studio/command-line-interface.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/studio/command-line-interface.md)
- **run-in-roblox** (rojo-rbx) runs a place, model or script in Studio and pipes output to stdout/stderr. Its README still references Foreman, version 0.3.0 and Rust 1.37 — [run-in-roblox README](https://github.com/rojo-rbx/run-in-roblox)
- **Lune 0.10.5 (2 July 2026)** is a standalone Luau runtime with filesystem, network and stdio APIs, a task-scheduler port, and an optional library for "manipulating Roblox place & model files". It is not meant for "Running full Roblox games outside of Roblox". 0.10.5 added `QueryDescendants` and `registerClass`/`registerService` — [Lune README](https://github.com/lune-org/lune); [Lune CHANGELOG](https://github.com/lune-org/lune/blob/main/CHANGELOG.md)

**Open Cloud Luau Execution API ("OCALE")**
- It "allows tools to headlessly run Luau scripts in a Roblox place, within the Roblox engine". The task timeout parameter accepts 1–300 s, and the default was raised from 30 s to 5 minutes. An optional place version is accepted — [DevForum: [Beta] Open Cloud Engine API for Executing Luau](https://devforum.roblox.com/t/beta-open-cloud-engine-api-for-executing-luau/3172185); [DevForum: timeout feature request](https://devforum.roblox.com/t/allow-setting-a-timeout-for-open-cloud-luau-execution-tasks/3420987); [docs page (blocked; URL from search)](https://create.roblox.com/docs/cloud/reference/features/luau-execution)
- Roblox's official sample **place-ci-cd-demo** runs selene lint, a StyLua check, a Rojo build of the RBXL, upload to a *test* place, Luau test execution via OCALE, and Rojo deploy. The key needs `universe.places:write` and `universe.place.luau-execution-session:write`. The API "is currently limited to **two concurrent request per universe**", handled with a GitHub Actions concurrency group. The README warns "It has not been battle tested" — [Roblox/place-ci-cd-demo README](https://github.com/Roblox/place-ci-cd-demo)
- More references: binary input/output example ([Roblox/open-cloud-execution-binary-payloads-example](https://github.com/Roblox/open-cloud-execution-binary-payloads-example)) and the `rbxcloud` CLI ([rbxcloud](https://github.com/sleitnick/rbxcloud); [rbxcloud Luau Execution docs](https://sleitnick.github.io/rbxcloud/cli/cli-luau-execution/))

### Inferences
**Suggested local gate.** Pin `rojo`, `selene`, `stylua`, `luau-lsp`, `lune`, `wally` and `jest-roblox-cli` in `rokit.toml`, then have Claude, or a Claude Code hook, run after every change:
- `stylua --check src`
- `selene src`
- `luau-lsp analyze --platform=roblox --definitions:@roblox=globalTypes.d.luau --sourcemap=sourcemap.json src` (definitions file downloaded from luau-lsp.pages.dev)
- `jest-roblox --backend studio-cli --formatters agent`

This command line is assembled from documented flags but has not been run as a whole. Use `--!strict` at the top of new modules. Consider enabling the new solver via `--settings` only after confirming it is stable for this codebase.

**Legacy or superseded tools:**
- jsdotlua/jest-lua has had no release since October 2024, and Roblox now publishes `roblox/jest` 3.20.0 itself. Use Roblox/jest-roblox.
- TestEZ points to Lemur for CI, which is an old approach. Prefer Jest Roblox for new tests.
- run-in-roblox is superseded in practice by Studio's official `--task RunScript` and by rodeo and jest-roblox-cli.
- Foreman and Aftman are superseded by Rokit.

**Using OCALE well.** Given about 30 task creates per hour per account and 2 concurrent sessions per universe, OCALE suits CI on push. Use the local headless Studio for the fast inner loop. Use a dedicated test place, never production, as in Roblox's demo.

### Gaps
- Could not read the official OCALE reference page, which was blocked. Exact endpoint paths, log and output size limits and current concurrency limits are unverified. The "2 concurrent per universe" figure comes from a demo README that says Roblox aims to lift it.
- No source confirmed whether Script Sync projects can use `luau-lsp analyze` without a Rojo project file.
- No benchmark of the new Luau type solver's false-positive rate on Roblox code was found.

## Q5. Giving Claude "eyes" and measurements: screenshots, logs, MicroProfiler dumps, ScriptProfiler, Stats (FPS, memory, draw calls), automated visual checks

### Takeaway
Claude can now see and measure directly:
- the built-in MCP's `screen_capture` (with a scripted camera position), `get_console_output` and simulated input
- the playtest subagent
- `execute_luau` in the **Client** datamodel during play, reading new `Stats` properties: `FrameTime`, `RenderCPUFrameTime`, `RenderGPUFrameTime`, `SceneDrawcallCount`, `SceneTriangleCount`, shadow and UI draw calls, and memory by category
- MicroProfiler dumps saved as HTML to `%LOCALAPPDATA%\Roblox\logs`, which Claude can read
- the Chrrxs fork's one-call profiler and scene-cost tools

Claude Code shows MCP images inline and saves the originals to disk. No official automated visual-regression tool exists, so visual checks have to be scripted.

### Cited Findings
**Screenshots and logs via MCP**
- Built-in MCP: `screen_capture` captures the current viewport, optionally from a custom camera position and look-at target. `get_console_output` reads the Output log. The `user_keyboard_input`, `user_mouse_input` and `character_navigation` tools and the `playtest` subagent drive gameplay — [studio/mcp.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/studio/mcp.md)
- Assistant's screen-capture subagent works in Edit and Play modes. Third-party MCP clients keep "direct access to the underlying screenshot tool" — [assistant/guide.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/assistant/guide.md)
- Known issue: on Windows, `screen_capture` and input tools fail during Play Mode with "Target is not reachable" — [DevForum bug](https://devforum.roblox.com/t/studio-mcp-play-mode-tools-fail-with-target-is-not-reachable-on-vscode/4648112)
- Claude Code renders MCP images inline, may downscale them, and saves the original bytes in `tool-results` so Claude "can then crop, convert, or reuse the full-resolution file with tools such as Bash" (v2.1.283+) — [Claude Code MCP docs](https://code.claude.com/docs/en/mcp)
- Community options:
  - Chrrxs: `capture_screenshot`, framing via `selection`, and `get_runtime_logs` per peer — [Chrrxs README](https://github.com/Chrrxs/robloxstudio-mcp)
  - EL4CTEO: `screenshot`, `viewport`, `device`, `performance` and `console`, with a known issue of black screenshots during playtest — [EL4CTEO README](https://github.com/EL4CTEO/rbx-studio-mcp); [issue #1](https://github.com/EL4CTEO/rbx-studio-mcp/issues/1)
- OS-level fallback on Windows: PowerShell with `System.Drawing` and `Graphics.CopyFromScreen`, saving with `$bitmap.Save($file, [System.Drawing.Imaging.ImageFormat]::Png)`. Window-specific capture uses the window bounds — [PDQ: Capturing screenshots with PowerShell and .NET](https://www.pdq.com/blog/capturing-screenshots-with-powershell-and-net/)

**Measurements via the Stats service, readable from executed Luau** — all from [creator-docs Stats.yaml](https://github.com/Roblox/creator-docs/blob/main/content/en-us/reference/engine/classes/Stats.yaml):
- `Stats.FrameTime` is "only available in client scripts". It is the time of the most recent frame in seconds: "Divide `1` by this value to calculate an FPS value".
- `Stats.RenderCPUFrameTime` and `Stats.RenderGPUFrameTime` measure CPU-side and GPU-side render time per frame.
- `Stats.SceneDrawcallCount` and `Stats.SceneTriangleCount` give scene draw calls and triangles: "A high draw call count could mean a scene is too complex or unoptimized".
- `ShadowsDrawcallCount`, `ShadowsTriangleCount`, `UI2DDrawcallCount`, `UI2DTriangleCount`, `UI3DDrawcallCount` and `UI3DTriangleCount` cover shadows and UI.
- Also available: `PhysicsStepTime`, `HeartbeatTime`, `InstanceCount`, `PrimitivesCount`, `MovingPrimitivesCount`, `ContactsCount`, and the data and physics send/receive kbps counters.
- `Stats.HeartbeatTimeMs` is **deprecated**: "Use `Class.Stats.HeartbeatTime` instead".
- `GetTotalMemoryUsageMb()`, `GetMemoryUsageMbForTag()`, `GetMemoryUsageMbAllCategories()` and `GetMemoryCategoryNames()` are available. The category APIs return 0 or empty with a warning unless `Stats.MemoryTrackingEnabled` is true.
- `GetHarmonyQualityLevel()` is "Internal-only… not callable from ordinary scripts".

**MicroProfiler and other profilers**
- The MicroProfiler focuses "entirely on frame time". The doc's example: "if 59 frames arrive in 10 milliseconds and one frame in 410 milliseconds, players perceive a huge, jarring stutter, even though the game is running at 60 FPS". **Orange bars** mean worker-thread jobs (scripts, physics, animation) took longer than the render thread, and **blue bars** mean render-bound frames. It opens with Ctrl+F6 in Studio and the desktop client — [creator-docs MicroProfiler](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/microprofiler/index.md)
- Saving dumps: "use the **Dump** menu… automatically saves the file to the Roblox logs directory: On Windows, check `%LOCALAPPDATA%\Roblox\logs`" as `microprofile-<date>-<time>.html`. Dumps contain only the selected frame count, except in counters mode. Server dumps can be captured from the Developer Console — [creator-docs MicroProfiler](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/microprofiler/index.md); [search summary of the same page](https://create.roblox.com/docs/performance-optimization/microprofiler)
- The Developer Console (Ctrl+F9) offers:
  - a client/server Log
  - a server command bar with in-game security restrictions
  - Memory by category and **Luau heap snapshots**
  - Network (HTTP and DataStore calls)
  - **Script Profiler**, which records the CPU time of running scripts
  - Source: [creator-docs developer-console.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/studio/developer-console.md)
- Chrrxs fork: `capture_script_profiler`, `capture_micro_profiler`, `get_memory_breakdown` and `get_scene_analysis` — [Chrrxs README](https://github.com/Chrrxs/robloxstudio-mcp). There is an open issue about repeated `capture_script_profiler` timeouts — [issue #94](https://github.com/Chrrxs/robloxstudio-mcp/issues/94)
- When Studio is launched from the CLI it "pipes verbose logs to `stdout` that are more detailed than what appears in the Output window", and `--outputFile` captures them — [creator-docs studio/command-line-interface.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/studio/command-line-interface.md)

### Inferences
**Per-scene performance probe.** Have Claude keep a reusable "perf probe" ModuleScript. During a playtest, run it via `execute_luau` with `datamodel_type="Client"`, or Chrrxs `eval_client_runtime`. It should sample `Stats.FrameTime` every frame for N seconds and return:
- average, p95 and p99 frame time, and the worst frame (stutter detection matters more than average FPS)
- `RenderCPUFrameTime` vs `RenderGPUFrameTime` (CPU- or GPU-bound)
- scene, shadow and UI draw calls and triangles
- memory by category

The user's 35–38 FPS scene and the micro-stutters can then be tracked as numbers across commits. Pair this with MicroProfiler dumps: Claude can read the HTML from `%LOCALAPPDATA%\Roblox\logs` to find spike tags.

**Visual checks are DIY.** Script deterministic camera positions through `screen_capture`'s camera parameters, save the images (Claude Code already saves originals), and compare against approved baselines, either with Claude's own vision or with a pixel-diff script.
- Z-fighting flicker is temporal, so capture several frames or small camera offsets. A single still may miss it.
- Because of the Windows play-mode `screen_capture` bug, Edit-mode captures at fixed cameras are the reliable baseline. Use the OS-level PowerShell capture of the Studio window as a fallback during play.

### Gaps
- No official Roblox tool for automated visual regression testing was found.
- It is undocumented whether `Stats` render properties (draw calls, GPU time) return meaningful values inside Studio playtests versus the real client, and whether they update when Studio's viewport isn't focused.
- The MicroProfiler HTML dump format is not documented for machine parsing.

## Q6. Keeping Claude on correct, current Roblox APIs (creator-docs repo, API dump JSON, docs MCP servers, Context7, llms.txt; avoiding deprecated APIs)

### Takeaway
Several current, machine-readable sources exist:
- Roblox's own `llms.txt` indexes (docs, Engine API and Cloud API)
- the open-source **Roblox/creator-docs** repo, where each class is a YAML file with `Deprecated` tags and deprecation messages
- the built-in MCP's `http_get` (Roblox docs only) and `skill` tools
- Studio's own `--api`, `--fullApi` and `--apiV2` dumps, plus the community Roblox-Client-Tracker
- luau-lsp's auto-updated type definitions and selene's auto-regenerated Roblox std, which catch hallucinated APIs at check time

Context7 has no confirmed Roblox-specific library. A Roblox-docs MCP and several community skills exist but are unofficial.

### Cited Findings
- The docs index is at `https://create.roblox.com/docs/llms.txt`, with additional indexes at `/docs/reference/engine/llms.txt` (Engine API) and `/docs/cloud/llms.txt` (Cloud API) — [WebSearch summary of create.roblox.com/docs](https://create.roblox.com/docs). This could not be fetched directly through the proxy. Docs pages are also served as Markdown, for example `.../docs/en-us/studio/command-line-interface.md` — [search result URL](https://create.roblox.com/docs/en-us/studio/command-line-interface.md)
- **creator-docs on GitHub** holds per-class API reference YAML with deprecation metadata. Example: `Stats.HeartbeatTimeMs` is tagged `Deprecated` with "Use `Class.Stats.HeartbeatTime` instead". Access is open via raw.githubusercontent.com — [Stats.yaml](https://github.com/Roblox/creator-docs/blob/main/content/en-us/reference/engine/classes/Stats.yaml)
- In the built-in MCP, `http_get` "Fetches content from allowed Roblox documentation URLs (Engine API reference, Creator docs, Cloud API, performance optimization guides)", and `skill` "Retrieves detailed knowledge, best practices, or reference material" — [studio/mcp.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/studio/mcp.md)
- Chrrxs fork: `get_roblox_docs` returns official engine API docs as Markdown, and `get_roblox_skills` returns Roblox-authored skills. `robloxdocs://` resource templates are also available — [Chrrxs README](https://github.com/Chrrxs/robloxstudio-mcp); [token-efficiency doc](https://github.com/Chrrxs/robloxstudio-mcp/blob/main/docs/token-efficiency.md)
- **API dumps from Studio itself (official):** `RobloxStudio.exe --api out.json` (the Luau scripting API), `--fullApi`, and `--apiV2` (the V2 schema) — [creator-docs studio/command-line-interface.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/studio/command-line-interface.md)
- **Roblox-Client-Tracker** (unofficial, by MaximumADHD) is datamined from Studio builds. It publishes `API-Dump.json`, `Full-API-Dump.json` (with defaults), `LuauTypes.d.luau` and `FVariables.txt` (fast flags) — [Roblox-Client-Tracker README](https://github.com/MaximumADHD/Roblox-Client-Tracker)
- Type-level guardrails: luau-lsp serves current Roblox definitions per security level at luau-lsp.pages.dev ([CHANGELOG](https://github.com/JohnnyMorganz/luau-lsp/blob/main/CHANGELOG.md)). selene's Roblox std auto-regenerates every 6 hours ([selene Roblox guide](https://github.com/Kampfkarren/selene/blob/main/docs/src/roblox.md))
- **Docs MCP servers:**
  - `mcp-roblox-docs` (run with `uvx mcp-roblox-docs`) has 27 tools: "850+ classes, 35,000+ members, 14,000+ FastFlags, 865 Cloud API endpoints", Luau docs and DevForum search. It is community-made and needs no key — [n4tivex/mcp-roblox-docs README](https://github.com/n4tivex/mcp-roblox-docs); [PyPI](https://pypi.org/project/mcp-roblox-docs/)
  - A Roblox DevForum plus creator-docs MCP by el4cteo is listed — [mcpservers.org](https://mcpservers.org/servers/el4cteo/roblox-devforum-mcp)
  - Context7 is a general docs MCP, and no Roblox-specific Context7 library was confirmed — [Stacklok Context7 guide](https://docs.stacklok.com/toolhive/guides-mcp/context7)
- **Community agent skills** in SKILL.md format, all unofficial:
  - `MSayib/roblox-dev-skill` is "Version-stamped against a specific Studio/Luau release" and covers "how to drive Studio's built-in MCP server safely".
  - `afrxo/roblox-agent-skills` exists "because Claude knows Lua but doesn't reliably know Roblox".
  - `AshExplained/roblox-skills` has 34 skills.
  - Sources: [MSayib](https://github.com/MSayib/roblox-dev-skill); [afrxo](https://github.com/afrxo/roblox-agent-skills); [AshExplained](https://github.com/AshExplained/roblox-skills/blob/main/README.md)

### Inferences
**Layered strategy for the user's SKILL.md playbook:**
1. Tell Claude to check any unfamiliar API against the creator-docs YAML or `llms.txt` (via WebFetch, or `http_get` through MCP), and to grep for `Deprecated` before using a member.
2. Optionally vendor a shallow clone of `Roblox/creator-docs` (`content/en-us/reference/engine`) or a fresh `--apiV2` dump into the repo, refreshed monthly. That makes the check offline and fast.
3. Rely on `luau-lsp analyze` and selene to catch nonexistent members mechanically.
4. Note known deprecations in the skill, for example `HeartbeatTimeMs` → `HeartbeatTime`, and the removed MCP `set_active_studio` → `studio_id`.

Community skills can be mined for ideas, but they should not replace the user's own playbook, given unknown quality and version drift.

### Gaps
- Could not verify the exact contents and refresh cadence of Roblox's `llms.txt` files (create.roblox.com blocked).
- No Roblox-specific Context7 entry was confirmed.
- No source documents whether creator-docs YAML or `--apiV2` mark "superseded but not deprecated" patterns (for example, preferred newer APIs), so deprecation checks catch only formally tagged members.

## Objective synthesis: recommended tool combination for a solo developer seeking maximum quality (Windows, Claude Code Pro, currently Studio-only)

### Takeaway
Recommended stack, in order of setup. Steps 1–3 are Roblox's own "coding harness" pattern; steps 4–7 are Claude-runnable quality gates and measurement:
1. Official built-in Studio MCP, connected via Quick Connect or `.mcp.json` with a long `timeout`.
2. Script Sync for all script folders, plus Git, with separate place backups for the hand-built world.
3. A Rokit-pinned local quality gate: StyLua `--check`, selene, `luau-lsp analyze`.
4. Jest Roblox tests run headless through `jest-roblox-cli --backend studio-cli --formatters agent`.
5. A Stats-based perf probe plus MicroProfiler dumps, with `screen_capture` at fixed cameras for visual checks.
6. Roblox's llms.txt and creator-docs as the API source of truth, encoded in the user's SKILL.md.
7. Optional: the Chrrxs community MCP (or its read-only Inspector edition) for profiler and scene-cost capture, and OCALE CI on a test place once the project is on GitHub.

### Cited Findings
- Roblox's official harness is Script Sync, the built-in MCP and Git, with Claude Code named as a supported editor agent — [creator-docs ai/coding-harness.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/ai/coding-harness.md)
- Roblox recommends the built-in MCP over the Rust server — [Rust server README](https://github.com/Roblox/studio-rust-mcp-server); [DevForum built-in announcement](https://devforum.roblox.com/t/assistant-updates-studio-built-in-mcp-server-and-playtest-automation/4474643)
- Roblox's own docs recommend luau-lsp with the Companion plugin, selene and StyLua alongside Script Sync — [scripting/sync.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/scripting/sync.md)
- Roblox's CI demo pipeline is selene, then StyLua, then a Rojo build, then OCALE tests, then deploy, using a separate test place — [place-ci-cd-demo](https://github.com/Roblox/place-ci-cd-demo)
- jest-roblox-cli's studio-cli backend gives headless local engine tests with an agent-oriented formatter — [jest-roblox-cli README](https://github.com/christopher-buss/jest-roblox-cli)
- The playtest subagent offloads gameplay testing to a Roblox-run model, so it doesn't consume the user's tokens — [DevForum Playtest Agent beta](https://devforum.roblox.com/t/studio-beta-studio-assistant-mcp-playtest-agent/4566767)

### Inferences
**Order of adoption.** Each step is reversible, and "no lock-in" is an explicit Roblox doc claim — [external-tools.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/projects/external-tools.md).
- **Week 1:** Enable Script Sync and git-commit all scripts. Reconnect the built-in MCP via Quick Connect. Add a `.mcp.json` `timeout` and raise `MAX_MCP_OUTPUT_TOKENS`.
- **Week 2:** Add Rokit with stylua, selene and luau-lsp. Add Claude Code hooks that run the checks on edited `.luau` files.
- **Week 3:** Add Jest Roblox for pure logic first: combat math, state machines, cutscene sequencing data. Then add the perf probe and baseline captures.

**Why not Rojo first.** The user's main content is a hand-built world and cinematic cutscenes, which are instances rather than code. A fully managed Rojo conversion is the most disruptive change and gains the least here. Revisit it when the combat system's UI and configuration need file-level versioning.

**Avoid duplicate write paths.** Don't run two write-capable Studio MCP servers at once. If the Chrrxs fork is added, prefer its Inspector edition, or use it only for profiling sessions.

**Pro-plan budget.** Pro limits favour Claude's file tools, which cost little context, over MCP script reads. Delegate gameplay QA to Roblox's playtest subagent and keep perf probes returning compact JSON.

### Gaps
- No published case study or benchmark compares end-to-end AI build quality across these stacks. The recommendation is a synthesis of official guidance and tool capabilities, not measured outcomes.
- The cited Windows-specific bugs may already be fixed in the October 2026 Studio build. This could not be verified, so the user should re-test after updating Studio.
