# Roblox Performance Optimization & Visual Fidelity (engine state as of October 1, 2026): a measurement-and-fix playbook for an AI agent

> Source baseline: The Roblox `creator-docs` repository (the source of create.roblox.com docs). I read it locally from a sparse git clone at commit `578b33e` (committed 2026-10-01). "Added on" dates come from that repo's git history, fetched shallow from 2025-01-01, so a date of 2025-01-06 means "already present before 2025". The Luau VM performance guide was read from `luau-lang/site` (branch master, last commit 2026-09-29). DevForum and news items could not be fetched directly (blocked domains). They come from WebSearch result summaries and are marked "(search summary)". Treat them as lower-confidence than the docs.
>
> Short URL keys used below:
> - DOCS = `https://github.com/Roblox/creator-docs/blob/main/content/en-us/`
> - REF = `https://github.com/Roblox/creator-docs/blob/main/content/en-us/reference/engine/`

## 1. Rendering performance: draw calls, instancing, parts vs MeshParts vs unions, shadows, transparency, particles/lights, textures, LOD, budgets

### Takeaway
Draw calls (object count × uniqueness) are the main rendering lever on Roblox, ahead of triangles. The engine instances identical meshes only when the asset ID and the SurfaceAppearance/texture/material all match. After draw calls, the next big costs are shadow work, transparency overdraw, particles and dense clusters of small parts. Roblox does not publish PC budgets. Its only concrete budget is a mobile "baseline device" example: under 1,000 draw calls and under 1,000,000 triangles. Community guidance pushes toward 500 or fewer draw calls for low-end phones.

### Cited Findings
**Frame budget**
- Roblox games target 60 FPS by default, which is 16.67 ms per frame with proper frame pacing. Windows users can raise their cap up to 240 FPS. — [performance-optimization/index.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/index.md); [identify.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/identify.md)
- Consistent frame times matter more than averages. The docs' example: 59 frames at 10 ms plus 1 frame at 410 ms is a "huge, jarring stutter" even though it averages 60 FPS. — [microprofiler/index.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/microprofiler/index.md)

**Draw calls and instancing**
- Draw calls "have significant overhead": fewer draw calls per frame means less render time. You can see the count in Render Stats (Shift+F2 in the client). — [improve.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/improve.md)
- **Instancing rule (official):** multiple meshes with the same `MeshContent` are drawn in a single draw call when either:
  - their `SurfaceAppearance`s are identical (if present), otherwise their `TextureContent`s are identical; or
  - their materials are identical when neither a SurfaceAppearance nor a TextureID exists.
  — [improve.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/improve.md)
- **Missed instancing** is common. The usual cause is importing a whole scene at once: the Importer does not de-duplicate meshes, so identical tiles become separate assets. The fix is to upload each mesh once and duplicate it in Studio, using Packages to manage reuse. The docs include a script that prints `Name, MeshId` for every MeshPart so duplicates can be spotted. — [improve.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/improve.md)
- Decals, textures and particles "don't batch well" and add draw calls. Property changes to ParticleEmitters "can have a dramatic impact on performance". A frame-rate drop when looking at one area is a signal of excessive object density there. — [improve.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/improve.md)
- MicroProfiler tag `Perform/Scene/queryFrustumOrdered` (frustum culling): a high cost means there are a lot of elements. The docs' advice: "Perhaps use some larger meshes where a single mesh has more details as opposed to many small individual pieces." `updateInstancedClusters` "updates geometry that uses instanced rendering such as parts". — [tag-table.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/microprofiler/tag-table.md)
- In Roblox's environment-art sample, combining a tower's pieces into one asset cut its draw calls from 8 to 1, at the cost of per-piece editability. The docs recommend doing this only late in development. — [optimize-your-experience.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/tutorials/curriculums/environmental-art/optimize-your-experience.md)
- `Workspace.RenderingCacheOptimizations` lets the renderer cache rendering state and skip recomputing it for static objects, "improving frame rates in scenes with many parts". It is NotScriptable, so it must be set in Studio. — [REF classes/Workspace.yaml](https://github.com/Roblox/creator-docs/blob/main/content/en-us/reference/engine/classes/Workspace.yaml)
- Culling: the engine already does frustum culling and occlusion culling for parts, meshes and terrain. For indoor areas, a manual room/portal system can cut further. — [improve.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/improve.md)

**Parts vs MeshParts vs unions (PartOperations)**
- Official facts:
  - `RenderFidelity` LOD applies to meshes and to solid-modeled parts (unions). — [REF enums/RenderFidelity.yaml](https://github.com/Roblox/creator-docs/blob/main/content/en-us/reference/engine/enums/RenderFidelity.yaml)
  - Memory is tracked separately for GraphicsParts, GraphicsMeshParts, GraphicsSolidModels and GeometryCSG. — [REF enums/DeveloperMemoryTag.yaml](https://github.com/Roblox/creator-docs/blob/main/content/en-us/reference/engine/enums/DeveloperMemoryTag.yaml)
  - SLIM LOD may render unions (PartOperations) incorrectly. — [slim.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/workspace/streaming/slim.md)
- Community (search summary):
  - Unioning 2 parts gives 1 draw call instead of 2, but every unique union is a separate mesh the client must download, and unions are often triangle-heavy.
  - MeshParts are generally more efficient because you control the geometry.
  - For repeated elements (e.g. 100 windows), build one union or mesh and copy it.
  — [DevForum: Unions for performance?](https://devforum.roblox.com/t/unions-for-performance/2270887); [Part Count or Unions?](https://devforum.roblox.com/t/part-count-or-unions-which-produces-more-lag/799767); [Unions vs MeshParts](https://devforum.roblox.com/t/unions-vs-meshparts/1311979)

**Triangles and mesh LOD**
- Triangle count is "not as important as the number of draw calls" but still matters. Common problems are many very complex meshes, or `RenderFidelity = Precise` set on too many meshes. — [improve.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/improve.md)
- An individual mesh cannot exceed 20,000 triangles. — [art/modeling/specifications.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/art/modeling/specifications.md)
- `RenderFidelity` values:
  - `Automatic` (default) picks detail by distance: highest under 250 studs, medium at 250–500 studs, lowest at 500+ studs.
  - `Precise` always renders the highest detail.
  - `Performance` "pushes performance as much as possible", discarding appearance if necessary.
  - Writing the property requires PluginSecurity (so the Command Bar, plugins or MCP can set it).
  — [REF classes/MeshPart.yaml](https://github.com/Roblox/creator-docs/blob/main/content/en-us/reference/engine/classes/MeshPart.yaml); [REF enums/RenderFidelity.yaml](https://github.com/Roblox/creator-docs/blob/main/content/en-us/reference/engine/enums/RenderFidelity.yaml)
- `RenderSettings.MeshPartDetailLevel = DistanceBased` (the default, and what the client uses) only works when `RenderFidelity = Automatic`. — [REF classes/RenderSettings.yaml](https://github.com/Roblox/creator-docs/blob/main/content/en-us/reference/engine/classes/RenderSettings.yaml)
- Model-level LOD (SLIM; details in §2). Roblox's own crowd example with SLIM avatars:
  - Far audience: about 170,000 triangles and 4,000 client instances, versus about 2,600,000 triangles and 60,000 instances without SLIM.
  - Near audience: about 100,000 versus 670,000 triangles.
  — [slim.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/workspace/streaming/slim.md)

**Shadows and lights**
- Shadows are expensive, especially with many shadow-casting lights or many small parts influenced by shadows. The engine degrades shadow quality as the client's graphics quality drops, and disables shadows "at quality levels below 4". The MicroProfiler `ShadowMapSystem` and `Scene/Shadows` tags are "not performed at quality levels below 4". — [improve.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/improve.md); [tag-table.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/microprofiler/tag-table.md)
- Official mitigations:
  - Turn off `BasePart.CastShadow` on small parts, especially far ones.
  - Disable shadows on moving objects.
  - Turn off `Light.Shadows` where not needed.
  - Limit light range and angle, and use fewer lights.
  - Disable lights outside a range, or room by room.
  — [improve.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/improve.md)
- `CastShadow` "is not designed for performance enhancement, but in complex scenes, strategically disabling it on certain parts can improve performance". It may cause shadow artifacts, and the docs recommend leaving it on "in most situations". — [REF classes/BasePart.yaml](https://github.com/Roblox/creator-docs/blob/main/content/en-us/reference/engine/classes/BasePart.yaml)
- Parts cast shadows regardless of their transparency, because the engine assumes they may carry decals. Fully transparent parts without decals should have `CastShadow` disabled. This applies to invisible collision, trigger and helper parts. — [tag-table.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/microprofiler/tag-table.md)
- `computeLightingPerform` (lighting near the camera): the advice is to "manipulate the number of light sources or move the camera less" to reduce lighting recalculation. `LightGridCPU` (voxel lighting, used at lower quality levels): reduce part count or resolution, anchor parts, and use non-shadow-casting geometry for moving objects. — [tag-table.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/microprofiler/tag-table.md)
- The range of PointLight, SpotLight and SurfaceLight is always clamped to 120 studs. `Lighting.ExtendLightRangeTo120` is unused. — [REF classes/Lighting.yaml](https://github.com/Roblox/creator-docs/blob/main/content/en-us/reference/engine/classes/Lighting.yaml)
- CastShadow cost grows with geometric complexity. Roblox's environment-art sample disables CastShadow on foliage near the edges of the play area. — [assemble-an-asset-library.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/tutorials/curriculums/environmental-art/assemble-an-asset-library.md); [optimize-your-experience.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/tutorials/curriculums/environmental-art/optimize-your-experience.md)
- Older Roblox lighting notes (2019-era "Future Is Bright" tech preview, search summary):
  - Shadow-update cost depends on both geometric detail and the number of shadow-casting lights.
  - A moving, large-radius light inside a building forces the whole building to be re-rendered every frame for that light's shadows.
  — [Future Is Bright comparison page](https://roblox.github.io/future-is-bright/compare.html) (search summary; an old source, so treat as directional)

**Transparency and overdraw**
- Avoid transparency values other than 0 and 1. Partial transparency risks "high transparency overdraw". — [design.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/design.md)
- Overlapping semi-transparent objects (foliage, glass) force the same pixels to be rendered many times. Roblox's planter example produced "hundreds of thousands of overdrawn pixels". The fix is to review and delete layered transparencies. — [optimize-your-experience.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/tutorials/curriculums/environmental-art/optimize-your-experience.md)
- `MeshPart.DoubleSided` renders polygons twice. Roblox's sample enables it only on foliage. — [assemble-an-asset-library.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/tutorials/curriculums/environmental-art/assemble-an-asset-library.md)

**Particles**
- One ParticleEmitter can emit up to 400 particles per second (100 per second on mobile). Particle size affects fill rate, and overlapping particles cause overdraw. Keep `Rate` as low as possible. — [effects/particle-emitters.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/effects/particle-emitters.md)
- Related MicroProfiler tags:
  - `updateDynamicParts` prepares Beams, ParticleEmitters and Humanoids for rendering.
  - `updateParticles` / `updateParticleBoundings` update particle positions and bounds. Reduce emitters, rates and lifetimes, and limit emitter movement.
  — [tag-table.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/microprofiler/tag-table.md)

**Texture memory**
- Graphics memory depends on pixel count, not file size: a 1024² texture uses 4× the memory of a 512². Uploads are transcoded to a fixed format, so removing alpha or using a smaller color model saves nothing. Use 512² or less unless the texture covers a large part of the screen, and 256² or less for minor images. — [improve.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/improve.md)
- Texel-density guidance:
  - 5×5-stud objects: 256²
  - 10×10-stud objects: 512²
  - 20×20-stud objects: 1024²
  - Default materials show 1024² on an 8×8-stud face.
  - Textures up to 4096² are supported.
  — [texture-specifications.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/art/modeling/texture-specifications.md)
- Use one texture tinted with `SurfaceAppearance.Color` instead of several recolored copies. Tinting "does not affect performance" and saves memory. — [improve.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/improve.md); [surface-appearance.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/art/modeling/surface-appearance.md)
- Built-in materials use "far less memory than custom textures". — [design.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/design.md)

**Budgets and device mix**
- The only official budget is an example: testing on a chosen baseline device you "could … determine that you need to stay below 1,000 draw calls and 1,000,000 triangles". — [design.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/design.md)
- Community guidance (search summary):
  - "aim for 500 or fewer drawcalls to ensure good performance across even relatively low spec mobile phones".
  - A blog claims well-optimized games keep under 5,000 Workspace instances during play, and that 15–20k is "almost always struggling on mobile".
  - Both come from secondary sources and are unverified.
  — [DevForum: Too much draw calls](https://devforum.roblox.com/t/too-much-draw-calls-for-actually-no-reason/4271244); [mcrs-docs Roblox Optimisation](https://mcrs-docs.gitbook.io/robloxvistools/articles/roblox-optimisation); [santozstudios blog](https://santozstudios.com/blog/roblox-performance-optimisation-guide/)
- Player hardware:
  - Android is about 65% of a typical game's players.
  - About 60% of those Android devices have 2–4 GB RAM, about 35% have 4–8 GB, and about 5% have more than 8 GB.
  - Over 50% of Roblox players use devices scoring 10,000–20,000 on Passmark.
  — [test-on-hardware.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/test-on-hardware.md)

### Inferences
- **Capital-city draw-call audit (agent-runnable):**
  - Histogram `MeshId` + `TextureID` + SurfaceAppearance identity across the city. Collapse near-duplicate assets to one ID. Replace many-part props that repeat (lamps, windows, crates) with one MeshPart or package duplicated.
  - Unique unions should be re-used, or replaced by MeshParts.
  - This attacks the number-one documented cost.
- **Cheap shadow wins with no visual loss:**
  - Turn off CastShadow on every `Transparency == 1` part that has no decal.
  - Turn off shadows on small decorative lights and on any moving or animated light.
  - Turn off CastShadow on small or distant props outside the playable path.
  - Keep shadows on hero geometry and the key lights of cinematic scenes.
- **Isolating the 35–38 FPS scene:** it is plausibly bound by one of four things: many shadow-casting local lights, layered transparency (glass, foliage, particles, Beams), very high object density in view, or heavy post-processing. The §5 protocol isolates which one by A/B toggling each category while reading `Stats` counters.
- **Choosing a budget:** with no official PC budget, use the documented mobile example (under 1,000 draw calls and 1M triangles per view) as the hard ceiling. Treat 500 draw calls as the target for crowded cinematic views. Verify on a real low-end device, because Studio numbers are skewed (§5).

### Gaps
- No official per-platform (PC/console/mobile) draw-call, triangle, light-count or particle budgets beyond the single baseline-device example.
- No reliable numeric guidance on how many shadow-casting lights "Future"/Realistic lighting tolerates. One search result claimed "85% GPU load", but it came from a low-quality aggregator and was discarded.
- Instancing batch limits are unknown. A DevForum thread, ["Why does the same mesh use more than 1 draw call when duped a lot?"](https://devforum.roblox.com/t/why-does-the-same-mesh-use-more-than-1-draw-call-when-duped-a-lot/3988136), suggests batches split, but I could not read it.

## 2. Streaming and loading: StreamingEnabled settings, focus control for cutscenes, preloading, join time, and making a distant reveal shot render fully and fast

### Takeaway
Under instance streaming, content far from the replication focus (the character, by default) is simply absent. Distant models without a LevelOfDetail representation are invisible, and meshes and textures now stream low-resolution first, then ramp up. A reliable reveal needs four things:
- Steer streaming to the shot ahead of time, from the server: `RequestStreamAroundAsync` with a timeout, a temporary `AddReplicationFocus` or `ReplicationFocus`, and/or `Player.FrustumStreaming = Enabled`.
- Give static city models `LevelOfDetail = SLIM`, so the skyline renders even beyond the streaming radius.
- Favor view distance (`Lighting.PrioritizeLightingQuality = false`).
- Leave a few seconds' settle time for mesh and texture LODs to ramp before the camera reveals.

### Cited Findings
**Settings (recommended values; all NotScriptable, so set in Studio)**
- Roblox's recommended values:
  - `EnableSLIMAvatars = Enabled`
  - `ModelStreamingBehavior = Improved`
  - `StreamingIntegrityMode = PauseOutsideLoadedArea`
  - `StreamingMinRadius = 64` (the default)
  - `StreamingTargetRadius = 1024` (the default)
  - `StreamOutBehavior = Opportunistic`
  — [streaming/techniques.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/workspace/streaming/techniques.md); [streaming/index.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/workspace/streaming/index.md)
- These Workspace properties are tagged NotScriptable, and `StreamingEnabled` "is not scriptable": they must be set in Studio's Properties window. Inconsistency: the `EnableSLIMAvatars` description says it can be set via "the Properties window, Command Bar, or a plugin". — [REF classes/Workspace.yaml](https://github.com/Roblox/creator-docs/blob/main/content/en-us/reference/engine/classes/Workspace.yaml)
- `StreamingTargetRadius` is "the maximum distance players will be able to see the full detail of your game". The engine may keep already-loaded content beyond it, memory permitting. Target should exceed Min, because the band between them is a buffer. Raising MinRadius costs memory and server bandwidth. — [streaming/index.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/workspace/streaming/index.md)
- `StreamOutBehavior`:
  - `LowMemory` (the default) removes content only under memory pressure.
  - `Opportunistic` can remove content beyond the target radius even without memory pressure.
  — [streaming/index.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/workspace/streaming/index.md)
- `ModelStreamingBehavior`:
  - `Improved`: "Models are never sent during player join". A model with BaseParts streams in when any of its parts becomes eligible.
  - `Legacy`: model containers and their non-part children are sent at join.
  — [REF enums/ModelStreamingBehavior.yaml](https://github.com/Roblox/creator-docs/blob/main/content/en-us/reference/engine/enums/ModelStreamingBehavior.yaml); [streaming/index.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/workspace/streaming/index.md)
- `ModelStreamingMode`:
  - `Atomic`: all initial descendants arrive together.
  - `Persistent`: sent at join and never streamed out. "Not intended to circumvent streaming", and overuse hurts performance.
  - `PersistentPerPlayer`: persistent only for players added via `AddPersistentPlayer`.
  - Set it in Studio or from server Scripts, never from LocalScripts.
  — [streaming/index.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/workspace/streaming/index.md); [REF classes/Model.yaml](https://github.com/Roblox/creator-docs/blob/main/content/en-us/reference/engine/classes/Model.yaml)
- Model structure for streaming:
  - Group spatially and logically related parts.
  - Keep each model's spatial extent "under ~64 cubic studs" so it streams in together.
  - Decompose huge container models.
  - Flatten nesting: a Persistent model inside an Atomic model forces the Atomic one to behave as Persistent.
  — [streaming/techniques.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/workspace/streaming/techniques.md)
- Moving assemblies with many instances stream in as one unit "may cause network/CPU spikes". — [streaming/index.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/workspace/streaming/index.md)

**Steering streaming toward a cutscene's view**
- **Replication focus:** streaming centers on the character's PrimaryPart unless `Player.ReplicationFocus` is set to another part. That property should only be set from a server Script. — [streaming/index.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/workspace/streaming/index.md); [REF classes/Player.yaml](https://github.com/Roblox/creator-docs/blob/main/content/en-us/reference/engine/classes/Player.yaml)
- **Extra foci:** `Player:AddReplicationFocus(part)` / `RemoveReplicationFocus` are server-only and use the same Min/Target radii as the main focus.
  - Each extra focus adds server work: "a single player with nine dynamically moving foci could generate server networking and streaming processing comparable to ten players".
  - Too many foci on one client risks OS out-of-memory kills.
  - One documented use case is "Distant viewpoints".
  — [streaming/index.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/workspace/streaming/index.md); [REF classes/Player.yaml](https://github.com/Roblox/creator-docs/blob/main/content/en-us/reference/engine/classes/Player.yaml)
- **`Player:RequestStreamAroundAsync(position, timeOut)`:**
  - It yields. Its effect is temporary, and there are "no guarantees of what will be streamed in".
  - `timeOut` defaults to effectively infinite. All requests are abandoned if the client is low on memory.
  - The docs recommend server-side calls before a CFrame change. If the request succeeds, then when it returns "the minimum radius around the target location should be present on the client".
  — [REF classes/Player.yaml](https://github.com/Roblox/creator-docs/blob/main/content/en-us/reference/engine/classes/Player.yaml); [streaming/techniques.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/workspace/streaming/techniques.md)
- **Frustum streaming (new; docs page added 2026-10-01).** `Player.FrustumStreaming` is server-only, with modes `Default`/`Disabled`/`Automatic`/`Enabled`. It streams instances inside the camera's view frustum beyond the normal radius, in addition to the standard cube and any foci.
  - `Automatic` turns on for a narrow FOV, high velocity toward the direction of view, or a camera far from the replication focus, after "a short activation delay". `Enabled` is the manual mode for pre-arming.
  - It reaches out to the lesser of the client's draw distance and an engine maximum. It is switched off automatically when draw distance falls to or below the target radius (low graphics quality or low FPS).
  - Fast camera rotation invalidates the frustum and restarts streaming from the center outward.
  - It does no occlusion culling, and it adds memory and CPU cost. It gets the same budget as a replication focus.
  - With `Opportunistic` stream-out, content that leaves the view lingers 1.5 s before cleanup. With `LowMemory`, it stays.
  — [streaming/frustum.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/workspace/streaming/frustum.md); [REF enums/FrustumStreamingMode.yaml](https://github.com/Roblox/creator-docs/blob/main/content/en-us/reference/engine/enums/FrustumStreamingMode.yaml); added-date from [repo history](https://github.com/Roblox/creator-docs/commits/main/content/en-us/workspace/streaming/frustum.md)
- **Predictive streaming (new; enum docs added 2026-07-30).** `Workspace.PredictiveStreamingMode = Enabled` adds small temporary foci in two cases: at likely respawn points after death, and at a location the player just CFramed away from. It is additive, expires, is skipped on resource-constrained clients, and does not duplicate existing prefetches or foci. `Default` currently means Disabled. — [streaming/index.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/workspace/streaming/index.md); [REF enums/PredictiveStreamingMode.yaml](https://github.com/Roblox/creator-docs/blob/main/content/en-us/reference/engine/enums/PredictiveStreamingMode.yaml)
- Community (search summary): streaming around the character makes cutscenes that move the camera away "render nothing". The workaround is to set the replication focus near the camera. — [DevForum: Big Changes to StreamingEnabled](https://devforum.roblox.com/t/big-changes-to-streamingenabled/351704?page=2)

**Distant visuals: model LOD (SLIM)**
- `Model.LevelOfDetail` values:
  - `SLIM`: renders a cloud-generated composite of all child parts at progressively lower resolutions by distance, "greatly improv[ing] visual quality over StreamingMesh".
  - `StreamingMesh`: a legacy, coarse, colored imposter that does not support textures.
  - `Automatic` and `Disabled`: no low-resolution mesh.
  - Composite meshes have no physics, collision or raycasts.
  - Writing it requires PluginSecurity, so it can be set from the Command Bar, a plugin or MCP.
  — [REF classes/Model.yaml](https://github.com/Roblox/creator-docs/blob/main/content/en-us/reference/engine/classes/Model.yaml); [REF enums/ModelLevelOfDetail.yaml](https://github.com/Roblox/creator-docs/blob/main/content/en-us/reference/engine/enums/ModelLevelOfDetail.yaml)
- SLIM requirements and behavior:
  - It needs StreamingEnabled, a place saved to Roblox (not a local .rbxl), and Team Create enabled.
  - Transcoding happens on first publish or play. Allow 1–2 minutes, then rejoin.
  - It suits static world geometry only: no runtime part or material changes, no animations, no Humanoids, and Scale ≠ 0.
  - Unions may misrender, and UVs may shift on default materials.
  - On unsupported platforms it falls back to `Disabled`.
  - Supported instance types: Part, MeshPart, Decal, Texture, SurfaceAppearance, PartOperation, NegateOperation, SpecialMesh.
  - The docs give a one-loop Command Bar script to convert StreamingMesh models to SLIM.
  — [streaming/slim.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/workspace/streaming/slim.md)
- Timeline: SLIM client beta announced late 2025 (Roblox newsroom, December 2025); docs page added 2026-07-20. — [Roblox newsroom: Introducing SLIM](https://about.roblox.com/newsroom/2025/12/introducing-roblox-slim-scalable-lightweight-interactive-models); [DevForum: [Client Beta] SLIM](https://devforum.roblox.com/t/client-beta-introducing-scalable-lightweight-interactive-models-slim/4034709); [repo history](https://github.com/Roblox/creator-docs/commits/main/content/en-us/workspace/streaming/slim.md)
- **Official AI conversion skill:** `rbx-convert-to-streaming` configures streaming settings, sets SLIM where applicable, refactors model structure, adds `WaitForChild` and nil-checks, and adds prefetches and foci. It can run "using any LLM you prefer through the Model Context Protocol (MCP) in Studio". The docs estimate 20–30 minutes and about 200,000 tokens for a frontier model, and say to back up first. — [streaming/techniques.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/workspace/streaming/techniques.md)

**Asset-level streaming (meshes and textures load progressively)**
- Texture streaming is automatic. It loads baseline-quality textures first, "in order of importance", then raises quality up to the device's memory, prioritizing objects by screen space. It covers MeshPart, SurfaceAppearance, Texture, Decal, MaterialVariant, Beam, ParticleEmitter, and the base materials of Parts and PartOperations. — [parts/textures-decals.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/parts/textures-decals.md); [DevForum: Introducing Texture Streaming](https://devforum.roblox.com/t/introducing-texture-streaming/4144855) (search summary)
- `Workspace.MeshStreamingAndImprovedLods` (RolloutState, NotScriptable): mesh requests "fetch the lowest quality LOD first and stream in higher detail over time", using the "Wild Mesh Simplifier" LOD system. It appeared in the API docs on 2026-04-15. Per Roblox's DevForum opt-in announcement, it became the default around July 2026. — [REF classes/Workspace.yaml](https://github.com/Roblox/creator-docs/blob/main/content/en-us/reference/engine/classes/Workspace.yaml); [DevForum: Mesh Streaming and Improved Cloud LoDs (Opt-in)](https://devforum.roblox.com/t/introducing-mesh-streaming-and-improved-cloud-lods-in-published-experiences-opt-in-phase/4601232) (search summary)
- A DevForum Engine Bugs report is titled ["Mesh Streaming and Improved Cloud LoDs causing stuttering"](https://devforum.roblox.com/t/mesh-streaming-and-improved-cloud-lods-causing-stuttering/4742906) (title only, not read). A third-party site claims up to 70% memory reduction from mesh streaming (unverified). — [creation.dev](https://www.creation.dev/learn/roblox-mesh-streaming-cloud-lods-guide)

**Preloading, loading screens and join time**
- `ContentProvider:PreloadAsync`:
  - Use it only for loading-screen images, key menu images, and important assets in the start or spawn area.
  - Loading the entire Workspace "significantly increases load times".
  - Provide a Skip button if preloading a lot.
  - `RequestQueueSize` is unreliable for progress bars.
  — [improve.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/improve.md); [REF classes/ContentProvider.yaml](https://github.com/Roblox/creator-docs/blob/main/content/en-us/reference/engine/classes/ContentProvider.yaml)
- **PreloadAsync limitations:** it does nothing for `SurfaceAppearance` or `MaterialVariant`, which rely on processed texture packs that stream at runtime. Textures preloaded for instances that are not visible may be unloaded again to save memory. — [REF classes/ContentProvider.yaml](https://github.com/Roblox/creator-docs/blob/main/content/en-us/reference/engine/classes/ContentProvider.yaml)
- Under streaming, a loading screen that waits for a specific spatial instance can hang forever: before the character spawns there is no focus. Either signal readiness once the character and nearby area exist, or `AddReplicationFocus` at the spawn point first. — [streaming/techniques.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/workspace/streaming/techniques.md)
- Measuring load time:
  - There is no built-in tool, and a stopwatch is enough.
  - A ReplicatedFirst script can time `game.Loaded`.
  - Studio Settings → Network → **Print Join Size Breakdown** prints the top 20 instances by size and a breakdown by type.
  — [identify.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/identify.md)
- Don't store everything in ReplicatedStorage, because the client loads all of it. — [design.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/design.md)
- Creating or destroying large hierarchies at runtime is network-heavy, so chunk them. Strip Animation Editor metadata from rigs. — [improve.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/improve.md)

**Visual tricks and debugging**
- Higher graphics quality increases render distance. The Frame Rate Manager scales view distance, block count and quality level. `Lighting.PrioritizeLightingQuality = false` makes the engine keep view distance and scale lighting/shading down first. — [REF enums/QualityLevel.yaml](https://github.com/Roblox/creator-docs/blob/main/content/en-us/reference/engine/enums/QualityLevel.yaml); [REF enums/FramerateManagerMode.yaml](https://github.com/Roblox/creator-docs/blob/main/content/en-us/reference/engine/enums/FramerateManagerMode.yaml); [environment/lighting.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/environment/lighting.md)
- In *The Mystery of Duvall Drive*, Roblox hid the unstreamed "end of the world" with blocking geometry and a winding path. For a huge distant element (a storm), they used perspective tricks and taller nearby trees. — [stream-in-immersion.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/resources/the-mystery-of-duvall-drive/stream-in-immersion.md)
- Streaming debug overlay: Shift+Ctrl+F3, then Shift+1 repeatedly; the 4th panel shows colored streamed regions. Temporarily raise `CameraMaxZoomDistance` (e.g. 1000) to inspect. Test with `StreamingTargetRadius = 64` to expose streaming bugs. — [streaming/index.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/workspace/streaming/index.md); [streaming/techniques.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/workspace/streaming/techniques.md)

### Inferences
- **Why the reveal "needed the camera very close":** the camera sat far from the replication focus (the character). Content outside that focus's radius was not on the client. City models had no SLIM LOD, so nothing drew in their place. On top of that, mesh and texture streaming start every asset at its lowest LOD. Any one of these produces late pop-in, and together they produce the observed symptom.
- **Reveal-shot recipe (agent-implementable):**
  1. Set the city's static building and prop models to `LevelOfDetail = SLIM`, built in small groups per the ~64-studs guidance. Publish with Team Create on, wait for transcoding, and verify from far away.
  2. On the server, before the cutscene, call `player:RequestStreamAroundAsync(cityCenter, 10)`. Optionally call it again for 1–3 other key positions on the camera path, before fading in.
  3. For the shot's duration, either `AddReplicationFocus(anchorPart)` at the city (and remove it afterwards), or set `player.FrustumStreaming = Enabled`. Restore `Default` afterwards.
  4. Fade in from black or blur only after the requests return, plus a short settle delay (e.g. 1–3 s) so mesh and texture LODs ramp up.
  5. Keep `Lighting.PrioritizeLightingQuality = false` for vista-heavy content.
  6. Preload only non-SurfaceAppearance assets used in the shot (decals, sounds, particle textures).
  7. Avoid fast camera whips across the city, which invalidate frustum streaming and add lighting recomputation.
- **Settings to verify:** use `ModelStreamingBehavior = Improved` (faster joins) and `PauseOutsideLoadedArea`. Prefer `Opportunistic` stream-out for memory, but note it discards frustum content 1.5 s after it leaves view. If the shot revisits the same vista, keep a focus there.
- **Frustum streaming is brand new** (docs dated today), so verify it on the live client before relying on it. Keep `RequestStreamAroundAsync` and replication foci as the primary path.
- **Settings an MCP agent cannot write:** the NotScriptable Workspace streaming properties may not be writable via `execute_luau`. The agent should attempt the change, read it back, and fall back to asking the user to set it in the Properties window.

### Gaps
- No official distance thresholds for SLIM's rendering zones, and no documented "engine-defined maximum range" for frustum streaming.
- No API reports "streaming complete for region X" beyond `RequestStreamAroundAsync` returning. Readiness of specific models must be checked client-side (WaitForChild with timeout, CollectionService tags).
- Whether the mesh-streaming stutter report is confirmed or fixed is unknown (thread not readable).
- Exact semantics of "~64 cubic studs" (volume versus per-axis extent) are ambiguous in the docs.

## 3. Z-fighting and flicker: causes, robust fixes, scripted detection

### Takeaway
Z-fighting comes from coplanar or overlapping faces, stacked decals/textures, and surfaces flush with terrain. It gets worse with distance and with narrow FOV, because depth-buffer precision drops. Small nudges (0.001–0.01 studs) fix near-camera cases. They can fail in long cinematic shots, so robust fixes remove the overlap entirely or make it invisible. Only SLIM troubleshooting covers z-fighting in the official docs; the rest is community knowledge plus general graphics theory.

### Cited Findings
- **Official (SLIM troubleshooting):** z-fighting "can occur when parts in the original model have overlapping or coplanar faces". Fix: "Move overlapping parts slightly apart (even 0.01 studs is sufficient)" and "avoid perfectly flush surfaces between adjacent parts in the same model". — [streaming/slim.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/workspace/streaming/slim.md)
- Community (search summary): if overlap cannot be avoided, offset one part along the face normal; "a minuscule offset of around 0.001" is usually enough and unnoticeable. — [DevForum: How to fix clipping / z fighting](https://devforum.roblox.com/t/how-to-fix-clipping-z-fighting-issue/735036); [DevForum: Preventing Z-fighting of textures and parts](https://devforum.roblox.com/t/preventing-z-fighting-of-textures-and-parts-on-top-of-the-texture/347111)
- Distance dependence (search summary):
  - Z-fighting "becomes worse in the distance due to the depth buffer being less accurate".
  - A reported extreme case: a camera with FieldOfView 1 viewing from over 1,000 studs away showed severe z-fighting.
  - Layered decals can flicker at some angles and distances even with the top layer offset by 1 stud (an Engine Bugs report).
  - A 2025 report is titled "Streaming 'Z-Fighting Effect' on meshes at distance".
  — [DevForum: Terrible Z-Fighting Issue](https://devforum.roblox.com/t/terrible-z-fighting-issue/20386); [DevForum: Decals flicker…](https://devforum.roblox.com/t/decals-on-parts-flicker-between-the-top-decal-and-decals-underneath-when-viewing-angle-or-distance-changes/2463254); [DevForum: Streaming Z-Fighting at distance](https://devforum.roblox.com/t/streaming-z-fighting-effect-on-meshes-at-distance/3927548)
- General graphics background: z-fighting happens when two surfaces are at nearly the same depth and the depth buffer cannot separate them. It is worse far from the camera and with wide near/far ranges. Fixes are separating surfaces, tightening clip planes, or depth bias. — [Wikipedia: Z-fighting](https://en.wikipedia.org/wiki/Z-fighting); [bugnet.io guide](https://bugnet.io/blog/how-to-fix-z-fighting-and-flickering-surfaces)
- Detection tooling (community, search summary):
  - `WorldRoot:GetPartsInPart` and `BasePart:IntersectAsync` can find overlaps.
  - Plugins exist: "Remove Z-Fighting via Intersections", the "Advanced Z-Fighting Remover", and "Z-Texture", a client-side fix for black lines where two parts' Textures intersect.
  — [DevForum: Detect which parts are overlapping](https://devforum.roblox.com/t/detect-which-parts-are-overlapping/2834647); [Remove Z-Fighting plugin](https://devforum.roblox.com/t/remove-z-fighting-via-intersections-plugin/2865317); [Advanced Z-Fighting Remover](https://devforum.roblox.com/t/advanced-z-fighting-remover-plugin/2833769); [Z-Texture](https://devforum.roblox.com/t/z-texture-a-texture-z-fighting-fix-client-based/4715991)
- **Spatial-query caveat for detection scripts:** queries such as `GetPartBoundsInBox` and `Raycast` "will never include parts with `CanQuery` of `false`", and `CanQuery` only takes effect when `CanCollide` is false. Decorative parts that are non-collidable and non-queryable are invisible to query-based detectors. — [REF classes/BasePart.yaml](https://github.com/Roblox/creator-docs/blob/main/content/en-us/reference/engine/classes/BasePart.yaml)

### Inferences
- **Why 0.07 studs may not be enough everywhere:** the past fix nudged 3,663 overlaps by 0.07 studs. That is probably sufficient at gameplay distances, which is consistent with the 0.001–0.01 guidance. Reveal shots view the capital from hundreds or thousands of studs, possibly with a narrow FOV. There, depth precision is much coarser, so nudged coplanar pairs can flicker again. They should be re-checked from the actual cinematic camera positions; the Studio MCP `screen_capture` tool accepts a custom camera position and look-at target.
- **Robust fixes, in order of preference:**
  1. Remove the hidden overlapping face or part (merge, trim, or shrink one part so faces no longer share a plane).
  2. Merge static clusters into single meshes. SLIM transcoding also "removes hidden internal geometry" for distant views, but SLIM still z-fights if the source has coplanar faces.
  3. Where coplanar overlap must stay, give both parts identical color, material and texture, so a flicker is invisible.
  4. Use distance-aware offsets for geometry seen from far away.
  5. Avoid stacking multiple Decals or Textures on the same face; bake them into one texture.
  6. Keep part tops slightly above or below flat terrain surfaces, never exactly flush.
- **Detection algorithm sketch (inference; untested):**
  - Iterate all BaseParts in Workspace instead of spatial queries, which miss `CanQuery=false` parts. Bucket parts into a spatial hash.
  - For candidate pairs whose rotations are parallel (axis-aligned up to sign or permutation), compute the six world-space face planes of each Block part.
  - Flag pairs with a same-facing normal, a plane distance under a tolerance (e.g. 0.01 studs), and a positive 2D overlap area of the face rectangles.
  - Separately flag Decals/Textures sharing a face with another decal, and parts whose face lies within the tolerance of a coplanar part they overlap.
  - Rank flagged pairs by visible-difference risk (different Color/Material/texture) and by distance to the cinematic camera path.
  - MeshParts need bounding-box heuristics only, or a manual review list.
- **Verification step:** after nudging, verify no new gaps or light leaks appeared. Nudge consistently (shrink-inward is safer than translate).

### Gaps
- Roblox's depth-buffer configuration (reversed-Z or not, near/far planes) and any engine depth bias are not documented in the sources found. So the safe minimum offset at a given distance cannot be computed and must be found empirically.
- No official Roblox guidance on decal/texture z-fighting or terrain-surface flicker beyond community threads.

## 4. Luau and engine performance: native codegen, types, Parallel Luau, allocation/GC, cleanup and leaks, physics settings, per-frame budgets

### Takeaway
On the client, the wins are algorithmic: do less per frame, spread work across frames, avoid allocations in RenderStepped/Heartbeat code, use Parallel Luau for heavy pure computation, and clean up connections. Native code generation (`--!native` / `@native`) is documented as a server-side feature with size limits; it does not run on clients per the latest available information. Physics settings are documented, near-free wins: anchor static parts, use Box/Hull collision on scenery, turn off CanTouch/CanQuery/CanCollide where unused, and keep adaptive timestepping.

### Cited Findings
**Native code generation**
- `--!native` at the top of a script compiles all its functions natively, plus the top level when deemed profitable. `@native` marks a single function.
  - The docs describe it for "server-side scripts". It suits numeric work on tables and `buffer`s with few heavy API calls.
  - Costs: compile time (slower server startup), extra memory, and a total code limit.
  - Avoid `getfenv`/`setfenv`, built-ins called with non-numeric arguments, and wrongly typed arguments to typed functions.
  - Annotate `Vector3` parameters so vector-specialized code is generated.
  - Breakpoints disable native execution. Script Profiler marks native functions `<native>`.
  - `debug.dumpcodesize()` (Command Bar, Server view) reports native code size.
  - Limits: 64K instructions per code block, 32K blocks per function, and 1 million instructions per script, plus an overall native-code memory limit.
  — [luau/native-code-gen.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/luau/native-code-gen.md)
- Client availability (search summary): Roblox stated that native codegen "is not available on the clients yet", so LocalScripts are not compiled natively. A DevForum feature request asks to enable it for clients. The docs still describe it as server-side, as of commit 2026-10-01. — [DevForum: Luau Native Code Generation Preview Update](https://devforum.roblox.com/t/luau-native-code-generation-preview-update/2961746); [DevForum: Enable --!native for clients](https://devforum.roblox.com/t/enable-native-for-clients/3170510)

**Luau VM performance (official Luau guide)**
- Tables:
  - Create object-like tables with all fields in one literal (the "table templates" optimization).
  - Use `table.create(N)` for arrays of known size.
  - Use `table.insert` when the size is unknown, or indexed writes into a preallocated table.
- Iteration: generalized iteration (`for k, v in t`) performs comparably to `pairs`/`ipairs` and is recommended. `for i = 1, #t` is slightly slower.
- `Vector3` is a native value type (3-wide SIMD), giving "significantly smaller GC pressure".
- Closures are cached only when they have no upvalues, or their upvalues are immutable and module-scoped. Otherwise each `function() end` expression allocates.
- "Avoid allocating memory in tight loops". The GC is incremental, but each cycle's "atomic" step "can result in occasional pauses on the order of tens of milliseconds". Many coroutines and large weak tables make atomic steps worse.
- Use `obj:Method()` calls, and point `__index` directly at a table (no `__index` functions or deep chains). Caching methods in locals "isn't very productive".
— [Luau performance guide (luau-lang/site, master)](https://github.com/luau-lang/site/blob/master/src/content/docs/guides/performance.md), published at [luau.org/performance](https://luau.org/performance)

**Scheduling and frame budget**
- RunService frame events (PreAnimation, PreRender, PreSimulation, PostSimulation, Heartbeat) should be used sparingly. Break up big tasks with `task.wait()`. — [improve.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/improve.md)
- The docs' stutter math: 100 ms of code run once per second in an otherwise-60-FPS game gives 59 frames at 16.67 ms and then one at 100 ms. Instead, do about 5 ms per frame and finish over 20 frames. — [design.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/design.md)
- Event placement:
  - Bind to render step only for work that must happen between input and render, such as the camera. Use `BindToRenderStep` for strict ordering.
  - Physics-affecting logic goes in PreSimulation; physics-reading logic goes in PostSimulation.
  - Set `Motor6D.Transform` in PreSimulation.
  — [task-scheduler.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/microprofiler/task-scheduler.md)
- Legacy `wait`/`spawn`/`delay` should be replaced by `task.wait`/`task.defer`/`task.delay`. — [scripting/scheduler.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/scripting/scheduler.md)
- `WaitingHybridScriptJob` resumes `WaitForChild` and `wait()` waiters about 30 times per second within a time budget. It is throttled when there are too many waiting scripts. — [tag-table.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/microprofiler/tag-table.md)
- Community (search summary): camera cutscene jitter is commonly caused by updating the camera on Heartbeat. The fix is RenderStepped or `BindToRenderStep` with `RenderPriority.Camera`, plus delta-time-based interpolation. — [DevForum: Camera is stuttering during cutscene](https://devforum.roblox.com/t/camera-is-stuttering-during-cutscene/2534430); [DevForum: Issues with scripted camera stuttering](https://devforum.roblox.com/t/issues-with-scripted-camera-stuttering/387257)

**Parallel Luau**
- Mechanics:
  - Code runs in parallel only under `Actor`s, after `task.desynchronize()` or via `:ConnectParallel()`. Return to serial with `task.synchronize()`.
  - Scripts under the same Actor run serially.
  - `require()` is not allowed in a parallel phase.
  - API members without a thread-safety tag are Unsafe. Instance writes need the serial phase; for example, `Terrain:WriteVoxels` must be serial.
- Communication: Actor messaging (`SendMessage`, `BindToMessageParallel`) and `SharedTable` share data across actors.
- Actor count: use "more Actors" than cores. For raycast validation, 64 or more Actors is reasonable even on 4-core systems.
- Long unyielding computations still block.
— [scripting/multithreading.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/scripting/multithreading.md)

**Memory leaks and cleanup**
- Leak mechanics:
  - Connected events keep their callbacks and any referenced values out of reach of the GC.
  - `Player` objects and characters are not auto-destroyed on leave, so connections on them leak. Enable `Workspace.PlayerCharacterDestroyBehavior` or destroy them manually.
  - Tables keyed by player grow unless cleaned.
- Watch `LuaHeap`, `InstanceCount` and `PlaceScriptMemory` in the Developer Console.
— [improve.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/improve.md)
- Streamed-out instances are parented to `nil`, not destroyed, so Luau state reconnects if they stream back in. Client-created or cloned instances are exempt from stream-out unless parented under a server-created instance. — [streaming/index.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/workspace/streaming/index.md)
- Scene Analysis "Unparented instances" shows which scripts hold references to removed instances. "Animation memory" covers animations, which are "one of the most common sources of memory leaks in production". — [scene-analysis.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/scene-analysis.md)
- Cleanup libraries (community, search summary): Janitor is described as more maintained than Maid, with better typing and custom cleanup methods (e.g. cancelling a Tween). Trove and Janitor are both solid choices. Don't use a cleanup library for one or two connections. — [DevForum: Using Janitor to combat memory leaks](https://devforum.roblox.com/t/using-janitor-to-combat-memory-leaks/1601710); [DevForum: Best module for memory cleaning in 2025?](https://devforum.roblox.com/t/whats-the-best-module-for-memory-cleaning-in-2025/3987770); [Janitor docs](https://howmanysmall.github.io/Janitor/)

**Physics settings**
- General:
  - Anchor everything that doesn't need simulation.
  - Use adaptive timestepping, where islands step at 240, 120 or 60 Hz. It is "up to 2.5 times" faster. Fixed 240 Hz is for racing, destruction or complex mechanisms.
  - Reduce constraints and self-collision.
  — [improve.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/improve.md); [physics/adaptive-timestepping.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/physics/adaptive-timestepping.md)
- `CollisionFidelity`:
  - Box has the lowest memory. Default and PreciseConvexDecomposition are expensive in CPU and memory.
  - Small anchored parts are "generally safe" as Box.
  - Non-colliding objects should still use Box or Hull, because collision geometry is stored in memory anyway.
  - Find precise meshes with the Explorer filter `CollisionFidelity=PreciseConvexDecomposition`.
  — [improve.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/improve.md)
- Per-part flags:
  - Disable `CanCollide`, `CanTouch` and `CanQuery` on parts that don't need them.
  - `CanTouch` costs per-frame touch-state checks.
  - `CanQuery` is honored only when `CanCollide` is false.
  — [improve.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/improve.md); [assemble-an-asset-library.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/tutorials/curriculums/environmental-art/assemble-an-asset-library.md); [REF classes/BasePart.yaml](https://github.com/Roblox/creator-docs/blob/main/content/en-us/reference/engine/classes/BasePart.yaml)
- Humanoids and NPCs:
  - Disable unused HumanoidStates.
  - Use AnimationController for static NPCs, and run NPC animations on the client.
  - Pool NPCs, and spawn them only near players.
  - Drive procedural motion through `Motor6D.Transform`, not C0/C1.
  - Avoid size or scale changes, which rebuild FastClusters. `updateInvalidatedFastClusters` over 4 ms signals avatar invalidation.
  - Server-side TweenService replicates every frame, causing jitter and traffic, so tween on the client.
  — [improve.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/improve.md)
- `Workspace.ClientAnimatorThrottling` throttles animations of remotely simulated models based on camera visibility, FPS and the number of active animations. — [REF classes/Workspace.yaml](https://github.com/Roblox/creator-docs/blob/main/content/en-us/reference/engine/classes/Workspace.yaml)

### Inferences
- **Cutscene code rules:**
  - Precompute the camera path (spline control points, eased timings) before the shot.
  - Update only `Camera.CFrame`/FOV in `BindToRenderStep(..., Enum.RenderPriority.Camera.Value, ...)` using `dt`.
  - Create no tables or closures per frame; reuse buffers and use `Vector3` math.
  - Do no `WaitForChild` or `Instance.new` bursts inside the shot.
  - Pre-spawn NPCs and props before the fade-in.
- **Native codegen:** native code can't help client-side cinematic code (per the docs and the last known status). Use `@native` only for hot numeric server code, such as server-side procedural generation, pathing math or hit validation, and check `debug.dumpcodesize()`.
- **Agent-friendly per-frame client budget (heuristic, not official):** scripts at or below 2–3 ms in steady state, no single task over about 5 ms, and the remainder left for render and physics. Measure actual usage with the MicroProfiler (§5).

### Gaps
- No 2026 primary source confirms or denies native codegen on clients. The docs still say server-side, and the most recent DevForum statements are from the 2024 preview era.
- No official per-subsystem ms budgets (scripts/physics/render) exist.

## 5. Measurement: MicroProfiler, Developer Console, Script Profiler, Scene Analysis, Stats APIs, quality levels, Studio vs live client, benchmarking

### Takeaway
Measure frame time, not FPS, and attribute it to work (MicroProfiler tags, Stats counters) before fixing anything. An AI agent can automate most of this in Studio through the official MCP server: run Luau in the Client or Server datamodel, read `Stats` counters, call `SceneAnalysisService`, analyze paused MicroProfiler captures, and take viewport screenshots from chosen camera positions. Studio numbers are skewed by Studio itself, by running server and client in one process, and by quality and resolution differences. Final verdicts must come from the live client, ideally on a low-end Android device.

### Cited Findings
**MicroProfiler**
- Frame-bar colors in the MicroProfiler:
  - **Orange:** jobs wall time exceeds render wall time (scripts, physics, animation).
  - **Blue:** render exceeds jobs (object density, movement, lighting).
  - **Red:** render exceeds jobs AND GPU wait exceeds 2.5 ms (object complexity, texture size, effects).
  - "Focus more on frame time than frame color."
  — [microprofiler/index.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/microprofiler/index.md)
- Usage:
  - Open it with Ctrl+F6 (desktop and Studio) per microprofiler/index.md. identify.md and the walkthrough say Ctrl+Alt+F6 (doc inconsistency).
  - Ctrl+P pauses into detailed mode. Ctrl+F jumps to the frame where a given tag was slowest.
  - Threads: Main ("RBX Main"), Workers, and Render ("GPU": Prepare → Perform → Present).
  - Label custom code with `debug.profilebegin(name)` / `debug.profileend()`.
  — [microprofiler/index.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/microprofiler/index.md); [use-microprofiler.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/microprofiler/use-microprofiler.md); [identify.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/identify.md)
- Dumps and profiling sources:
  - Dumps are standalone HTML files in `%LOCALAPPDATA%\Roblox\logs` (Windows) or `~/Library/Logs/Roblox` (macOS).
  - Server profiling runs from the Developer Console's MicroProfiler tab: at most 60 frames, with a delay of up to 4 s.
  - On mobile, turn the MicroProfiler on in Settings, then browse from a PC to `<device-ip>:1338`. It shows 30 frames by default; append `/90` for more.
  — [microprofiler/index.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/microprofiler/index.md)
- Web-UI-only features:
  - X-Ray memory-allocation coloring.
  - CPU and memory flame-graph export.
  - "Combine & Compare" diff flame graphs between dumps, for before/after regression checks. Don't combine dumps from different places.
  — [microprofiler/index.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/microprofiler/index.md)
- Modes: Timers (per-label times and call counts); Counters (memory and instance counts since start); Groups and Threads (web only); Hidden. — [microprofiler/modes.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/microprofiler/modes.md)
- **AI analysis:** Studio Assistant can analyze a paused capture "through the MicroProfiler API". "This functionality also works via the Studio MCP server, so you can integrate MicroProfiler analyses into your own AI agent or agentic loop." — [microprofiler/index.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/microprofiler/index.md)
- Key tags and their advice:
  - `Perform/Present/waitUntilCompleted`: waiting on the GPU; too much is being rendered.
  - `Scene/Id_Opaque`, `Id_Transparent`, `Id_Decals`: render passes.
  - `Scene/Shadows`, `ShadowMapSystem`, `computeLightingPerform`, `LightGridCPU`: lighting and shadows.
  - `Glow`, `ColorCorrection`, `MSAA`, `SSAO`: post-processing.
  - `updateInvalidatedFastClusters`: Humanoids and skinned meshes.
  - `Render/PreRender/RunService.RenderStepped`: client per-frame scripts.
  - `GC`: Luau garbage collection.
  - `Dispatch StreamJob`: reduce the streaming radii.
  - Scope names: `physicsStepped`/`worldStep` (physics), `stepHumanoid`/`stepAnimation`, `ProcessPackets` (incoming network).
  — [tag-table.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/microprofiler/tag-table.md); [improve.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/improve.md)

**Stats service (readable from scripts)**
- Frame timing: `Stats.FrameTime` (client-only, in seconds; 1/FrameTime = FPS), `RenderCPUFrameTime`, `RenderGPUFrameTime`.
- Scene counters: `SceneDrawcallCount`, `SceneTriangleCount`, `ShadowsDrawcallCount`, `ShadowsTriangleCount`, plus `UI2DDrawcallCount` and other UI counters.
- Engine counters: `InstanceCount`, `HeartbeatTime`, `PhysicsStepTime`, `PrimitivesCount`, `MovingPrimitivesCount`, `ContactsCount`, and Data/Physics Send/Receive Kbps.
- Memory:
  - `GetTotalMemoryUsageMb()` comes from the OS, roughly what Task Manager shows.
  - `GetMemoryUsageMbForTag(Enum.DeveloperMemoryTag.X)` and `GetMemoryUsageMbAllCategories()` require `MemoryTrackingEnabled`.
- Deprecated: `HeartbeatTimeMs`, `PhysicsStepTimeMs`.
- Internal-only (`InternalTest` capability): "Harmony" dynamic-quality APIs such as `GetHarmonyQualityLevel`.
— [REF classes/Stats.yaml](https://github.com/Roblox/creator-docs/blob/main/content/en-us/reference/engine/classes/Stats.yaml)
- Memory tags include `GraphicsTexture`, `GraphicsMeshParts`, `GraphicsParts`, `GraphicsSolidModels`, `GraphicsParticles`, `GraphicsTerrain`, `GraphicsSlimModels`, `LuaHeap`, `Animation`, `Sounds`, `PhysicsCollision` and `GeometryCSG`. — [REF enums/DeveloperMemoryTag.yaml](https://github.com/Roblox/creator-docs/blob/main/content/en-us/reference/engine/enums/DeveloperMemoryTag.yaml)

**Scene Analysis (Studio; docs added 2026-04-30)**
- Opened via Window → Performance Summary → Scene Analysis.
- Treemap views: Script memory, Unparented instances, Instance composition, Audio memory, Animation memory, and Triangle composition. Triangle composition breaks triangles and draw calls down by Shadows, Opaque, Transparent, Terrain, Grass, Particles, Sky and UI.
- Its numbers "don't necessarily match what players see on their devices".
- `SceneAnalysisService` (`GetTriangleCompositionAsync`, `GetInstanceCompositionAsync`, `GetScriptMemoryAsync`, `GetUnparentedInstancesAsync`, `GetAnimationMemoryAsync`, `GetAudioMemoryAsync`) "is exposed through the MCP server".
— [scene-analysis.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/scene-analysis.md); [REF classes/SceneAnalysisService.yaml](https://github.com/Roblox/creator-docs/blob/main/content/en-us/reference/engine/classes/SceneAnalysisService.yaml)

**Studio MCP server (docs added 2026-03-04)**
- Tools relevant to measurement:
  - `execute_luau` with `datamodel_type` Edit, Client or Server.
  - `start_stop_play`, `get_studio_state`, `get_console_output`.
  - `screen_capture`, with an optional custom camera position and look-at target.
  - `character_navigation`, `user_keyboard_input`, `user_mouse_input`.
  - A `subagent` tool (types `explore`, `playtest`).
  - `http_get` for Roblox docs, including the performance guides.
- Claude Code is a supported quick-connect client.
— [studio/mcp.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/studio/mcp.md)

**Other tools**
- Developer Console (F9):
  - The Memory tool splits CoreMemory from PlaceMemory.
  - Luau heap snapshots can be compared over time.
  - Server view includes a command bar.
  - Script Profiler samples client or server at 1 kHz (default) or 10 kHz (more precise, more overhead).
  — [studio/developer-console.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/studio/developer-console.md); [studio/optimization/memory-usage.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/studio/optimization/memory-usage.md); [studio/optimization/scriptprofiler.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/studio/optimization/scriptprofiler.md)
- Overlays and dashboards:
  - Performance Stats: Ctrl+Alt+F7.
  - Debug Stats: Shift+Ctrl+F1 through F5. The client summary is Shift+F5 and Render stats Shift+F2 (shortcuts differ slightly between pages).
  - Network simulation in Studio.
  - The Performance Dashboard covers live sessions: client and server memory, FPS, heartbeat and crashes. Investigate crash rates above 2–3%.
  — [identify.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/identify.md); [improve.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/improve.md); [monitor.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/monitor.md)
- Server health:
  - Heartbeat is capped at 60; read Steps Per Sec under Server Jobs → Heartbeat.
  - Server memory is `6.25 GiB + 100 MiB × peak players` (e.g. 30 players is about 9.18 GiB). Keep usage under 50%.
  — [identify.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/identify.md)

**Quality levels and the Frame Rate Manager (FRM)**
- Quality scales:
  - `Enum.QualityLevel` has Automatic plus Level01–Level21. Higher levels raise render distance, shading, geometry and texture resolution, particle limits and post-effect quality; low levels may disable some post effects.
  - The user-saved setting `UserGameSettings.SavedQualityLevel` uses Automatic or 1–10.
- FRM and RenderSettings:
  - The FRM (`RenderSettings.FrameRateManager`: Automatic/On/Off) scales view distance, block count and quality.
  - In Studio, `RenderSettings.EditQualityLevel` applies when FRM is disabled.
  - `RenderSettings.EagerBulkExecution = true` gives scene updates an unlimited budget: every frame looks right, at the cost of an unstable frame rate.
  - All RenderSettings members require PluginSecurity.
- Script access: `UserGameSettings.GraphicsQualityLevel` is RobloxScriptSecurity, so it is not readable by game scripts. `SavedQualityLevel` is readable.
— [REF enums/QualityLevel.yaml](https://github.com/Roblox/creator-docs/blob/main/content/en-us/reference/engine/enums/QualityLevel.yaml); [REF enums/SavedQualitySetting.yaml](https://github.com/Roblox/creator-docs/blob/main/content/en-us/reference/engine/enums/SavedQualitySetting.yaml); [REF classes/RenderSettings.yaml](https://github.com/Roblox/creator-docs/blob/main/content/en-us/reference/engine/classes/RenderSettings.yaml); [REF enums/FramerateManagerMode.yaml](https://github.com/Roblox/creator-docs/blob/main/content/en-us/reference/engine/enums/FramerateManagerMode.yaml); [REF classes/UserGameSettings.yaml](https://github.com/Roblox/creator-docs/blob/main/content/en-us/reference/engine/classes/UserGameSettings.yaml)

**Studio vs live client**
- Official:
  - "Performance stats in Studio are skewed by the Studio application"; view frame rate on the client for accurate numbers.
  - Studio runs server and client together, so memory is much higher, and the device emulator "isn't accurate for memory usage".
  - When evaluating FPS, set Graphics Mode to manual at maximum quality to remove FRM effects.
  - A 60-FPS cap on a strong PC hides a 4 ms vs 16 ms difference. Profile on mobile.
  - Test 10–15 minutes on mobile for thermal throttling.
  — [identify.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/identify.md); [design.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/design.md); [microprofiler/index.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/microprofiler/index.md); [test-on-hardware.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/test-on-hardware.md)
- Community (search summary):
  - Studio carries debugging, plugin and in-process server overhead.
  - Its viewport is smaller than the full-resolution live client, and high-DPI scaling differs, so the two can be GPU-bound differently.
  - NVIDIA's frame limiter or G-Sync settings have capped Studio at about 20 FPS for some users.
  — [DevForum: Performance disparity between Studio and Client](https://devforum.roblox.com/t/performance-disparity-between-studio-and-client/2309725); [DevForum: FPS difference between Studio and Game](https://devforum.roblox.com/t/what-could-be-causing-this-fps-difference-between-studio-and-game/4829901); [DevForum: Studio FPS locked at 10-20](https://devforum.roblox.com/t/roblox-studio-fps-is-locked-at-10-20/4080733)

### Inferences
- **Agent benchmark protocol for a slow scene (e.g. the 35–38 FPS one, about 26–28 ms per frame, roughly 10 ms over budget):**
  1. Start play via MCP and move the camera to a fixed, scripted viewpoint.
  2. Via `execute_luau` in the Client datamodel, sample `Stats` for about 5 s: FrameTime p50 and p99, RenderCPU/GPUFrameTime, Scene/Shadows draw calls and triangles. Also call `SceneAnalysisService:GetTriangleCompositionAsync()` for the per-pass split.
  3. A/B toggle one category at a time and re-sample: local-light shadows off, CastShadow off on small parts, transparent parts and particles hidden, post effects disabled, a district's models hidden.
  4. Rank the deltas, apply the cheapest fix with the largest delta, and confirm visually with `screen_capture`.
  5. Re-verify in the published client at manual max quality, then on a low-end Android device.
- **Stats sampling sketch (untested; verify the units of RenderCPU/GPUFrameTime empirically, since only FrameTime is documented as seconds):**
  ```lua
  local Stats, RS = game:GetService("Stats"), game:GetService("RunService")
  local ft, n, dc, sdc, tri = table.create(600), 0, 0, 0, 0
  local c = RS.PostSimulation:Connect(function()
      n += 1; ft[n] = Stats.FrameTime
      dc += Stats.SceneDrawcallCount; sdc += Stats.ShadowsDrawcallCount; tri += Stats.SceneTriangleCount
  end)
  task.wait(5); c:Disconnect(); table.sort(ft)
  return string.format("n=%d p50=%.1fms p99=%.1fms dc=%d shadowDC=%d tris=%d",
      n, ft[math.ceil(n*0.5)]*1000, ft[math.ceil(n*0.99)]*1000, dc//n, sdc//n, tri//n)
  ```
- **Diagnosing micro-stutters:** record a MicroProfiler capture during the cutscene and look at spike frames. Typical culprits:
  - `GC` spikes, which point to allocation in per-frame code.
  - `Dispatch StreamJob` or ProcessPackets bursts, from content streaming in mid-shot.
  - `computeLightingPerform`/`ShadowMapSystem` during fast camera moves or moving shadowed lights.
  - `updateInvalidatedFastClusters`, from spawning or modifying avatars mid-shot.
  - First-use asset loads.
  If mesh streaming is suspected, A/B `Workspace.MeshStreamingAndImprovedLods` in Studio while that RolloutState toggle still exists.
- **Trailer capture in Studio:** `RenderSettings.EagerBulkExecution = true` (plugin-level) is plausibly useful for recording trailers inside Studio, because every frame looks complete. It is not a player-facing fix.

### Gaps
- The docs do not say which MCP tool exposes MicroProfiler capture data (no dedicated tool appears in the MCP tool list). They also do not say whether SceneAnalysisService works outside Studio sessions.
- The units of `RenderCPUFrameTime`/`RenderGPUFrameTime` are not stated.
- How "quality level 4" for shadows maps onto the user-facing 1–10 slider versus the internal 21 levels is not stated.
- No official guidance on vsync/frame pacing or why a scene might lock near 30–40 FPS in Studio specifically.

## 6. Visual quality: lighting, Atmosphere, Sky, post-processing, PBR/SurfaceAppearance, MaterialVariant, new 2025–2026 features, and how high-fidelity games stay fast

### Takeaway
High-end Roblox visuals now rest on four pieces:
- `Lighting.LightingStyle = Realistic` with `PrioritizeLightingQuality` chosen per art direction. `Lighting.Technology` (Future/ShadowMap/Voxel) is deprecated and no longer script-accessible.
- Environment-driven ambient and specular light, plus Atmosphere for depth and haze.
- A small set of post effects, with ColorGradingEffect for tonemapping.
- PBR SurfaceAppearance or MaterialVariant built on trim sheets.

The engine now scales fidelity automatically ("Harmony", texture streaming up to 4K, mesh streaming, SLIM). The best-looking projects stay fast mainly through asset reuse (trim sheets, packages, tinting), restrained shadows and lights, and limited transparency.

### Cited Findings
**Lighting**
- **`LightingStyle` replaces `Technology`.**
  - `LightingStyle` has two values. `Realistic` is "the most advanced and realistic lighting and shadows Roblox can deliver". `Soft` gives "a flat, retro‑Roblox look".
  - `PrioritizeLightingQuality` chooses whether lighting quality or view distance scales down first. `Soft` with it enabled uses shadow maps instead of voxels.
  - `Lighting.Technology` "has been superseded" by these two. It is now RobloxScriptSecurity for read and write. This deprecation text appeared in the docs on 2025-07-23.
  - `Technology.Compatibility` is deprecated; the replacement is Voxel plus a ColorGradingEffect with the `Retro` tonemapper.
  — [REF classes/Lighting.yaml](https://github.com/Roblox/creator-docs/blob/main/content/en-us/reference/engine/classes/Lighting.yaml); [REF enums/Technology.yaml](https://github.com/Roblox/creator-docs/blob/main/content/en-us/reference/engine/enums/Technology.yaml); [environment/lighting.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/environment/lighting.md); [repo history](https://github.com/Roblox/creator-docs/commits/main/content/en-us/reference/engine/classes/Lighting.yaml)
- Shadow and environment properties:
  - `ShadowSoftness` (0–1, default 0.2) is valid only with Realistic.
  - `EnvironmentDiffuseScale` (default 0) gives sky- and time-dependent ambient light; lower `Ambient`/`OutdoorAmbient` when raising it.
  - `EnvironmentSpecularScale` (default 0) gives environment reflections and is "especially important to make metal look more realistic".
  - `ExposureCompensation` ranges from -5 to 5.
  - Fog properties are hidden when an Atmosphere exists.
  - Deprecated: `Outlines` (the feature was removed) and `ShadowColor` (non-functional).
  — [REF classes/Lighting.yaml](https://github.com/Roblox/creator-docs/blob/main/content/en-us/reference/engine/classes/Lighting.yaml); [environment/lighting.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/environment/lighting.md)
- Local lights: PointLight, SpotLight and SurfaceLight share `Color`, `Brightness` and `Shadows`; Range is clamped to 120 studs. — [effects/light-sources.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/effects/light-sources.md); [REF classes/Lighting.yaml](https://github.com/Roblox/creator-docs/blob/main/content/en-us/reference/engine/classes/Lighting.yaml)

**Atmosphere**
- `Density`: how many particles fill the air.
- `Offset`: low values blend distant objects into the sky "for a seemingly endless and seamless open world"; high values create a horizon silhouette.
- `Haze` and `Color`: tint the air.
- `Glare`: requires Haze above 0.
- `Decay`: requires Haze and Glare.
- Balance Offset against Density. A low Offset can make the skybox show through objects.
— [environment/atmosphere.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/environment/atmosphere.md)

**Post-processing**
- Available effects: Bloom, Blur, ColorCorrection (Brightness, Contrast, Saturation, TintColor), DepthOfField, SunRays and ColorGrading.
  - Effects under `Lighting` apply to all players; effects under `Camera` apply to one player.
  - `ColorGradingEffect.TonemapperPreset` is `Default` (post-2019 look) or `Retro` (pre-2019). Only one ColorGradingEffect, parented to Lighting, is applied.
  - Studio's Editor Quality Level must be high to see some effects.
  — [environment/post-processing-effects.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/environment/post-processing-effects.md); [REF classes/ColorGradingEffect.yaml](https://github.com/Roblox/creator-docs/blob/main/content/en-us/reference/engine/classes/ColorGradingEffect.yaml)
- Post effects have MicroProfiler tags (`Glow`, `ColorCorrection`, `MSAA`, `SSAO`). Low quality levels may disable some post effects entirely. — [tag-table.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/performance-optimization/microprofiler/tag-table.md); [REF enums/QualityLevel.yaml](https://github.com/Roblox/creator-docs/blob/main/content/en-us/reference/engine/enums/QualityLevel.yaml)

**PBR materials**
- SurfaceAppearance basics:
  - It takes up to four PBR maps, plus emissive via `EmissiveMaskContent`, `EmissiveStrength` and `EmissiveTint`.
  - `AlphaMode` options: Overlay (default), Transparency (for lace or netting instead of modeling the geometry), TintMask, Opaque.
  - `Color` tinting is free and saves memory.
  - If both a SurfaceAppearance and a MaterialVariant are set, the SurfaceAppearance's maps win.
  — [art/modeling/surface-appearance.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/art/modeling/surface-appearance.md); [parts/meshes.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/parts/meshes.md)
- Texture streaming and 4K:
  - Textures up to 4096² are supported, and the engine ramps quality to each device's resources.
  - Prefer unique textures over atlases "unless the atlas is applied to batchable parts", because requesting high resolution for one region streams the whole atlas at that resolution.
  - Keep texel density uniform.
  - Per DevForum (search summary), MaterialVariant streaming includes 4K support.
  — [parts/textures-decals.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/parts/textures-decals.md); [texture-specifications.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/art/modeling/texture-specifications.md); [DevForum: Introducing Texture Streaming](https://devforum.roblox.com/t/introducing-texture-streaming/4144855); [DevForum: 4k Texture Rendering](https://devforum.roblox.com/t/4k-texture-rendering/4316229)

**2025–2026 graphics timeline**
- RDC 2025 announced:
  - SLIM, for better LODs with fewer triangles and draw calls.
  - Emissive maps, targeted for late 2025.
  - Up-to-4K textures on capable devices via cloud transcoding, texture streaming and **Harmony**, the system that "monitors each user's available resources every frame" and scales quality.
  — [DevForum: RDC25 – What we announced](https://devforum.roblox.com/t/rdc25-what-we-announced/3920245); [DevForum: Creator Roadmap 2025 RDC Update](https://devforum.roblox.com/t/creator-roadmap-2025-rdc-update/3961527); [GamesBeat](https://gamesbeat.com/roblox-launches-scalable-graphics-for-rendering-more-realistic-and-detailed-worlds-exclusive/); [Roblox newsroom: SLIM](https://about.roblox.com/newsroom/2025/12/introducing-roblox-slim-scalable-lightweight-interactive-models) (search summaries)
- Dated items from the docs repo history:
  - Scene Analysis: 2026-04-30.
  - `MeshStreamingAndImprovedLods`: 2026-04-15.
  - SLIM docs: 2026-07-20.
  - Predictive streaming: 2026-07-30.
  - Frustum streaming: 2026-10-01.
  - Studio MCP: 2026-03-04.
  - "Test on hardware" guide: 2026-06-16.
  — [creator-docs commit history](https://github.com/Roblox/creator-docs/commits/main)

**How Roblox's own showcase projects stay fast**
- *The Mystery of Duvall Drive*:
  - Chose an architectural style specifically to reuse a few materials across many assets.
  - Shared trim maps through packaged SurfaceAppearances.
  - Dropped Color/Roughness/Metalness map resolution "by 1 or 2 times without losing any visual fidelity", and often left Metalness blank.
  - Deleted auto-imported TextureIDs when applying a packaged SurfaceAppearance, to avoid duplicate-texture bloat.
  — [materialize-the-world.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/resources/the-mystery-of-duvall-drive/materialize-the-world.md)
- *Beyond the Dark*: "90% of the architectural elements used a handful of swappable trim sheet sets". Putting several surface treatments in one sheet "improves runtime performance by decreasing object and material draw calls". Modular pieces were packaged. — [beyond-the-dark/building-architecture.md](https://github.com/Roblox/creator-docs/blob/main/content/en-us/resources/beyond-the-dark/building-architecture.md)

### Inferences
- **Suggested "cinematic but scalable" baseline for the isekai world:**
  - `LightingStyle = Realistic`.
  - `EnvironmentDiffuseScale` and `EnvironmentSpecularScale` near 1, with Ambient and OutdoorAmbient lowered.
  - An Atmosphere tuned for aerial perspective. Its low-Offset haze also hides the streaming and LOD frontier during the capital reveal.
  - One ColorGradingEffect, plus subtle Bloom and ColorCorrection.
  - DepthOfField parented to the Camera only during cutscenes, so it is per-player and temporary.
- **PrioritizeLightingQuality:** `false` is the safer default for an open world with vistas. `LightingStyle` and `PrioritizeLightingQuality` carry no NotScriptable tag, so runtime toggling (e.g. `true` for interior cutscenes) appears possible but is untested.
- **City-light alternative:** use emissive SurfaceAppearance maps plus a few non-shadowed lights instead of many shadow-casting PointLights for windows and lamps. This likely gives night-city richness at far lower lighting cost, but should be measured.
- **Reuse rules for the capital:** trim sheets and tinted SurfaceAppearances (memory-free variation), Packages for every repeated module, and built-in materials or MaterialVariants for broad surfaces. Note the 2026 texture-streaming caveat: atlases are only good when applied to batchable (instanced) parts.

### Gaps
- No official per-effect GPU cost numbers (Bloom, DoF, SunRays, Atmosphere), and no official light-count guidance for Realistic lighting.
- Details on new 2026 render features beyond those found (e.g. any new sky or cloud or GI features) were not located. The `Enum.Technology` list contains an undocumented `Unified` value whose meaning is unknown.
- Whether toggling `PrioritizeLightingQuality` or `LightingStyle` at runtime is supported or cheap is not documented.
