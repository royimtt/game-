# Top-Tier Roblox Combat Systems: Architecture, Hit Detection, Netcode, Security and Combat Feel (state as of October 1, 2026)

Source conventions: Roblox engine facts are cited from the official `Roblox/creator-docs` repository on GitHub (the source of create.roblox.com; read directly via raw.githubusercontent.com in this session). Library facts are cited from each library's own README where possible. DevForum, Reddit, YouTube and GDC Vault were not directly reachable, so claims from those are taken from web-search result summaries and labelled "(via search summary)". Sources that look like secondary/SEO/AI-generated blogs are labelled "(secondary blog, treat as indicative)".

---

## 1. Architecture of top Roblox combat games: authority, prediction, lag compensation, combat state, abilities, stun/ragdoll/knockback, M1/block/parry/i-frames

### Takeaway
In October 2026 there are two workable netcode blueprints for a serious Roblox combat game. (a) The battlegrounds-style hybrid: the attacker's client detects hits so they match what the player sees. The server validates them (state, cooldown, distance and angle, ideally a rewind of the target's past position) and owns all damage, stun and cooldown state. (b) Roblox's native **Server Authority** model (fully released July 2026). The server owns everything, clients predict via `RunService:BindToSimulation` at a fixed 60 Hz, mispredictions are rolled back, inputs go through `InputAction`s, and synced state lives in attributes. Either way, combat state such as stun, i-frames, parry windows and cooldowns must be a server-owned state machine. Knockback and ragdoll must be designed around network ownership.

### Cited Findings

#### The hybrid "client detects, server validates" model (battlegrounds genre)
- The DevForum consensus for battlegrounds-style melee is client-side hitboxes, because server-side boxes are visibly offset for the attacker. The server runs sanity checks (e.g., magnitude/distance) and always applies damage. Purely client-side hitboxes can be resized, moved or rewritten by exploiters. — [DevForum: Client-Sided or Server-sided Hitbox for this combat?](https://devforum.roblox.com/t/client-sided-hitbox-or-server-sided-hitbox-for-this-combat/2910826); [DevForum: Combat Hitbox Server or Client?](https://devforum.roblox.com/t/combat-hitbox-server-or-client/4535993); [DevForum: Hitbox System Battlegrounds](https://devforum.roblox.com/t/hitbox-system-battlegrounds/3194134) (via search summary)
- Posters quantify the server-hitbox offset. At default WalkSpeed with 50 ms latency the box is ~0.8 studs off (16 studs/s × 0.05 s). At 100 ms, ~4 studs is reported in battlegrounds movement. The 4-stud figure implies faster-than-default movement or interpolation delay, so treat it as anecdotal. — [DevForum: Client-Sided or Server-sided Hitbox…](https://devforum.roblox.com/t/client-sided-hitbox-or-server-sided-hitbox-for-this-combat/2910826) (via search summary)
- A commonly described battlegrounds flow works like this. On attack, the client builds a box in front of the character and detects hits immediately. If anything is hit, it sends the hitbox CFrame plus the hit array to the server. The server validates the magnitudes between the attacker, the reported hitbox CFrame and each hit target. — [DevForum: Creating a Battlegrounds-like Hitbox](https://devforum.roblox.com/t/creating-a-battlegrounds-like-hitbox/3623640); [DevForum: How to make client side hitbox for combat game](https://devforum.roblox.com/t/how-to-make-client-side-hitbox-for-combat-game/2672420) (via search summary)
- Roblox's own Parallel Luau guide describes this pattern for "a fighting and battle game". The client simulates weapons "to achieve good latency", and the server confirms hits with raycasts and heuristics on expected character velocity and past behavior. It suggests one `Actor` and one remote event per character, validation inside a parallel connection, and `task.synchronize()` before damage is applied. — [creator-docs: scripting/multithreading.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/scripting/multithreading.md)
- A secondary guide states that "pure client authority is exploitable in minutes, and pure server authority feels broken above 100 ms ping". It describes the shipped pattern as the client proposing a hit and the server confirming it against a rewound snapshot. — [simplified.media: Roblox Combat Systems](https://simplified.media/guides/roblox-combat-systems) (secondary blog, treat as indicative)
- Pre-2026 community answer to full authority: **Chickynoid**, a "server-authoritative networking character controller". It provides client-side movement prediction with rollbacks, rayscan/projectile weapons with server-side hit detection and lag compensation, and custom collision. It trusts nothing from the client "except input directions and buttons (and to a limited degree dt)". Drawbacks: it replaces Humanoids, the character is a fixed-size box, and it cannot push or ride physics parts. — [Chickynoid README](https://raw.githubusercontent.com/easy-games/chickynoid/main/README.md)

#### Roblox native Server Authority (prediction + rollback), generally available since July 2026
- Definition: the server is the single source of truth and "clients are only trusted to report their own inputs". The client predicts a few frames ahead of the last known server state, then rolls back and resimulates on misprediction. The docs' own example is combat-relevant: the client predicts you moved forward, but on the server "another player used a stun ability that stopped you from moving." — [creator-docs: projects/server-authority/index.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/projects/server-authority/index.md)
- Setup: setting `Workspace.AuthorityMode = Server` also turns on five settings: `NextGenerationReplication`, `PlayerScriptsUseInputActionSystem`, `SignalBehavior = Deferred`, `UseFixedSimulation` and `StreamingEnabled`. — [server-authority/index.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/projects/server-authority/index.md)
- The `Enum.AuthorityMode` values are `Server` ("server authority with client side prediction and rollback enabled") and `Automatic` (the traditional distributed model, where `SetNetworkOwner` influences who simulates). — [creator-docs: enums/AuthorityMode.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/enums/AuthorityMode.yaml)
- Characters and gameplay-critical objects can stay server-owned "without incurring the input latency cost". Instances with simulation access near the local character are predicted automatically, and `RunService:SetPredictionMode()` (client only) forces prediction on or off. — [server-authority/index.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/projects/server-authority/index.md); [creator-docs: RunService.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/RunService.yaml)
- Core logic must live in functions bound via `RunService:BindToSimulation()`, inside a ModuleScript initialized on both client and server; these are re-run during resimulation. `BindToSimulation` requires `Workspace.UseFixedSimulation`. It errors if the callback touches properties or methods without "Simulation Access". Use `time()`, which is synchronized and rewinds in resimulation, rather than `tick()`, `os.time()` or `os.clock()`. — [server-authority/index.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/projects/server-authority/index.md); [RunService.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/RunService.yaml); [Workspace.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/Workspace.yaml)
- Custom synced state, such as health, ammo and inventory, goes in **attributes** on predicted instances. Any attribute mismatch triggers a full rollback. Write those attributes only inside `BindToSimulation`. Replication limits: an attribute must be among the first 64 on its instance, have a name of at most 50 characters, and string values of at most 50 characters. — [server-authority/index.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/projects/server-authority/index.md)
- All inputs that affect the core simulation must use the Input Action System (`InputAction`/`InputContext`, with contexts parented under the `Player`). These inputs are replayed during resimulation and should be sanity-checked. The docs say not to use `UserInputService.InputBegan` in the core simulation. RemoteEvents are still allowed for discrete messages, but they "might not be consistently ordered with property and attribute updates." — [server-authority/index.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/projects/server-authority/index.md)
- Animations, sounds and VFX should be driven from a separate `RenderStepped` function that reads simulation state. They must be "undoable" when a prediction turns out wrong; the docs give a grenade state-machine example. Cached `AnimationTrack`s break under rollback ("avoid track caching"). Instance "stitching" lets a client predictively create instances (e.g., projectiles) inside `BindToSimulation`. A deterministic GUID built from type, source, frame and a per-script counter then merges them with the server copy. — [creator-docs: server-authority/techniques.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/projects/server-authority/techniques.md)
- Design guidance from the same page:
  - Slower acceleration hides latency better.
  - A delayed effect (a "fuse") produces fewer visible artifacts than an instant explosion on input.
  - Other players' inputs are not forwarded by default, so other characters "render slightly in the past" rather than mispredicting.
  - Position smoothing: render a visual-only clone tracking the simulated part with `TweenService:SmoothDamp` (sample `smoothTime = 0.07`).
  
  Source: [techniques.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/projects/server-authority/techniques.md)
- Engineering numbers from Roblox staff:
  - The fixed simulation runs at 60 Hz (16.67 ms per frame); 100 ms of latency is about 6 frames of client lead.
  - A misprediction at 100 ms latency means resimulating the full 100 ms, "6.25x the simulation load" of a client-authoritative game.
  - Players within one US-sized country can comfortably have about two delay frames.
  
  Source: [DevForum: Server Authority – Tech Deep Dive + Engineering Insights](https://devforum.roblox.com/t/server-authority-tech-deep-dive-engineering-insights/4624565) (via search summary)
- Timeline:
  - Studio Beta: [DevForum Studio Beta](https://devforum.roblox.com/t/studio-beta-build-fair-responsive-games-with-server-authority/4139157).
  - A March 2026 update expected general release "in the next 1–2 months": [DevForum: Server Authority Studio Beta Updates](https://devforum.roblox.com/t/server-authority-studio-beta-updates/4503827) (via search summary).
  - Client Beta, which allowed publishing: [DevForum Client Beta](https://devforum.roblox.com/t/client-beta-publish-test-your-server-authoritative-experiences/4606949).
  - Full release: [DevForum Full Release](https://devforum.roblox.com/t/full-release-ship-fair-and-competitive-games-with-server-authority/4727993).
  - Roblox's X post "Server Authority is now available for all creators" is dated 2026-07-09 (decoded from the post's snowflake ID): [Roblox on X](https://x.com/Roblox/status/2075267517111582783).
  - Roblox newsroom article: [Roblox newsroom, July 2026](https://about.roblox.com/newsroom/2026/07/creating-responsive-cheat-resistant-games-roblox-server-authority).
- **Conflict:** the creator-docs security page still says "Server authority is currently in beta and will be released soon." That page appears stale relative to the July 2026 full-release announcements. — [creator-docs: scripting/security/network-ownership.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/scripting/security/network-ownership.md) vs [Roblox on X](https://x.com/Roblox/status/2075267517111582783)
- Reported limitations and bugs around the release:
  - Animations do not re-play during correction or resimulation, which can cause further mispredictions when avatars collide with animated parts.
  - The 64-attribute cap with short strings.
  - The default PlayerModule forces `Humanoid.AutoRotate` each simulation step.
  - A crash bug with `Humanoid:ApplyDescriptionAsync()`.
  - A bug report that mispredictions scale with client FPS under high latency.
  
  Sources: [DevForum Full Release](https://devforum.roblox.com/t/full-release-ship-fair-and-competitive-games-with-server-authority/4727993); [PlayerModule bug](https://devforum.roblox.com/t/unable-to-modify-the-playermodule-when-server-authority-is-enabled/4698731); [ApplyDescriptionAsync crash](https://devforum.roblox.com/t/humanoidapplydescriptionasync-can-crash-when-server-authority-is-enabled/4710116); [mispredictions scale with FPS](https://devforum.roblox.com/t/server-authority-mispredictions-scale-with-client-fps-under-high-latency/4739385); [Client Beta "was a damn nightmare" advice thread](https://devforum.roblox.com/t/server-authority-client-beta-was-a-damn-nightmare-heres-some-advice/4712758) (via search summary)
- A developer testimonial cited in Roblox's release coverage: "The real-time combat system would be dead in the water without Server Authority" (ThoughtSpinnr's space game). — [Roblox newsroom](https://about.roblox.com/newsroom/2026/07/creating-responsive-cheat-resistant-games-roblox-server-authority) / [DevForum Full Release](https://devforum.roblox.com/t/full-release-ship-fair-and-competitive-games-with-server-authority/4727993) (via search summary; exact page holding the quote not verified)
- Official templates: Racing, Soccer and Laser Tag. There is no melee or fighting template. — [server-authority/index.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/projects/server-authority/index.md)

#### Lag compensation (rewind) for hit validation
- **RollbackHitbox** (open source, Wally `michaelvqq/rollbackhitbox@0.1.0`):
  - Every server Heartbeat (~60 Hz) it writes each character's hitbox CFrames into a circular buffer.
  - On a hit claim it computes `rewind = clamp(serverNow − clientTimestamp + buffer, 0, maxRewind)`. It then binary-searches and lerps the buffer for sub-frame accuracy, and tests ray-vs-OBB without moving parts or running physics.
  - Defaults: `MAX_REWIND_SECONDS = 0.5`; `INTERPOLATION_BUFFER = 0.1` s ("to compensate for Roblox's ~20 Hz character replication delay"); `MAX_ORIGIN_DISTANCE = 12` studs; `MAX_PLAYER_SPEED = 60` studs/s (scales origin tolerance with latency); `BUFFER_CAPACITY = 24` snapshots (~400 ms at 60 Hz).
  - The client timestamp comes from `workspace:GetServerTimeNow()`.
  
  Source: [RollbackHitbox README](https://raw.githubusercontent.com/michaelvqq/RollbackHitbox/main/README.md)
- Rewinding the target is also valid for melee. The lag-compensated position "would always be pretty close to where the player actually was… so it would always work for large hitbox detections, such as close combat punches". — [DevForum: RollbackHitbox thread](https://devforum.roblox.com/t/rollbackhitbox-server-authoritative-lag-compensation-for-roblox-shooters-open-source/4553295) (via search summary)
- Classic definition ("favor the shooter"): keep hitbox history and backtrack by half the shooter's ping when a shot is made. — [roblox-lag-compensation README](https://raw.githubusercontent.com/RegularTetragon/roblox-lag-compensation/master/README.md)
- A secondary guide suggests a ~1 s ring buffer (≈60 entries at 60 Hz), evaluating the target at attackerTime − ping/2. It also suggests rejecting timestamps from the future or older than the buffer. — [creation.dev: lag compensation](https://www.creation.dev/learn/how-to-implement-lag-compensation-roblox-shooters) (secondary blog, treat as indicative)
- Other libraries:
  - "Rewind – Server-Authoritative Hit Validation & Custom Character Replication" (v1.2.0). The same thread ID also appears in the search index titled "[Archived]", so its maintenance status is uncertain: [DevForum: Rewind v1.2.0](https://devforum.roblox.com/t/rewind-server-authoritative-lag-compensated-hit-validation/4160622); [archived title](https://devforum.roblox.com/t/archived-rewind-server-authoritative-hit-validation-custom-character-replication/4160622).
  - SecureCast (server-authoritative projectiles with lag compensation) is marked archived: [DevForum: SecureCast (Archived)](https://devforum.roblox.com/t/archived-securecast-server-authoritative-projectiles-with-lag-compensation-multi-threading-and-more/2546164).

#### Replication delay and ping facts
- `Player:GetNetworkPing()` returns round-trip latency in seconds, excluding deserialization and processing. The docs suggest using it to mask latency, e.g., by adjusting throw-animation speed. — [creator-docs: Player.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/Player.yaml)
- `Workspace:GetServerTimeNow()` is the client's best approximation of server Unix time. It is monotonic and moves at the local clock rate "to within 0.6%". — [creator-docs: Workspace.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/Workspace.yaml)
- Chrono's README says Roblox replicates physics at 20 Hz by default and that all characters get "a large, non-configurable interpolation delay designed primarily for mobile devices". Chrono bypasses this by forwarding CFrames with a configurable dynamic interpolation delay. It exposes historical snapshots and the interpolation delay "for far more accurate lag compensation". — [Chrono README](https://raw.githubusercontent.com/Parihsz/Chrono/master/README.md)
- The default character interpolation buffer is dynamic (it varies with network, device, FPS, camera distance and physics settings) and is not exposed by any API. — [DevForum: Character Replication Delay Duration](https://devforum.roblox.com/t/character-replication-delay-duration/3215748); [DevForum: Character Interpolation Period](https://devforum.roblox.com/t/character-interpolation-period/1523855) (via search summary)

#### Combat state machines, stun, M1 combos, block/parry/posture, i-frames
- Community combat state machines use priority-based transitions between Attack, Block, Perfect Block and Stun. — [DevForum: Combat State Machine for Block / Attack / Stun](https://devforum.roblox.com/t/combat-state-machine-for-block-attack-stun-system/4660683) (via search summary)
- Stun design debate: separate stun states (GuardBroken, PerfectBlockStunned, AttackStunned) versus one Stunned state plus a `StunReason` attribute. A related point is comparing stun end times so that a shorter stun cannot override a longer one. — [DevForum: Multiple Stun States vs Stun Reason Attribute](https://devforum.roblox.com/t/state-machine-design-multiple-stun-states-vs-stun-reason-attribute/4256628) (via search summary)
- A legacy pattern (seen in older threads) parents named BoolValues (Stun/Block/Sprint) to the character and listens with `ChildAdded` to change WalkSpeed. — [DevForum: Best way to create a stun system](https://devforum.roblox.com/t/best-way-to-create-a-stun-system-for-a-combat-system/2881646) (via search summary)
- An illustrative recipe:
  - A 4-hit M1 chain at 8 damage, with a 14-damage finisher that knocks back.
  - Heavy attack, block, parry, a dash with i-frames, and stamina.
  - A `GetPartBoundsInBox` hitbox.
  - A `CombatServer` that owns combo, cooldowns, stamina and hitbox queries.
  
  Source: [picoo.io: How to make a Roblox combat system](https://picoo.io/how-to-make/roblox-combat-system) (AI-prompt site; numbers are examples, not a standard)
- Deepwoken, the reference Roblox "parry" game:
  - Parry (F) opens a deflection window. Attacks landing in it are parried, which stuns the attacker and deals posture damage to them, while also reducing your own posture.
  - Holding F after the window becomes a block. A block negates damage (except chip) but fills your posture bar.
  - Posture damage depends on weapon weight. A full bar means a "block break": stun plus bonus damage taken.
  - Posture regenerates when not sprinting or blocking, and through parries and some talents.
  
  Source: [Deepwoken Wiki: Combat Mechanics](https://deepwoken.fandom.com/wiki/Combat_Mechanics) (via search summary)

#### Knockback, ragdoll and network ownership
- `BasePart:ApplyImpulse` rules:
  - If the part is server-owned, it must be called from a server Script.
  - If it is client-owned through automatic ownership, it may be called from either side.
  - Calling it from a client on a server-owned part "will have no effect".
  
  Source: [creator-docs: BasePart.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/BasePart.yaml)
- Ownership basics:
  - The server always owns anchored parts.
  - Unanchored parts are auto-assigned to nearby clients based on proximity and hardware.
  - `SetNetworkOwner(nil)` hands a part to the server, and `SetNetworkOwnershipAuto()` restores automatic assignment.
  - Anchoring then unanchoring a lone assembly loses its previous ownership state.
  
  Sources: [creator-docs: physics/network-ownership.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/physics/network-ownership.md); [BasePart.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/BasePart.yaml)
- A client that owns parts, including its own character, can:
  - teleport;
  - set WalkSpeed locally without firing any events;
  - play arbitrary animations;
  - replicate `Inf`/`NaN` CFrames and velocities that fling others;
  - suppress or spoof `Touched`.
  
  For gameplay-critical unanchored parts, set ownership manually. — [creator-docs: scripting/security/network-ownership.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/scripting/security/network-ownership.md)
- Community pitfalls:
  - LinearVelocity knockback on players is laggy or inconsistent.
  - Some systems transfer the victim's ownership to the attacker for knockback. Toggling ownership per punch then broke the ragdoll applied after the combo finisher.
  - Ragdoll plus knockback looks laggy to everyone except the victim and the server.
  - Fixes tried: `SetNetworkOwner(nil)` combined with LinearVelocity, VectorForce or BodyVelocity.
  
  Sources: [DevForum: Knockbacking someone and network ownership](https://devforum.roblox.com/t/knockbacking-someone-and-network-ownership-combat-system/3174729); [DevForum: Unsolved combat network ownership problem](https://devforum.roblox.com/t/unsolved-combat-system-network-ownership-problem/3217564); [DevForum: Ragdoll Knockback Lag](https://devforum.roblox.com/t/ragdoll-knockback-lag-replication-issue/2845470); [DevForum: LinearVelocity knockback very laggy](https://devforum.roblox.com/t/linearvelocity-used-for-my-knockback-is-very-laggy/3127045) (via search summary)
- Standard ragdoll: disable the Motor6Ds and create BallSocketConstraints at the joint attachments. Ragdoll knockback that worked only on NPCs was fixed by calling `SetNetworkOwner(nil)` on the player character's parts. R15 rigs can bounce off the ground after ragdoll knockback. A free MIT R15/R6 ragdoll module exposes `applyImpulse()`. — [DevForum: Ragdoll knockback only working for NPCs](https://devforum.roblox.com/t/ragdoll-knockback-only-working-for-npcs-and-not-players/3432025); [DevForum: R15 bounces after ragdoll knockback](https://devforum.roblox.com/t/r15-bounces-off-the-ground-after-ragdoll-knockback/1244135); [DevForum: Free ragdoll module](https://devforum.roblox.com/t/free-ragdoll-have-a-discord-and-also-likes-suggestions/4636801) (via search summary)

#### Animation timing and VFX replication
- Gate damage to "active frames" with Animation Event markers (e.g., `HitStart`/`HitEnd` via `AnimationTrack:GetMarkerReachedSignal`). Markers are client-side and can be missed on the server. So have the client react to the marker and let the server validate, rather than relying on the marker server-side. — [DevForum: Help with AnimationEvents for Combat System](https://devforum.roblox.com/t/help-with-animationevents-for-combat-system/3244308); [DevForum: Issues with GetMarkerReachedSignal](https://devforum.roblox.com/t/issues-with-getmarkerreachedsignal/3071598) (via search summary)
- The VFX pattern is a shared VFX ModuleScript. The attacking client plays effects instantly; the server validates and `FireAllClients` with parameters (positions, tween info) so the other clients render the same effect. Replicate VFX, never hitboxes. `FireAllClients` does not reach players who join later. — [DevForum: Client Replication 101](https://devforum.roblox.com/t/client-replication-101-the-guide-to-replicating-effects-to-clients/1789487); [DevForum: Should my VFX scripts be on the client or server?](https://devforum.roblox.com/t/should-my-vfx-scripts-be-on-the-client-or-server/1608975) (via search summary)

### Inferences
- **Choosing the blueprint (recommendation for this solo isekai project).**
  - Server Authority is the strongest anti-cheat option: it stops speed, fly and fling exploits without custom code. But it is new (GA July 2026). It forces Deferred signals, IAS, StreamingEnabled and attribute-only synced state (≤64 attributes, ≤50-char strings). It does not yet replay animations during resimulation, which matters for animation-heavy anime melee. And it adds resimulation CPU cost.
  - The hybrid model has years of tutorials, works with standard Humanoid and animation tooling, and fits cinematic VFX-heavy kits.
  - Practical path: build the combat core as **pure, data-driven, deterministic-friendly modules**, i.e. state transitions and damage math that do not touch Instances. Prototype one race kit under Server Authority in a test place. If the animation and misprediction issues are acceptable, adopt it; otherwise ship hybrid plus server-side rewind validation.
- **Hybrid reference loop.**
  1. Client: input, then local state check, then play the animation and startup VFX immediately.
  2. During active frames, gated by markers or ability timing, run spatial queries every `Heartbeat`.
  3. Send `{abilityId, comboIndex, t = GetServerTimeNow(), targets[], hitboxCFrame}` over a reliable remote.
  4. Server: rate-limit; check that the attacker is alive, not stunned, owns the ability and is off cooldown; check that `t` falls inside the expected active window (±RTT tolerance); check distance and angle; rewind targets to `t − interpDelay`; raycast line of sight; resolve block, parry or i-frames on the victim at that time; apply damage, posture, stun and knockback; broadcast the result for VFX.
  5. Clients play hit VFX, hitstop and camera shake.
- **Combat state should be server-owned data, not booleans.** Keep, per character, `State` (Idle/Startup/Active/Recovery/Blocking/Parry/Stunned/Ragdoll/Dashing/Casting/Dead), `StateUntil`, `StunUntil`, `IFrameUntil`, `ParryUntil`, `Posture`, `ComboIndex` and `ComboResetAt`, all as server timestamps. Replicate a compact subset (attributes, or a state-replication library) for client UI and prediction. "Longest stun wins": compare end times instead of overwriting.
- **Ability framework.** Use one ModuleScript table per ability, shared in ReplicatedStorage, holding: `startup/active/recovery` (seconds or 60 Hz frames); `cooldown`; `hitbox` (shape, size, offset, sweep or overlap); `damage`; `postureDamage`; `hitstun`; `blockstun`; `knockback` (vector and type); `cancelInto[]` with windows; `iFrames`; `canBeParried`; `vfxId`/`sfxId`/`animId`. The server interprets the table, so the client never sends damage numbers. This also makes the six races data variations of one engine.
- **Knockback strategy.**
  - Under the default authority model, the victim's client owns its character. Two options:
    - Apply knockback on the victim's own client (server tells the victim via remote; the client applies `ApplyImpulse`/`LinearVelocity`). This is smooth for the victim, and others see it after replication.
    - Temporarily `SetNetworkOwner(nil)` the victim during heavy launches or ragdolls, then restore auto ownership. This is authoritative but laggier for the victim.
  - Never give the attacker ownership of the victim.
  - Under Server Authority, characters stay server-owned and knockback goes inside `BindToSimulation`.

### Gaps
- No primary or official technical write-ups were found from the developers of The Strongest Battlegrounds, Jujutsu Shenanigans, Deepwoken, Type Soul or Blox Fruits. Claims about "what big games use" come from community speculation on DevForum and secondary blogs. A DevForum thread asking specifically what TSB/JJS use exists, but its contents could not be read: [DevForum](https://devforum.roblox.com/t/what-is-the-hit-detection-that-the-strongest-battlegrounds-jujutsu-shinenigans-use/3019423).
- The exact Studio-Beta start date of Server Authority, and whether the July 2026 full release fixed animation resimulation, could not be confirmed.
- No sourced numbers were found for parry or i-frame windows in popular Roblox games (e.g., Deepwoken's parry window in ms).

---

## 2. Hit detection options and trade-offs (raycast modules, shapecasts, spatial queries, magnitude/angle checks, community modules)

### Takeaway
Use engine spatial queries rather than `Touched`. Sweeps (`Blockcast`/`Spherecast`/`Shapecast`, up to 1,024 studs) catch fast-moving blades between frames but miss parts that start inside the shape. Overlaps (`GetPartBoundsInBox`/`Radius`) are cheap, AABB-approximate and the battlegrounds default. `GetPartsInPart` is exact but costlier. Pick a maintained module (ShapecastHitbox, which succeeds RaycastHitboxV4; MuchachoHitbox; ClientCast) for the client side. Exploit resistance comes only from server-side validation: distance and angle checks, timestamped rewind (e.g., RollbackHitbox), and state and cooldown checks.

### Cited Findings

#### Engine primitives
- `WorldRoot:Raycast` direction vectors are limited to 15,000 studs. — [creator-docs: WorldRoot.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/WorldRoot.yaml)
- `Blockcast`, `Spherecast` and `Shapecast` sweep a shape along a direction and return the first hit (`RaycastResult` with Distance and Position). Their max distance is 1,024 studs. Unlike `GetPartsInPart`, they do **not** detect parts that **initially** intersect the shape. `Shapecast` casts the actual geometry of a given BasePart instead of a simple box or sphere. — [WorldRoot.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/WorldRoot.yaml)
- `GetPartBoundsInBox` and `GetPartBoundsInRadius` test parts' **bounding boxes**: efficient, but inaccurate for spheres, cylinders, unions and MeshParts. `GetPartsInPart` does a full geometric check: more accurate, slower, and "generally a better choice" than `GetTouchingParts()`. — [WorldRoot.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/WorldRoot.yaml)
- `OverlapParams` defaults to `MaxParts=0, Tolerance=0, BruteForceAllSlow=false, RespectCanCollide=false, CollisionGroup=Default, FilterDescendantsInstances={}`, and it has `AddToFilter`. Queries respect `CanQuery` unless `RespectCanCollide` is set. — [creator-docs: OverlapParams.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/datatypes/OverlapParams.yaml); [WorldRoot.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/WorldRoot.yaml)
- Legacy `FindPartsInRegion3*` and `FindPartOnRay*` still appear in WorldRoot. The docs point Region3 users to `GetPartBoundsInBox()` with `OverlapParams`. — [WorldRoot.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/WorldRoot.yaml)
- Exploiters can trigger client-initiated events such as `Touched` "at any range or frequency" and can manipulate or suppress `Touched` on parts they own. — [creator-docs: security-tactics.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/scripting/security/security-tactics.md); [security/network-ownership.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/scripting/security/network-ownership.md)
- Server-side hit validation can run in parallel with one Actor per character. `Workspace:Raycast` can run in the parallel phase, while damage (a property write) needs `task.synchronize()`. — [creator-docs: multithreading.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/scripting/multithreading.md)

#### Community hitbox modules (status October 2026)
- **RaycastHitboxV4** (Swordphin): the repo README only points to the DevForum thread "Raycast Hitbox 4.01". The author now presents **ShapecastHitbox** as its successor. — [raycastHitboxRbxl README](https://raw.githubusercontent.com/Swordphin123/raycastHitboxRbxl/master/README.md); [DevForum: Raycast Hitbox 4.01 #1139](https://devforum.roblox.com/t/raycast-hitbox-401-for-all-your-melee-needs/374482/1139)
- **ShapecastHitbox** (TeamSwordphin): "A shapecast-centric solution to melee hitboxes on Roblox. Successor to RaycastHitbox". It uses Blockcast, Spherecast and Raycast with improved performance. Announced 2025-04-24 (date decoded from the X post ID); DevForum thread at v0.2.5. A companion "Shapecast Editor" Studio plugin exists. — [ShapecastHitbox README](https://raw.githubusercontent.com/TeamSwordphin/ShapecastHitbox/master/README.md); [GitHub](https://github.com/TeamSwordphin/ShapecastHitbox); [DevForum v0.2.5](https://devforum.roblox.com/t/shapecasthitbox-for-all-your-melee-needs-v025/3624241); [Swordphin on X](https://x.com/thephinRBLX/status/1915455455456907392); [Shapecast Editor plugin](https://devforum.roblox.com/t/shapecast-editor-a-shapecasthitboxraycasthitbox-plugin/3624244)
- **ClientCast**: raycasts between `DmgPoint` attachments as the part moves (no detection until it moves). `Caster:SetOwner(player)` lets that client compute collisions and notify the server, which "take[s] into account a player's ping". The trust is placed in the client, so the server must validate. — [ClientCast README](https://raw.githubusercontent.com/PysephWasntAvailable/ClientCast/main/README.md)
- **MuchachoHitbox**: a spatial-query (box/sphere `OverlapParams`) hitbox, "used by thousands of developers for over 3 years". It has velocity prediction (`VelocityPrediction = true`, example `VelocityPredictionTime = 0.2`), modes Default/HitOnce/HitParts/ConstantDetection, and TouchEnded events. The Creator Store asset was updated 2026-04-11 (via search summary). — [MuchachoHitbox README](https://raw.githubusercontent.com/CatSushi/MuchachoHitbox/main/README.md); [DevForum](https://devforum.roblox.com/t/muchachohitbox-an-easy-to-use-spatialquery-based-hitbox-system/3682320); [Creator Store](https://create.roblox.com/store/asset/9645263113/MuchachoHitbox)
- **RollbackHitbox**: server-side validation by OBB math against rewound snapshots, with no ghost parts moved. The config numbers are given in section 1. — [RollbackHitbox README](https://raw.githubusercontent.com/michaelvqq/RollbackHitbox/main/README.md)
- `GetPartBoundsInBox` is recommended for battlegrounds-type games because it is cheap. A secondary guide claims well-known PvP games call it with OverlapParams on each frame the swing is active. — [DevForum: Best ability hit detection?](https://devforum.roblox.com/t/best-ability-hit-detection/3147871) (via search summary); [simplified.media](https://simplified.media/guides/roblox-combat-systems) (secondary blog, unverified claim)

#### Exploit resistance
- A **hitbox expander** exploit enlarges other players' HumanoidRootPart or Head locally, then tells the server it hit. The prevention is to store player positions with timestamps on the server, have the client send the hit timestamp, and verify the hit was possible. — [DevForum: What is a hitbox expander? How to prevent it?](https://devforum.roblox.com/t/what-is-a-hitbox-expander-how-to-prevent-it/682634) (via search summary)
- RollbackHitbox's anti-cheat measures:
  - The rewind is clamped (a client cannot claim arbitrarily old positions).
  - The origin is validated against the shooter's rewound position, with tolerance scaled by latency and max speed.
  - It guards against "hit teleportation, timestamp manipulation, and headshot spoofing".
  
  Source: [RollbackHitbox README](https://raw.githubusercontent.com/michaelvqq/RollbackHitbox/main/README.md); [DevForum thread](https://devforum.roblox.com/t/rollbackhitbox-server-authoritative-lag-compensation-for-roblox-shooters-open-source/4553295)

### Inferences
- **Trade-off summary (synthesis):**

| Method | Accuracy | CPU cost | Typical use | Exploit resistance |
|---|---|---|---|---|
| `Touched` | Poor, physics-dependent | Low | Avoid for combat | Very low (owner can spoof) |
| Raycasts from attachments (RaycastHitboxV4/ClientCast) | Good for blades, thin swept lines | Low–medium | Weapons/swords | Only as good as server checks |
| `Blockcast`/`Spherecast` sweeps (ShapecastHitbox) | High for fast swings; misses initial overlaps | Medium | Weapons, dashes, beams | Server can re-run the same cast |
| `GetPartBoundsInBox`/`Radius` (MuchachoHitbox) | AABB approximate | Low | M1s, AoE, battlegrounds | Server can re-run on a rewound pose |
| `GetPartsInPart` | Exact | Higher | Odd-shaped AoE (rings, cones via meshes) | Same |
| Server magnitude + dot-product checks | Coarse | Very low | Always, as validation | High (server data) |
| Rewind + OBB (RollbackHitbox) | High at the attacker's view time | Low–medium | Validation layer | Highest of the hybrid options |
- **Combine sweep and overlap.** On the first active frame, do one `GetPartBoundsInBox` to catch targets already inside the box; on later frames, `Blockcast` from the previous to the current box CFrame. This covers both shapecast blind spots and frame-skipping at low client FPS.
- **Server validation checklist for each claimed target** (cheap to expensive):
  1. Remote rate limit.
  2. Attacker state and ability ownership.
  3. Server-side cooldown.
  4. Claimed `t` within the ability's active window (plus or minus RTT tolerance).
  5. Distance `|attackerRoot − targetRoot(t)| ≤ reach + size margin + speed × latency`.
  6. Facing: `attackerLook · dirToTarget ≥ cos(maxAngle)`.
  7. Optional rewound OBB or `GetPartBoundsInBox` re-check.
  8. Line-of-sight ray.
  9. Victim's defensive state at `t`: block, parry window, i-frames.
  10. Per-target hit-once-per-swing debounce.
- Hitbox size per race must be balanced against **hurtbox** size. Dragon-people or large monster rigs will be easier to hit if their HumanoidRootPart or collision box is bigger. Normalize hurtboxes (dedicated, invisible, `CanQuery` hitbox parts, as RollbackHitbox does with `HitboxBody`/`HitboxHead`) rather than querying cosmetic meshes.

### Gaps
- No independent CPU benchmarks were found comparing `Blockcast` vs `GetPartBoundsInBox` vs `GetPartsInPart` per call on current engine versions.
- ShapecastHitbox's README has no API documentation (the "Installation: To do" section is empty). Its API details live on DevForum, which was not directly readable.

---

## 3. Networking: RemoteEvent vs UnreliableRemoteEvent, buffers, networking libraries, bandwidth budgets, rate limiting, anti-exploit

### Takeaway
Use reliable `RemoteEvent`s for gameplay-critical messages: attack requests, hit claims, damage results and state changes. Use `UnreliableRemoteEvent`s only for ephemeral, frequently refreshed data such as cosmetic VFX positions, aim directions and custom character CFrames. Unreliable payloads must stay under 1,000 bytes. Both remote types share a ~500 requests/s per-client throttle per remote type. In 2026, buffer-based IDL libraries (Blink, Zap) lead benchmarks; ByteNet and Packet are simpler alternatives; BridgeNet2 is superseded. Treat every client message as hostile: validate types and semantics, rate-limit server-side, and keep cooldowns and state on the server.

### Cited Findings

#### Remote semantics and hard limits
- `RemoteEvent` and `UnreliableRemoteEvent` "both have a limit of approximately 500 requests per second, per client", and the limit is "shared among all remote events of the same type". — [creator-docs: RemoteEvent.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/RemoteEvent.yaml); [UnreliableRemoteEvent.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/UnreliableRemoteEvent.yaml)
- **Conflict:** a community claim that the client limit is "15 events or 15 calls per second" appears in search results. It is contradicted by the official ~500/s figure above. — [DevForum: What is the remote event client → server limit?](https://devforum.roblox.com/t/what-is-the-remote-event-client-server-limit/3327869) (via search summary) vs [RemoteEvent.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/RemoteEvent.yaml)
- Reliable RemoteEvents sent faster than the throttle are processed later, keeping order. With no handler connected, messages queue (with count and memory limits). RemoteFunction invocations and RemoteEvent messages have no guaranteed relative order. — [creator-docs: scripting/events/remote.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/scripting/events/remote.md)
- `UnreliableRemoteEvent`:
  - It is unordered and unreliable, with no relationship to RemoteEvent ordering.
  - Messages are dropped if the payload exceeds **1,000 bytes**, if the client exceeds the throttle (dropped rather than delayed), or if no listener is connected.
  - It is "best used for ephemeral events… or for replicating continuously changing data".
  - Buffers and some types are encoded and compressed, which "can make it difficult to verify whether you are under the limit".
  
  Sources: [UnreliableRemoteEvent.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/UnreliableRemoteEvent.yaml); [remote.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/scripting/events/remote.md)
- Argument limitations:
  - Non-string table keys (e.g., Instances) are converted to strings.
  - Mixed numeric/string-key tables should not be sent.
  - Tables are copied.
  - Metatables are lost.
  
  Source: [remote.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/scripting/events/remote.md)
- With `Workspace.NextGenerationReplication`, which Server Authority requires, "you should not rely on the ordering of property replication and remote events". — [creator-docs: Workspace.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/Workspace.yaml)
- `buffer` is a fixed-size mutable memory block (little-endian reads and writes) intended to replace `string.pack`/`unpack` for compact binary serialization. A buffer sent through remotes arrives as a copy, and one buffer cannot be shared across Actors. — [creator-docs: libraries/buffer.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/libraries/buffer.yaml)

#### Networking libraries (status and evidence)
- **Blink**: an IDL compiler that generates buffer networking code. Data sent by clients is "validated on the receiving side before reaching any critical game code". — [Blink README](https://raw.githubusercontent.com/1Axen/blink/main/README.md)
- **Blink benchmark** (maintained by Blink's author, so possibly biased). Methodology: fire the event 1,000 times per frame for 10 s. Last updated 2025-04-30. Versions: blink v0.17.1, zap v0.6.20, bytenet v0.4.3.

| Benchmark | Roblox native | Blink | Zap | ByteNet |
|---|---|---|---|---|
| "Entities" median FPS | 16 | 42 | 39 | 32 |
| "Entities" median Kbps | ≈559,364 | 41.81 | 41.71 | 41.64 |
| "Booleans" median FPS | 21 | 97 | 52 | 35 |

  Source: [Blink Benchmarks.md](https://raw.githubusercontent.com/1Axen/blink/main/benchmark/Benchmarks.md)
- **Zap**: packs data into buffers "with no overhead", and "validates all data received". Its README still says "early pre-release… API may change", even though v0.6.x is widely benchmarked. — [Zap README](https://raw.githubusercontent.com/red-blox/zap/main/README.md)
- **ByteNet**: buffer serialization with a minimal, strictly typed API, and no IDL compile step. — [ByteNet README](https://raw.githubusercontent.com/ffrostflame/ByteNet/master/README.md)
- **BridgeNet2** is superseded: its README opens with "I strongly recommend you use ByteNet over BridgeNet2". — [BridgeNet2 README](https://raw.githubusercontent.com/ffrostflame/BridgeNet2/master/README.md)
- **Red**: a single remote event with identifiers, claiming "up to 75% less bandwidth", plus data "obfuscation". — [Red README](https://raw.githubusercontent.com/red-blox/Red/main/README.md)
- **Packet** (Suphi Kaner):
  - Batches all events into one remote and serializes into a single buffer.
  - Supports 16- and 24-bit floats, has "DDoS protection", and supports unreliable remotes.
  - In community benchmarks it does not beat Blink or Zap, but beats ByteNet, NetRay and native.
  
  Source: [DevForum: Packet – Networking library](https://devforum.roblox.com/t/packet-networking-library/3573907); [#99 benchmark discussion](https://devforum.roblox.com/t/packet-networking-library/3573907/99) (via search summary)
- New in 2026 and unverified: BlinkBlox claims "6x faster server decoding than Zap/Blink" and flood protection. — [DevForum: BlinkBlox](https://devforum.roblox.com/t/blinkblox-6x-faster-server-decoding-than-zap-blink-and-exploiters-cant-flood-your-server/4898948) (via search summary)
- **Squash**: a SerDes library for hand-rolled compact serialization. — [Squash README](https://raw.githubusercontent.com/Data-Oriented-House/Squash/main/README.md)

#### Bandwidth budgets
- A community network-optimization guide gives a soft per-player limit of about **50 KB/s** (kilobytes, not kilobits). Going over it "gradually increase[s] ping" as replication queues. It recommends budgeting about **25 KB/s** for your own remotes and leaving the rest for Roblox replication. — [DevForum: Network Optimization (2021)](https://devforum.roblox.com/t/network-optimization-2021-preventing-high-latency-reducing-lag/1046078) (via search summary; 2021 community figure, not an official 2026 spec)
- The engine exposes `NetworkPeer:SetOutgoingKBPSLimit(limit)` ("maximum outgoing bandwidth (in 1,000 bits/second) that Roblox can use"). — [creator-docs: NetworkPeer.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/NetworkPeer.yaml)
- Chrono benchmark: 150 entities, Humanoid:MoveTo every 0.1 s, Chrono at 10 TPS. Measured as `Stats.DataSendKbps + PhysicsSendKbps`:

| Mode | Server send (Kbps) | Client receive (Kbps) |
|---|---|---|
| Native | 56.81 | 50.49 |
| Roblox default | 34.57 | 28.74 |
| Native with lock | 28.98 | 22.13 |
| Custom | 22.10 | 21.92 |

  The README also says Roblox can cause "10x" receive and "100x" send overhead for server-moved parts. An older DevForum summary quoted different figures for 150 NPCs (Roblox 110.29 send / 412 receive vs Chrono 3.72 / 42.97 kb/s); the current README numbers should be preferred. — [Chrono README](https://raw.githubusercontent.com/Parihsz/Chrono/master/README.md); [DevForum: Chrono](https://devforum.roblox.com/t/chrono-drop-in-custom-physics-replication-library/3873294) (via search summary)

#### Rate limiting and anti-exploit principles
- Official principles: "Never trust the client". Exploiters can:
  - decompile any replicated LocalScript or ModuleScript;
  - fire remotes "at any frequency with arbitrary arguments (besides the first Player argument)";
  - take network ownership of their character;
  - modify their position and physics;
  - alter any local code.
  
  Keep logic and data in ServerScriptService. Threat-model each feature, including "What happens if this feature is used 1,000+ times per second?". — [creator-docs: security-tactics.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/scripting/security/security-tactics.md)
- For movement validation without Server Authority:
  - Use "leaky bucket-style accumulators" for bursts.
  - Project movement onto the XZ plane to avoid flagging vertical motion.
  - Add explicit exemptions for legitimate teleports.
  - Average over time, because of latency.
  
  Source: [security/network-ownership.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/scripting/security/network-ownership.md)
- Community rate-limiting guidance:
  - Use server-side per-player timestamps, or a token bucket (N tokens refilling at a fixed rate, one consumed per call).
  - For combat actions, 0.1–0.2 s between calls is "reasonable".
  - Drop excess calls silently, without telling the exploiter.
  - Client-side cooldowns are trivially bypassed.
  
  Sources: [DevForum: Rate limiter module for Remotes](https://devforum.roblox.com/t/rate-limiter-module-for-remotes/616268) (via search summary); [kitsblox: RemoteEvents explained](https://kitsblox.com/blog/roblox-remote-events-explained) (secondary blog, treat as indicative)
- Blink and Zap validate types on receipt, and Red and Blink advertise that buffer compression or obfuscation makes traffic harder to snoop with RemoteSpy-style tools. — [Blink README](https://raw.githubusercontent.com/1Axen/blink/main/README.md); [Zap README](https://raw.githubusercontent.com/red-blox/zap/main/README.md); [Red README](https://raw.githubusercontent.com/red-blox/Red/main/README.md)
- Knit's author notes that "Luau's structural typings do not enforce the underlying data" sent over the network. Runtime checks (e.g., `assert` on incoming values) are therefore needed regardless of static types. — [Knit ARCHIVAL.md](https://raw.githubusercontent.com/Sleitnick/Knit/main/ARCHIVAL.md)

### Inferences
- **Message plan for the combat system:**
  - Reliable: `AttackRequest(abilityId, t)`, `HitClaim(abilityId, t, targetIds[], hitboxCFrame)`, `DefenseInput(block/parry/dodge, t)`, `CombatResult` (server to clients, batched per frame).
  - Unreliable: cosmetic-only `VfxCue`s (e.g., beam endpoints updated at 20–30 Hz), aim or look direction, and custom character snapshots if you adopt Chrono-style replication.
  - Keep each unreliable packet comfortably under 1,000 bytes. With buffers, quantize: positions as int16 or f16 relative to the character, angles as uint8 or uint16, IDs as uint8 or uint16.
- **Budget example (inference):** about 20 players and about 2 KB/s of combat traffic per player is far below the ~25 KB/s self-imposed budget. The bandwidth risk is VFX spam broadcast to all players and server-moved NPCs, not hit claims. Send VFX "cues" (ability ID, seed, origin, direction, server time) and let each client simulate the effect locally instead of streaming positions.
- **Server-side rate limiter:** a token bucket per player per remote (e.g., capacity 10, refill 5 per second for HitClaim; tune to your fastest legitimate M1 rate) plus per-ability cooldowns checked against server time. Silently drop or log violations. Track a "suspicion score" instead of instantly kicking, since lag spikes create false positives. Reject `NaN`/`Inf` (`x ~= x`) and out-of-range vectors on every numeric field.
- **Library choice:** for a solo developer working with Claude Code, **Blink** or **Zap** suits a Rojo or file-based workflow, since their IDL files are easy for an agent to edit and they validate payloads. Blink's README also credits icons for a Studio plugin with autocompletion, which suggests it can work in a Studio-centric workflow. In a pure Studio + MCP workflow, where an IDL compile step is awkward, **ByteNet** or **Packet** (pure Luau modules) or a thin hand-written buffer wrapper are simpler. Avoid BridgeNet2 and Knit's networking for new work.
- Obfuscation and compression are deterrents, not security. Every handler still needs semantic validation (state, cooldown, range, timestamps) on the server.

### Gaps
- No current (2026) official Roblox figure for the per-player bandwidth ceiling was found. The 50 KB/s figure is a 2021 community measurement.
- Packet's documentation and source were not directly verifiable (it is distributed through DevForum or the Creator Store, not a readable GitHub README).
- No neutral third-party benchmark of Blink, Zap, ByteNet and Packet was found; the available benchmarks are maintained by library authors or forum users.

---

## 4. Code architecture in 2026: frameworks, patterns, ECS, typed Luau, state replication

### Takeaway
Knit is archived and should not be used for new projects. The mainstream 2026 pattern is a framework-less "single-script architecture": one server Script and one client LocalScript bootstrap plain ModuleScript services and controllers. Add a dedicated typed networking library, strict Luau under the new type solver, and optionally an ECS (Jecs is the performance leader; Matter continues as a community fork) plus a state-replication library (Replica, which supersedes ReplicaService, or Charm with charm-sync). The Input Action System is fully released and required by Server Authority.

### Cited Findings
- **Knit**: "No Longer Maintained… Knit has been archived and will no longer receive updates". It was archived on 2024-07-31 (via search summary). The author's reasons:
  - Knit "cannot fully benefit from types, and thus does not have good intellisense".
  - The service role "is easy to replicate, as ModuleScripts themselves can already work in this way".
  - Networking wrappers are "trivial", and runtime type checks over the network are a separate concern.
  
  Sources: [Knit README](https://raw.githubusercontent.com/Sleitnick/Knit/main/README.md); [Knit ARCHIVAL.md](https://raw.githubusercontent.com/Sleitnick/Knit/main/ARCHIVAL.md); [GitHub: Sleitnick/Knit](https://github.com/Sleitnick/Knit)
- Knit-style successors exist: OwlKnit (rewritten from scratch in 2026 as a "spiritual successor") and Sleitnick's "Axis" (a provider framework without networking). "Prvd 'M Wrong" is described as not production-ready. — [DevForum: OwlKnit](https://devforum.roblox.com/t/owlknit-a-modern-and-knit-inspired-framework-v112/4761632); [DevForum: Is the Knit Framework still reliable?](https://devforum.roblox.com/t/is-the-knit-framework-still-reliable/3386821) (via search summary)
- **Single-script architecture**: many ModuleScript "systems", plus a single server Script and a single LocalScript that load and start them. Services are server singletons and controllers are client singletons. Sensitive code goes in ServerScriptService and shared utilities in ReplicatedStorage. — [DevForum: Single script Architecture](https://devforum.roblox.com/t/single-script-architecture/3659625); [Gist: script architectures tutorial](https://gist.github.com/lisachandra/0b5d74333c8f24598d9c7a516ec41617) (via search summary)
- **Jecs**:
  - Iterates "800,000 entities at 60 frames per second".
  - Type-safe Luau API, entity relationships as first-class citizens, archetype/SoA storage, zero dependencies, unit-tested.
  - Its creator describes it as production-ready.
  
  Sources: [Jecs README](https://raw.githubusercontent.com/Ukendio/jecs/main/README.md); [DevForum: Jecs](https://devforum.roblox.com/t/jecs-optimizing-declarative-scene-graphs-with-ecs/3263203) (via search summary)
- **Matter**: the original `evaera/matter` repo is "no longer maintained"; a community fork `matter-ecs/matter` continues (Wally `matter-ecs/matter@0.8.4`). — [evaera/matter README](https://raw.githubusercontent.com/evaera/matter/main/README.md); [matter-ecs README](https://raw.githubusercontent.com/matter-ecs/matter/main/README.md)
- **State replication**:
  - ReplicaService is "no longer supported"; "FOR NEW PROJECTS – USE Replica". Replica is a server-to-client replication solution where developers "subscribe certain players to certain states": [ReplicaService README](https://raw.githubusercontent.com/MadStudioRoblox/ReplicaService/master/README.md); [Replica README](https://raw.githubusercontent.com/MadStudioRoblox/Replica/main/README.md).
  - **Charm** provides fine-grained reactive signals, computed values and effects. Its companion `charm-sync` lets the server `addSignalsToClient` per player and send patches through your own remote via `server.connect`: [Charm README](https://raw.githubusercontent.com/littensy/charm/main/README.md).
  - **Reflex** is an earlier Rodux-style "producer" state container by the same author: [Reflex README](https://raw.githubusercontent.com/littensy/reflex/master/README.md).
- **Typed Luau**: the New Type Solver reached General Release, and the Studio Beta toggle was removed on 2026-01-07. The rollout targeted nocheck and non-strict scripts; strict-mode users of the beta needed `Workspace.UseNewLuauTypeSolver = Enabled`. New features include read-only table properties, better refinements and type functions. — [DevForum: [General Release] Luau's New Type Solver](https://devforum.roblox.com/t/general-release-luau%E2%80%99s-new-type-solver/4084991) (via search summary)
- **Input Action System (IAS)** is in Full Release:
  - `InputAction` has types Boolean and Direction1D/2D/3D.
  - `InputContext` groups actions that can be enabled, disabled and prioritized.
  - `InputBinding` maps hardware inputs.
  - Default player scripts were converted to IAS.
  
  Source: [DevForum: [Full Release] Input Action System](https://devforum.roblox.com/t/full-release-input-action-system-ias-newly-converted-player-scripts/4678416) (via search summary). Server Authority requires `PlayerScriptsUseInputActionSystem` and IAS inputs for core simulation: [server-authority/index.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/projects/server-authority/index.md)
- **Deferred signals**: Server Authority requires `Workspace.SignalBehavior = Deferred`, under which event handlers resume at later resumption points instead of immediately. — [server-authority/index.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/projects/server-authority/index.md); [Workspace.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/Workspace.yaml)

### Inferences
- **Recommended skeleton for this project (agent-friendly):**
  - `ServerScriptService/Server.server.luau` requires and starts `Services/*`: CombatService, AbilityService, StatusService (stun, i-frames, posture), HitValidationService, RaceService, DataService.
  - `StarterPlayerScripts/Client.client.luau` starts `Controllers/*`: InputController (IAS), CombatController (prediction, animations), VfxController, CameraController.
  - `ReplicatedStorage/Shared/*` holds ability definitions per race, frame-data tables, pure combat math (damage scaling, posture), network definitions and types.
  - Every module starts with `--!strict` and exports typed `Ability`, `CombatState` and `HitClaim` types. Pure functions (damage, scaling, state transitions) carry no Instance dependencies, so they can be unit-tested headlessly through Jest Lua or MCP-executed Luau.
- **Where ECS fits:** Jecs is worthwhile if the game has many simultaneous projectiles, summons, status effects or NPC mobs (isekai dungeons). Components then look like `Stunned{until}`, `IFrames{until}`, `Burning{dps, until}` and `Projectile{...}`, and a status system ticks them each Heartbeat. For player-vs-player melee alone, plain services plus per-character state tables are simpler.
- **Replication of combat state:** use character **attributes** for small, public, frequently read flags (`CombatState`, `StunUntil`), which is also the only option under Server Authority. Use Replica or charm-sync for private or structured state (cooldown table, resource bars, race and level data).
- **Agent workflow note:** strict types plus data-driven ability tables let Claude Code add a new race kit by writing data and VFX modules rather than editing the core loop. That lowers regression risk.

### Gaps
- No community survey from 2026 was found quantifying framework adoption (single-script vs OwlKnit vs ECS) among top combat games.
- Whether Jecs is used by specific top combat games could not be verified.

---

## 5. Fighting/action game design principles that translate to Roblox

### Takeaway
Think in 60 Hz frames, which matches Roblox's fixed simulation step. Every attack has startup, active and recovery frames; hitstun and blockstun determine frame advantage. Hitstop, input buffering, cancel windows, combo scaling and clear telegraphs make combat feel good and fair. On Roblox, network latency (6 frames at 100 ms) must be budgeted into startup and telegraph lengths and into defensive windows. Asymmetric archetypes (rushdown, zoner, grappler, all-rounder) give six races distinct identities while staying balanced through rock-paper-scissors matchups.

### Cited Findings
- Frame data:
  - Most fighting games run at 60 fps.
  - An attack has **startup** (frames before the hitbox appears), **active** (frames the hitbox is out) and **recovery** (frames until neutral).
  - Frame advantage is "whose turn it is": +5 on hit means the attacker can act 5 frames before the opponent; minus on block means it is the opponent's turn.
  
  Sources: [Very Nice Game: How frame data works](https://verynicegame.com/fighting/how-frame-data-works-in-fighting-games/); [Fighting Game Guide: Frame data](https://www.fightinggameguide.com/framedata.html); [critpoints: Understanding Framedata](https://critpoints.net/2016/11/29/understanding-framedata-combos-traps-and-turns/) (via search summary)
- Concrete values from Street Fighter 6 (character JP):

| Move | Hitstop | Hitstun | Blockstun |
|---|---|---|---|
| 5LP (light punch) | 9 | 17 | 11 |
| 5MP (medium punch) | 11 | 25 | 18 |
| 5HP (heavy punch) | 13 | not given | not given |
| 5HK (heavy kick) | not given | 28 | 23 |

  A general pattern of light/medium/heavy causing 8/12/16 frames of hit/block stop is also reported for a Capcom title (exact game not confirmed). — [SuperCombo: SF6 JP frame data](https://wiki.supercombo.gg/w/Street_Fighter_6/JP/Frame_data); [Capcom SFV column: Basics of Attacking](https://game.capcom.com/cfn/sfv/column/131545?lang=en) (via search summary)
- Input buffering:
  - Street Fighter 6: moves can be buffered up to 4 frames early, a 5-frame window.
  - Street Fighter V: 3 frames.
  - Super Smash Bros. for 3DS/Wii U: 10 frames.
  - A general guideline puts buffers at 5–15 frames (≈80–250 ms).
  
  Sources: [SuperCombo: SF6 Game Data](https://wiki.supercombo.gg/w/Street_Fighter_6/Game_Data); [SmashWiki: Buffer](https://www.ssbwiki.com/Buffer); [salivity: Input buffering](https://salivity.github.io/game-development/article/input-buffering-for-better-combat-responsiveness) (via search summary; the last one is a secondary blog)
- Hitstop (hit freeze) stops both characters briefly on impact. It makes hits feel heavier and gives players time to hit-confirm and input cancels. — [SuperCombo: SF6 Game Data](https://wiki.supercombo.gg/w/Street_Fighter_6/Game_Data); [SonicHurricane: Impact Freeze](https://sonichurricane.com/?p=1043) (via search summary; the exact page holding this wording was not isolated)
- Hitstop typically lasts 3–12 frames (0.05–0.2 s), and Masahiro Sakurai has discussed the term and its use. — [swordarcade: Hit-stop and screen shake](https://swordarcade.xyz/guides/game-feel-hitstop-and-screen-shake/) (secondary blog); [MyNintendoNews: Sakurai on hitstop](https://mynintendonews.com/2015/11/12/sakurai-talks-about-the-term-hitstop-used-in-fighting-games/) (via search summary)
- Research on "impact feel" found that hitstop, sound coherence and camera control strongly influence perceived impact. — [Lin et al. (UW) paper](https://faculty.washington.edu/zkwen/articles/lin22features.pdf); [Pichlmair & Johansen, Designing Game Feel survey (arXiv)](https://arxiv.org/pdf/2011.09201) (via search summary). Jan Willem Nijman's GDC talk "The Art of Screenshake" and Steve Swink's book "Game Feel" are commonly cited references (mentioned in the same search results; not accessed directly).
- Combo damage scaling (proration):
  - Successive hits deal progressively less damage, so long combos are not overwhelming.
  - Street Fighter V scales per move rather than per hit.
  - Guilty Gear and Dragon Ball FighterZ add "starter" proration: combos started with lights deal less overall, which trades easy confirms for damage.
  
  Sources: [SuperCombo: Combo Theory](https://wiki.supercombo.gg/w/Combo_Theory); [Dustloop: BBCF Damage](https://www.dustloop.com/w/BBCF/Damage) (via search summary)
- Telegraphs:
  - Anticipation (wind-up) signals the attack so getting hit "feels fair… a mistake the player can learn to avoid".
  - The anticipation should hint at the follow-up attack.
  - In Sekiro, most enemy attacks are telegraphed by a huge anticipation, held for over a second in one example, and difficulty is tuned through attack count and timing.
  
  Sources: [GDKeys: Anatomy of an Attack](https://gdkeys.com/keys-to-combat-design-1-anatomy-of-an-attack/); [Bugnet: Enemy attack telegraphs](https://bugnet.io/blog/how-to-design-enemy-attack-telegraphs); [Adam Turnbull on X (Sekiro)](https://x.com/animturnbull/status/1116028901770158080) (via search summary)
- Archetypes:
  - Rushdown: fast and high pressure, with low health or poor range.
  - Zoner: strong projectiles and long normals, weak up close.
  - Grappler: big and slow, with high-damage grabs.
  - All-rounder.
  - Rushdown beats zoner, zoner beats grappler, and grappler beats rushdown, a rock-paper-scissors triangle.
  
  Sources: [Medium: Fighting Fair – balanced fighting game](https://cfrusso18.medium.com/fighting-fair-how-to-create-a-balanced-fighting-game-c23310adfcac); [Let's Learn Fighting Games: Rushdown](https://letslearnfightinggames.wordpress.com/2021/03/29/character-type-1-the-rushdown-character/); [FrayTools: Character Archetypes](https://fraytools.fandom.com/wiki/Character_Archetypes) (via search summary)
- Defense economy (Deepwoken model): parry, block and posture with block-break stun, as detailed in section 1. — [Deepwoken Wiki](https://deepwoken.fandom.com/wiki/Combat_Mechanics)
- Roblox-specific latency design: delayed effects (a "fuse") mask resimulation artifacts better than instant effects, and lower acceleration looks smoother under latency. — [server-authority/techniques.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/projects/server-authority/techniques.md)
- Roblox fixed simulation runs at 60 Hz (16.67 ms per frame), and 100 ms of latency is about 6 frames. — [DevForum: Server Authority Tech Deep Dive](https://devforum.roblox.com/t/server-authority-tech-deep-dive-engineering-insights/4624565) (via search summary)

### Inferences
- **Frame-to-time table at 60 Hz:** 1 f = 16.7 ms; 4 f = 67 ms; 6 f = 100 ms (a typical RTT); 9 f = 150 ms; 12 f = 200 ms; 18 f = 300 ms. Store ability timings as frames in data tables and convert to seconds with `frames / 60`.
- **Latency-aware frame data (design proposals, not sourced standards):**
  - For a move to be reactable by the defender online, its startup should exceed human reaction time plus the defender's one-way latency plus replication delay. Fast "true combo" links (≤4-frame gaps) are only reliable when the server or attacker resolves them. So prefer stun-based combos where the server holds the victim in hitstun, rather than tight player-execution links.
  - Use larger input buffers than offline fighting games (e.g., 6–10 frames, about 100–167 ms) to absorb jitter.
  - Make parry windows explicit server-side (e.g., 8–15 frames), validated against the victim's parry timestamp, with RTT tolerance.
- **Hitstop on Roblox:** on hit confirmation, set each client's `AnimationTrack:AdjustSpeed(0)` for the attacker and victim for N frames (lights about 3–5, heavies about 8–12, within the 3–12 frame range cited above). Pair it with a camera shake and a hit-flash. The attacker plays the effects predictively and other clients play them on the server's `CombatResult`. Keep hitstop cosmetic; do not stretch server-side state timers, or desync risk grows. Under Server Authority, implement hitstop in render code only, since animation is not resimulated.
- **Combo scaling proposal:** multiply damage by `max(0.4, 1 − 0.1 × (hitIndex − 1))`, with starter proration for M1 openers and a hard combo cap via "stun decay". Gravity or launch scaling ends juggles, and a short post-combo invulnerability or "burst" mechanic prevents infinite combos in team fights (a common battlegrounds complaint).
- **Six races mapped to archetypes (identity proposal):**
  - Humans: all-rounder with technique variety, weapon and stance switching.
  - Elves: zoner with ranged and magic projectiles, mobility and weak posture.
  - Demons: rushdown with fast startup, lifesteal and high pressure, but low defense.
  - Dragon-people: grappler or bruiser with high posture, armor on heavies, slow startup and large telegraphed AoE.
  - Angels: aerial or support with flight, burst heals or shields, and parry-centric holy counters.
  - Magic monsters: set-play or summoner with traps, minions and status effects (ECS-friendly).
  
  Balance with the rock-paper-scissors triangle, and give each race one universal defensive tool (block, parry, dodge) with race-flavored timing.
- **Readable telegraphs are doubly important on Roblox:** they cover network delay. A 300–500 ms glowing wind-up on a big ultimate is both cinematic and lag-tolerant.

### Gaps
- GDC Vault and YouTube (Core-A Gaming) were blocked, so talks such as "The Art of Screenshake" and Core-A Gaming analyses could not be quoted directly.
- No published frame data was found for Roblox combat games (TSB, JJS, Deepwoken) to anchor Roblox-specific typical values.

---

## 6. Testing combat: dummies/bots, automated tests, latency simulation in Studio, metrics

### Takeaway
Studio now has first-class tooling for combat netcode testing:
- multi-client playtests (up to 8 clients) with separate client and server pause/step at 1/60 s;
- a beta Network Simulator with latency, jitter and loss presets (including a "Bad Connection (3G)" preset at 150–180 ms with 70–90 ms jitter), plus scriptable `NetworkSettings`;
- `StudioTestService` for scripted multi-client tests from plugins, which complements Studio's built-in MCP server;
- a Server Authority visualizer with prediction and input metrics;
- Jest Lua (the framework Roblox uses internally) for unit tests.

### Cited Findings
- In Test mode, Studio runs separate client and server simulations. "Server & Clients" supports up to 8 clients ("usually 1–2 is sufficient"). You can pause and resume the client or server separately and step forward 1/60 s (60 Hz); only `PreAnimation`, `PreSimulation`, `PostSimulation` and `Stepped` callbacks pause. — [creator-docs: studio/testing-modes.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/studio/testing-modes.md)
- **Network Simulator** (beta; enable it with File → Beta Features → "New Device Simulator", then Test → Device Simulator → "Network" pill) adds latency, jitter and packet loss independently inbound (server to client) and outbound (client to server). The values add to the real connection, which matters in Team Test. Presets (latency / jitter / loss):

| Preset | Inbound | Outbound |
|---|---|---|
| Ideal Fiber | 8 ms / 0 / 0% | 8 ms / 0 / 0% |
| Wired Broadband | 25 / 3 / 0% | 25 / 3 / 0% |
| Home Wi-Fi | 30 / 12 / 0.20% | 30 / 15 / 0.30% |
| Standard Mobile (4G/LTE) | 45 / 20 / 0.40% | 55 / 30 / 0.50% |
| Bad Connection (3G) | 150 / 70 / 0.50% | 180 / 90 / 0.50% |

  The docs recommend it specifically for Server Authority prediction and rollback and for UnreliableRemoteEvents. — [creator-docs: studio/network-simulator.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/studio/network-simulator.md); [testing-modes.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/studio/testing-modes.md); [DevForum: Studio Beta – Network Simulator](https://devforum.roblox.com/t/studio-beta-new-device-simulator-toolbar-and-network-simulator/4861695)
- Scriptable equivalents on `NetworkSettings`, for playtest connections:
  - `InboundNetworkMinDelayMs`, `InboundNetworkJitterMs` and `InboundNetworkLossPercent` (loss capped at 0.5%), plus the `Outbound*` counterparts.
  - Per-packet delay is rounded to 1 ms.
  - The legacy `IncomingReplicationLag` takes seconds.
  
  Source: [creator-docs: NetworkSettings.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/NetworkSettings.yaml)
- **StudioTestService** (Studio-only) lets plugins automate tests. `ExecuteMultiplayerTestAsync(numPlayers, args)` launches one server and 1–8 client DataModels and yields until the server calls `EndTest`. Scripts read `GetTestArgs`. `AddPlayers`, `LeaveTest` and `ExecutePlayModeAsync` are also available. It "complement[s] the existing playtest automation available through Studio's built-in MCP server", whose `start_stop_play` tool starts a single Play Client session. `StudioDeviceSimulatorService` and `VirtualInput` are listed alongside it as Studio-only scripted testing services. — [creator-docs: StudioTestService.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/StudioTestService.yaml); [testing-modes.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/studio/testing-modes.md); [DevForum: Introducing StudioTestService](https://devforum.roblox.com/t/introducing-studiotestservice/4116257); [DevForum: New Studio Testing APIs and Assistant Improvements](https://devforum.roblox.com/t/new-studio-testing-apis-and-assistant-improvements/4657854)
- **Jest Lua** is the Lua port of Jest (aligned to Jest v27.4.7) that Roblox uses internally for apps, core scripts and Studio plugins. It currently runs only inside Roblox. A `roblox-testservice-watcher` plugin re-runs tests when scripts change. TestEZ remains available (e.g., `@rbxts/testez`). — [GitHub: jsdotlua/jest-lua](https://github.com/jsdotlua/jest-lua); [GitHub: roblox-testservice-watcher](https://github.com/OrbitalOwen/roblox-testservice-watcher); [npm: @rbxts/testez](https://www.npmjs.com/package/@rbxts/testez) (via search summary)
- **Server Authority visualizer** (Ctrl+Shift+F6 or ⌘+Shift+F6) shows:
  - instance prediction success rate over the last 8 s;
  - input accept rate (on-time inputs);
  - client-server step delta (its stability reflects connection stability);
  - RCC heartbeat FPS (below 59 means the server can't keep up);
  - predicted instance count;
  - input drop reasons ("too old", "out of order", "buffer full").
  
  The "Are Regions Enabled" setting shows the prediction radius. — [server-authority/techniques.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/projects/server-authority/techniques.md)
- Runtime metrics:
  - `Player:GetNetworkPing()` gives RTT in seconds: [Player.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/Player.yaml).
  - The Developer Console shows average ping, memory and Luau heap, and has a Script Profiler. Its "Network" tool covers web/HTTP calls, not remote traffic: [creator-docs: studio/developer-console.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/studio/developer-console.md).
  - Bandwidth can be sampled with `Stats.DataSendKbps + Stats.PhysicsSendKbps`, as in Chrono's benchmark methodology: [Chrono README](https://raw.githubusercontent.com/Parihsz/Chrono/master/README.md).
- Chickynoid includes a server-side bot system for adding bots and NPCs, a useful model for combat dummies. — [Chickynoid README](https://raw.githubusercontent.com/easy-games/chickynoid/main/README.md)

### Inferences
- **Test pyramid for this project:**
  1. **Unit tests** (Jest Lua, or Luau run through the MCP server) for pure modules: damage and scaling math, posture, the state machine transition table (e.g., "Stunned cannot start Attack", "longest stun wins"), cooldown logic, and validation math (distance/angle/rewind interpolation with synthetic snapshots).
  2. **Scripted dummy scenarios** in a test place, using server-side dummy rigs with behaviors: idle, always-block, parry-on-frame-N, strafe at WalkSpeed X, dash spam. Each test asserts outcomes such as "M1 chain lands 4/4 on idle dummy", "parry at t=…ms reflects", and "finisher ragdolls and recovers within Y s".
  3. **Multi-client netcode tests** via `StudioTestService:ExecuteMultiplayerTestAsync(2…4)` with Network Simulator presets (Home Wi-Fi, 4G, 3G) applied through `NetworkSettings`. Run a scripted attacker client against a moving victim and record the server's accept and reject reasons.
- **Metrics to log per session** (inference): hit-claim acceptance rate, overall and per rejection reason (distance, angle, rewind-out-of-range, cooldown, state); median and p95 rewind age; client "whiff while it looked like a hit" reports (claims rejected within tolerance); damage events per second per player; remote calls per second per player against your token-bucket limits; `DataSendKbps` per player; server heartbeat FPS; and, under Server Authority, prediction success rate and input accept rate from the visualizer.
- **Claude Code + MCP workflow:**
  - Have the agent create dummies and run combat scenarios in Run or Play mode through the MCP `start_stop_play` and execute-Luau tools.
  - Use `StudioTestService` from a small helper plugin for multi-client cases.
  - Write results to the Output log as structured lines (e.g., JSON) so the agent can parse pass/fail.
  - Gate every refactor of the hit-validation or state-machine modules on these tests.

### Gaps
- No public data was found on how top Roblox combat games test (bot frameworks, CI). Community practice beyond Jest Lua and TestEZ could not be verified.
- It is unconfirmed whether Network Simulator settings apply to `StudioTestService` multi-client sessions launched from a plugin. The docs describe them separately.
- The exact Studio MCP server tool set beyond `start_stop_play` (as referenced in the StudioTestService docs) was not verified in this session.
