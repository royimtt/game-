# Professional-grade asset pipeline for a Roblox game built mostly through Claude Code (3D models, textures/materials, animation, audio) — state as of Oct 1, 2026

Research method note: Roblox's official creator-docs repository was shallow-cloned at commit `578b33e` (dated Oct 1, 2026), so every `raw.githubusercontent.com/Roblox/creator-docs/...` citation below reflects the docs as they stand today. create.roblox.com, devforum.roblox.com, about.roblox.com, elevenlabs.io and mindstudio.ai were blocked by the proxy. For DevForum, press and vendor pages, the findings come from WebSearch result summaries, and they are marked that way where it matters. Abbreviation used below: CD = `https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/`.

---

## Q1. Code-generated assets inside Roblox: Parts/MeshParts, EditableMesh/EditableImage, script-generated textures and skyboxes, SurfaceAppearance PBR, MaterialVariant/MaterialService, terrain. What is the quality ceiling of each?

### Takeaway
Claude can produce real geometry and textures directly from code. The options are Parts/CSG and the new `ProceduralModel`, an `EditableMesh` (max 60,000 vertices and 20,000 triangles), an `EditableImage` (max 1024×1024), and PNGs generated offline (skies, PBR maps, flipbooks). Runtime "editables" have three costs: they are memory-budgeted on clients, they are not replicated, and a published game can only use them after 13+ age verification, ID verification and a dashboard toggle. The production-grade pattern is therefore to generate at edit time and then bake the result into permanent assets. `AssetService:CreateAssetAsync` can do this from plugin context, and Open Cloud uploads can too. Code alone gives a high ceiling for architecture, hard-surface pieces, tiling materials, skies and VFX sheets. It gives a low ceiling for organic characters and creatures.

### Cited Findings
**Tools Claude already has through Studio MCP**
- The Roblox Studio MCP server is now **built into Studio** and runs over stdio. Its tools include:
  - `execute_luau` (Edit, Client or Server datamodel), `multi_edit` and `script_read`
  - `generate_mesh` ("textured 3D mesh from a text prompt"), `generate_material` (custom MaterialVariant) and `generate_procedural_model` ("3D objects built from primitive parts… Supports reference images and custom part schemas")
  - `search_asset` and `insert_asset` for the Creator Store and your own inventory
  - `upload_image` ("Uploads a batch of images **from HTTP URLs** to the Roblox asset server") and `store_image` (loads a local file and returns an image URI for use as a reference image)
  - `screen_capture` (captures the viewport, optionally from a custom camera position), plus play-test and input-simulation tools.
  — [CD studio/mcp.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/studio/mcp.md)
- Roblox's official setup guide for agents pairs **Script Sync (beta)** with the built-in MCP. It names Claude Code explicitly as a supported editor extension — [CD ai/coding-harness.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/ai/coding-harness.md)
- The older open-source `Roblox/studio-rust-mcp-server` is "no longer actively maintained" and points users to the built-in server. Its `run_code` tool executed code "within the Studio plugin's context" — [studio-rust-mcp-server README](https://raw.githubusercontent.com/Roblox/studio-rust-mcp-server/main/README.md)

**Procedural geometry: ProceduralModel and CSG**
- `ProceduralModel` (new) is a parameter-driven Model. A generator module (`OnGenerate`) plus attributes rebuild the content whenever parameters change or the model is resized. It works both at edit time and at runtime, and it integrates with undo/redo, Team Create and the draggers. Procedural models inserted from the Creator Store get `Sandboxed = true` — [CD parts/procedural-models.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/parts/procedural-models.md)
- Assistant allows **50 procedural-model generations per rolling 24 hours** — [CD assistant/guide.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/assistant/guide.md)
- In-game CSG is available through `GeometryService:UnionAsync/SubtractAsync/IntersectAsync`. These calls are asynchronous and can hurt performance, so the docs advise against long series of calls — [CD parts/solid-modeling.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/parts/solid-modeling.md)

**EditableMesh and EditableImage**
- `EditableMesh` "fails by default for published games". To enable it, the creator must be **13+ age verified and ID verified**, then turn on **Enable Mesh / Image APIs** in the Creator Dashboard.
  - Loading existing meshes is permission-gated: the asset must be owned by or shared with the game owner, the Studio user or the player.
  - Clients have "strict client-side memory budgets"; the server, Studio and plugins have unlimited memory.
  - A mesh created from an asset is FixedSize by default.
  - Batch APIs exist for performance.
  - Hard limit: **60,000 vertices and 20,000 triangles**, with quads counting as 2 triangles.
  — [CD EditableMesh.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/EditableMesh.yaml)
- Editable meshes "are not replicated" to other clients. This is stated in the `LoadGeneratedMeshAsync` docs — [CD GenerationService.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/GenerationService.yaml)
- `EditableImage`:
  - Maximum size is **1024×1024** and it cannot be resized.
  - Only **one EditableImage can update per frame** on the display side.
  - It has the same 13+ age, ID-verification and toggle requirement as EditableMesh, and the same memory budgets.
  - When an object referencing it is published through `PromptCreatePlatformContentAsync`, the EditableImage is published as an image.
  — [CD EditableImage.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/EditableImage.yaml)
- `CreateEditableImage` defaults to 512×512 and returns `nil` when the device's editable memory budget is exhausted — [CD AssetService.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/AssetService.yaml)

**Baking generated content into permanent assets**
- `AssetService:CreateAssetAsync` "can only be used in locally loaded plugins and uploads assets without prompting first". It supports four types:
  - `Model`, from any Instance
  - `Plugin`
  - `Mesh`, from an **EditableMesh**
  - `Image`, from an **EditableImage**

  It can also run in the "Open Cloud Luau Execution context" when given a CreatorId — [CD AssetService.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/AssetService.yaml)
- `AssetService:CreateSurfaceAppearanceAsync` builds a SurfaceAppearance at runtime from EditableImages: ColorMap, MetalnessMap, NormalMap, RoughnessMap and **EmissiveMask**. The maps cannot be swapped after creation — [CD AssetService.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/AssetService.yaml)
- `MeshPart.TextureContent` can point at an unpublished EditableImage, and it live-updates as the image changes. `MeshPart.MeshContent` cannot be changed directly by scripts; the docs direct you to use `CreateMeshPartAsync` plus `ApplyMesh` — [CD MeshPart.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/MeshPart.yaml)

**Textures and SurfaceAppearance PBR**
- Texture specifications:
  - Roblox "supports up to **4096×4096**" textures and streams lower mips first, depending on device resources.
  - Suggested sizes: 256² for a 5×5-stud object, 512² for 10×10 studs, 1024² for 20×20 studs.
  - For comparison, Parts display 1024² over an 8×8-stud face, and terrain displays 512² across 8×8 studs.
  - Normal maps must be **OpenGL tangent space**. Roughness, metalness and emissive maps are single-channel 8-bit.
  — [CD texture-specifications.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/art/modeling/texture-specifications.md)
- SurfaceAppearance supports:
  - An emissive mask, with EmissiveStrength and EmissiveTint.
  - AlphaModes **Opaque, Overlay, Transparency** (for lace or netting cut-outs) and **TintMask** (selective recoloring).
  — [CD surface-appearance.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/art/modeling/surface-appearance.md)
- Mesh limits: an individual mesh "can not exceed **20,000 triangles**", and a vertex can be influenced by at most **4 bones** — [CD art/modeling/specifications.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/art/modeling/specifications.md)

**MaterialVariant, MaterialService and terrain**
- Custom materials (`MaterialVariant` in `MaterialService`) are PBR materials that can be applied per part or globally. Terrain is limited:
  - Custom materials reach terrain **only as material overrides**.
  - Terrain materials are **global per place**, so you cannot use several variants of one base material on terrain.
  - `TerrainDetail` customizes the top, side and bottom faces of terrain.
  — [CD parts/materials.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/parts/materials.md)
- `MaterialVariant` properties include `EmissiveMaskContent`, `EmissiveStrength`, `EmissiveTint`, `MaterialPattern` and `StudsPerTile`. `ColorMapContent` "Only supports asset URIs as textures", which means a MaterialVariant cannot use a live EditableImage — [CD MaterialVariant.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/MaterialVariant.yaml)
- `Terrain.Decoration` currently "enables or disables animated grass" on the Grass material only — [CD Terrain.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/Terrain.yaml)

**Skyboxes and VFX textures**
- A skybox is **six images** (SkyboxBk/Dn/Ft/Lf/Rt/Up) that "must be seamless along all edges… when folded into a cube".
  - `SkyboxOrientation` can be animated cheaply.
  - The sun, moon and stars are separate, configurable celestial bodies.
  - A Sky can also serve as a reflection cubemap in ViewportFrames.
  — [CD environment/skybox.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/environment/skybox.md)
- Particle **flipbooks** support 2×2, 4×4, 8×8 or custom layouts; for example, a 1024² sheet in an 8×8 layout gives 64 frames. Frames need transparent spacing because of mip filtering — [CD effects/particle-emitters.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/effects/particle-emitters.md)

**Uploading files generated outside Studio**
- Open Cloud image upload accepts png, jpeg, bmp and tga. Images must be "smaller than 8000x8000 pixels", and uploaded images cannot be updated in place — [CD cloud/guides/usage-assets.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/cloud/guides/usage-assets.md)

### Inferences
- **The best way to use code is to generate at build time and bake.**
  1. Claude builds an `EditableMesh` or `EditableImage` in Studio through `execute_luau`.
  2. It saves the result as a permanent Mesh or Image asset with `CreateAssetAsync`.
  3. The game references the asset IDs.

  This avoids three runtime problems: client memory budgets, the lack of replication, and the ID-verification and toggle requirement for live use. Whether the *built-in* MCP's `execute_luau` runs with the "locally loaded plugin" permissions that `CreateAssetAsync` needs is not documented; the old Rust server ran code in plugin context. Test it once. If it fails, a small local plugin or Open Cloud upload covers the same step.
- **Quality ceilings by technique** (my assessment from the specs above):
  - **Parts, CSG and ProceduralModel:** excellent for modular architecture, the capital-city layout, roads, walls, bridges and stylized or low-poly props. With MaterialVariants and good lighting this reaches "front-page stylized" quality. Weaknesses are instance count (performance) and an inherently boxy silhouette.
  - **EditableMesh** (≤20k triangles): good for mathematically definable forms such as lathed or extruded weapons, crystals, noise-displaced rocks, ribbons and wings, terrain chunks, and parametric magic-circle geometry. UVs have to be computed by code, which works well for planar, cylindrical and box projections. Code cannot reach sculpted organic detail like faces or musculature.
  - **EditableImage** (≤1024², one update per frame): good for runtime decals, minimaps, damage or corruption masks and procedural UI. It is not a hero-texture tool.
  - **Offline procedural PNGs** (Python with numpy and Pillow is a better choice than PowerShell): strong for noise-based PBR maps (stone, sand, rust, grime), gradients, star fields and nebulae, flipbook sheets, and normal maps derived from height. Painterly or photoreal hero textures still need image models or artists.
  - **SurfaceAppearance:** the main quality lever for meshes, with 4K PBR, emissive, TintMask for race and team recolors, and alpha cut-outs.
  - **MaterialVariant:** the highest-leverage lever for Parts and terrain. Repetition can be reduced with the Organic pattern.
  - **Terrain:** global materials per place, plus animated grass.
- **Skybox upgrade path.** The PowerShell-generated sky from the earlier session is the code-only ceiling: gradients, noise and stars. A richer sky can come from either of two routes:
  - Render six 90° camera faces of a procedural Blender sky through Blender MCP.
  - Generate an equirectangular panorama with an AI skybox service (see Q4) and convert it to six faces with a Python script.

  In both cases, check edge seams, then upload through Open Cloud. `upload_image` needs HTTP URLs, so local files go through Open Cloud or the Asset Manager.
- **Visual verification loop.** `screen_capture` lets Claude look at its procedural results from chosen camera angles. That makes iterative art-directing possible, which matters a great deal for code-generated environments.

### Gaps
- Roblox does not publish the numeric client memory budgets for editables.
- It is undocumented whether the built-in MCP's `execute_luau` has the plugin-level security that `CreateAssetAsync` requires, and whether the 50-per-24h procedural-model cap also applies to MCP calls.
- I found no official guidance on the per-device memory cost of 4K SurfaceAppearance maps beyond the "ramps up quality based on device resources" note.

---

## Q2. Blender via MCP (e.g., ahujasid/blender-mcp) and Blender Python: can Claude model, UV, texture, rig and animate in Blender and export FBX/glTF to Roblox?

### Takeaway
Yes for modeling, layout, materials, scripted batch work and export. The blender-mcp server runs arbitrary `bpy` code and exports GLB/FBX. It can also pull Poly Haven, Sketchfab and Poly Pizza assets and call Hyper3D Rodin or Hunyuan3D. Practitioners report the same limits again and again: organic modeling, **rigging and weight painting, and character animation** remain unreliable through a text protocol. Roblox's side of the pipeline is mature: FBX or glTF import with PBR, rigs, skinning and animation; an official Blender upload add-on; and Avatar Auto Setup for automatic rigging and caging.

### Cited Findings
**blender-mcp (now branded "MCP for Blender")**
- Capabilities listed in the README:
  - Scene info, and creating, modifying and deleting objects
  - Applying and creating materials
  - "Run arbitrary Python code in Blender from Claude"
  - Importing **Poly Haven** (CC0 HDRIs, textures, models), **Sketchfab** and **Poly Pizza** assets
  - AI generation through **Hyper3D Rodin** and **Hunyuan3D**
  - **Export of the scene, the selection or named objects to GLB/FBX**
  - A bpy and node API-reference lookup
- Installation: installer scripts, or `uvx mcp-for-blender install-addon`, then enable the add-on and start the server from the N-panel. It supports Claude Desktop and Claude Code. Requirements are Blender 3.0+, Python 3.10+ and uv.
- Warnings in the README:
  - "The `execute_blender_code` tool… **ALWAYS save your work before using it.**"
  - "Sometimes the first command won't go through."
  - Blender's UI freezes during large Poly Haven downloads, so use 1k–2k resolutions.

  — [blender-mcp README](https://raw.githubusercontent.com/ahujasid/blender-mcp/main/README.md)

**Real-world assessments** (search summaries; the pages were blocked or unopened)
- Rigging with weight painting, bone constraints and IK is "not realistic with current MCP capabilities" because these steps involve "too much iterative visual judgement to drive through a text protocol".
- Basic object keyframing works, such as moving or rotating objects.
- The setup is "reliable for primitive shapes, positioning, multi-object scenes and basic materials" but "struggles with intricate organic geometry, precise dimensional specifications and rigging". Best uses are scene layout, basic objects, materials and automating Python tasks.

— [MindStudio: Claude + Blender MCP real-world performance](https://www.mindstudio.ai/blog/claude-blender-mcp-real-world-performance); [Harkness AI](https://www.harknessai.nz/articles/generate-3d-models-claude-blender); [Mixar guide](https://www.mixar.app/blender-agent/blender-mcp-guide) (Mixar sells an alternative, so treat its take as biased)

**Roblox-side pipeline**
- The **Roblox Blender plugin** (official, MIT license) uploads selected meshes or collections "to Roblox using Roblox's Open Cloud API", either as individual assets or as packages. It needs Blender 3.2+. Roblox calls it a reference implementation and accepts bug fixes but no feature PRs. The README does not mention animation or rig support — [Roblox Blender plugin README](https://raw.githubusercontent.com/Roblox/roblox-blender-plugin/main/README.md); [CD roblox-blender-plugin.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/art/modeling/roblox-blender-plugin.md)
- Blender-to-Studio scale settings: for FBX export, set **Apply Scalings = FBX Unit Scale**; on Studio import, set **Scale Unit = Stud** — [CD art/blender.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/art/blender.md)
- Studio's Importer takes `.fbx`, `.gltf` and `.obj`. FBX and glTF support multiple meshes and hierarchies, PBR textures and cages, and 3D import supports "meshes with rigging, skinning, and animation data" — [CD studio/importer.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/studio/importer.md)
- Rig requirements:
  - Bones frozen, with scale 1 and rotation 0
  - Root bone at the origin
  - At most 4 influences per vertex and no influences on the root bone
  - At most 20k triangles per mesh
  — [CD art/modeling/specifications.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/art/modeling/specifications.md)
- **glTF export from Studio (beta)** covers meshes, textures, rigging and skinning, vertex colors, cages and FACS. It does **not** export animation data — [CD gltf-export.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/art/modeling/gltf-export.md)
- **Avatar Auto Setup** turns a Model of MeshParts into a Roblox-ready avatar body, "automating the rigging, caging, and other configurations". A run can take "several minutes", and auto-decimation can be skipped for development avatars — [CD avatar-setup/index.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/avatar-setup/index.md)

### Inferences
- **Where Claude plus Blender is strong.** Everything below is a scripted, deterministic operation, which plays to an agent's strengths:
  - Kitbashing the capital city and the human world from modular pieces (geometry nodes or modifiers)
  - Decimating and splitting meshes to fit the 20k-triangle and 4-influence limits
  - Smart-UV or projection unwrapping
  - **Baking procedural shader networks into PBR maps**: albedo, roughness, metalness, OpenGL normal and emissive, for SurfaceAppearance
  - Batch-exporting FBX or GLB at stud scale
  - Rendering skybox faces and VFX flipbook sheets
- **Where it is weak.** Hero characters for the six races and the guiding entity, organic sculpting, retopology for deformation, weight painting, and keyframed character performance. Here the realistic route is a mix of:
  - AI image-to-3D (Q4) followed by Blender cleanup scripted by Claude
  - **Avatar Auto Setup** or another auto-rigger for rigging and caging
  - Marketplace or commissioned bases
  - A human pass on silhouettes and faces
- **Practical race design.** Keep players on standard R15-compatible bodies and express each race with accessories: wings, horns, tails, elf ears, halos and demon marks, as rigid or skinned MeshParts and SurfaceAppearance TintMask recolors. This preserves reuse of every R15 animation and means the six races do not need six bespoke rigs. Fully custom non-R15 rigs, such as a quadruped dragon form, should be reserved for cutscene-only or NPC models.
- Security: blender-mcp executes arbitrary code. Use version control and save Blender files before every agent session.

### Gaps
- I found no rigorous benchmark of Claude-driven Blender output quality; the evidence is anecdotal blog posts.
- The blender-mcp README summary gave no version number, and I could not confirm whether it currently offers a viewport-screenshot tool for visual feedback.
- I could not confirm whether the official Roblox Blender plugin uploads armatures or animations; its README is silent on this.

---

## Q3. Animations: Roblox pipeline, code-generated KeyframeSequences/CurveAnimations, procedural animation, how top anime combat games do it, realistic AI quality, best hybrid

### Takeaway
Top Roblox anime combat games use **human-keyframed animation, made in Moon Animator 2 and/or Blender, combined with tightly synced particle and beam VFX**, and they often hire dedicated combat animators and VFX artists. Claude can generate `KeyframeSequence` and `CurveAnimation` data programmatically, wire up Animation Graphs and events, and write excellent procedural layers (IK, springs, look-at, recoil, physics joints through the new `AnimationConstraint`). It can also use video-to-animation and third-party text-to-animation tools. Signature attacks and cinematic race-change performances still benefit most from a human animator's polish. Note one breaking change: **R15 player rigs now use `AnimationConstraint` instead of `Motor6D`.**

### Cited Findings
**Roblox animation tools**
- The **Animation Editor** is the primary clip-authoring tool, with keyframes, easing, a curve editor, events, loop and priority settings.
  - *Saving* stores a `KeyframeSequence` in ServerStorage.
  - To use an animation in the game you must *export or publish* it.
  - For group-owned games, select the group as Creator when publishing.
  — [CD animation/editor.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/animation/editor.md)
- The **Animation Graph Editor** (new) is a node-based tool for blend trees and state logic. It creates an `AnimationGraphDefinition` asset that you publish to get an Asset ID. Its parameters are accessible from code and it has replication modes — [CD animation/graph-editor.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/animation/graph-editor.md)
- **Animation Capture**:
  - *Body* (beta, "Live Animation Creator") turns a video of one well-lit person, filmed in a single stable shot under 15 seconds, into R15 keyframes in about a minute.
  - *Face* capture is also in beta.
  — [CD animation/capture.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/animation/capture.md)
- At runtime, `AssetService:PromptImportAnimationClipFromVideoAsync` converts a player-uploaded video into an `AnimationClip` (the player must consent first) — [CD AssetService.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/AssetService.yaml)

**Generating animation data by code**
- `AnimationClipProvider:RegisterAnimationClip` and `RegisterActiveAnimationClip` create *temporary* IDs that "cannot be used outside of Studio", so live games must upload the clip. `KeyframeSequenceProvider` is deprecated and replaced by `AnimationClipProvider` — [CD AnimationClipProvider.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/AnimationClipProvider.yaml)
- `CurveAnimation` stores one curve per channel: `Vector3Curve` for position and `EulerRotationCurve` or `RotationCurve` for rotation. The curves sit in a folder hierarchy that mirrors the Motor6Ds or Bones, and partial or relative hierarchy matching is supported — [CD CurveAnimation.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/CurveAnimation.yaml)
- The Open Cloud Assets API uploads **Animation** assets as `.rbxm` or `.rbxmx`, with the caveat that files "edited outside of Roblox Studio might not upload or function" — [CD usage-assets.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/cloud/guides/usage-assets.md)

**Procedural animation and the joint change**
- **AnimationConstraint replaces Motor6D** in R15 player rigs when `AvatarJointUpgrade` is enabled, which is the default for new experiences.
  - C0, C1, Part0 and Part1 are now *read-only* aliases.
  - Procedural layers should multiply into `.Transform` during `RunService.PreSimulation`.
  - `IsKinematic = false` enables force-based simulation (ragdoll, arm strength).
  - Instead of setting C0 on the server, use client-side evaluation and sync the data.
  — [CD AnimationConstraint.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/AnimationConstraint.yaml)
- The Avatar Joint Upgrade went live for published experiences, and a Phase 2 rollout followed. Roblox's 2026 "Advancing Avatars" plan adds articulation for clavicle, spine, neck, wrists, fingers and toes (search summaries) — [DevForum: AJU now live](https://devforum.roblox.com/t/avatar-joint-upgrade-for-physically-simulated-character-movement-is-now-live/4298561); [DevForum: AJU Phase 2](https://devforum.roblox.com/t/avatar-joint-upgrade-aju-phase-2-rollout-updated-migration-recommendations/4656414); [DevForum: Advancing Avatars](https://devforum.roblox.com/t/action-required-advancing-avatars-on-roblox/4541689)
- `IKControl` adds IK to rigs procedurally, outside the Animation Editor: hand placement, feet on slopes, grabbing objects — [CD animation/inverse-kinematics.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/animation/inverse-kinematics.md)

**Third-party and community tools**
- **Moon Animator 2** (by xSIXx) offers IK, a timeline and linear or Bezier keyframes. An aggregator reports a $29.99 Creator Store price — [The Tools Trunk](https://thetoolstrunk.com/how-much-is-moon-animator/)
- Blender-to-Roblox animation follows two routes (search summaries):
  - The community "Blender rig exporter/animation importer" plugin, which works through the clipboard and is described as more reliable for R15.
  - FBX export with Bake Animation on, Add Leaf Bones off, and Apply Scalings set to FBX Unit Scale.

  One summary claimed an "August 2026 Animation Clip Editor Importer update" with import-time fixes; **this is unverified** — [DevForum: Blender rig exporter/animation importer](https://devforum.roblox.com/t/blender-rig-exporteranimation-importer/34729); [Nilo: Export Blender animations to Roblox](https://nilo.io/articles/export-animation-blender-roblox)
- **AI text-to-animation for R15** is offered by third-party services (vendor claims, not tested):
  - Bloxlab: 0.5–5 s clips, returned as a GLB preview plus an `.rbxmx` KeyframeSequence
  - UGCraft: about 90 s per generation
  - NoCapMocap: includes a Studio plugin

  — [Bloxlab](https://bloxlab.io/tools/roblox-animation-generator); [UGCraft](https://www.ugcraft.ai/creation/roblox-animation-maker); [NoCapMocap](https://www.nocapmocap.com/roblox)

**How top anime combat games produce animation**
- The Strongest Battlegrounds' animations were reportedly made in **Moon Animator 2**, some built in Blender and then polished in Moon Animator 2. This comes from search-result summaries attached to the TSB trailer and its Creator Store listing; **I could not open the pages, so treat it as unverified** — [TSB trailer](https://m.youtube.com/watch?v=-hP1orW_OmE); [TSB OFFICIAL Animations, Creator Store](https://create.roblox.com/store/asset/16072313171/The-Strongest-Battlegrounds-OFFICIAL-Animations)
- Anime battlegrounds projects hire **dedicated combat animators and VFX artists**, often on revenue share. VFX artists build "custom particle effects, beams, and aura systems… aligned with animation timings and hitboxes" (search summary) — [DevForum: Hiring Combat Animator, Jujutsu Annals](https://devforum.roblox.com/t/hiring-combat-animator-jujutsu-annals/4716954); [DevForum: Hiring VFX Artist, Jujutsu Annals](https://devforum.roblox.com/t/hiring-visual-effects-vfx-artist-jujutsu-annals/4713724)

### Inferences
- **What Claude can realistically reach:**
  - **Procedural layers: high quality.** Head and torso look-at, foot IK, lean and tilt, breathing, recoil and hit-reacts as additive Transforms, sine or spring-driven wings, tails and capes, ragdoll on knockout via `IsKinematic=false`, hit-stop, camera shake, and **cutscene camera rails** built from CFrame splines or tweens.
  - **Systems: high quality.** Animation Graph setup, animation events that drive hitboxes and VFX, and priority and weight blending.
  - **Hand-authored keyframe data: low to medium quality.** Claude can write poses as numeric CFrames per joint per time, but it lacks the iterative visual judgement that timing, spacing, arcs, overlap and weight require. `screen_capture` helps somewhat.
  - **Base motion from video or AI tools: medium quality.** Live Animation Creator or text-to-animation services give a usable starting point that then needs cleanup.
- **Best hybrid pipeline:**
  1. Claude builds the combat framework and rig conventions (AJU-safe procedural code), plus placeholder animations, using AI or video capture and procedural layers.
  2. A human animator, commissioned or rev-share, does the *signature* moves and the race-change cutscene keyframes in Moon Animator 2 or Blender.
  3. Claude integrates and tunes everything: events, VFX timing, camera, audio sync.
- **Race-change cutscenes:**
  - Mostly code-driven: camera paths, lighting and post-processing tweens, particle bursts, beam spirals, scaling, dissolve via transparency and emissive ramps, and a mesh or accessory swap at the peak frame.
  - Animator-polished: only the character's body acting.
- **Avoid breaking code:** any procedural script that writes `Motor6D.C0` will fail on AJU rigs. Claude should write Transform-in-PreSimulation code and check for `AnimationConstraint` first.

### Gaps
- There is no primary source (developer interview or post-mortem) for how TSB, Jujutsu Shenanigans and similar games author their animations; my access was limited to search summaries.
- There are no independent quality benchmarks for AI text-to-animation on combat moves.
- The current Animation Editor's FBX-import UI path is not described in today's docs (the Importer docs only say animation data is supported).

---

## Q4. Generative AI for 3D/2D assets in 2026 (Roblox Cube 3D/4D and Studio generators; Meshy, Tripo, Rodin, Hunyuan3D; image models for textures, skyboxes and UI) and how Claude orchestrates them

### Takeaway
Roblox's own generators are now **directly callable by Claude** through the built-in Studio MCP (`generate_mesh`, `generate_material`, `generate_procedural_model`) and through `GenerationService`, which runs Cube 3D/4D: text or image input, multi-part schemas, triangle caps. They are good for props, background filler and functional objects, but not hero assets. For higher fidelity, the strongest route is AI image-to-3D (Rodin, Tripo, Meshy, Hunyuan3D), then Blender cleanup by Claude, then Roblox import. Image models (Gemini, GPT Image, FLUX), driven through MCP servers, can handle concept art, textures and UI, and dedicated skybox generators produce panoramas. Uploads are scriptable through Open Cloud. Licensing tiers differ widely between tools.

### Cited Findings
**Roblox Cube / GenerationService**
- `GenerationService` "enables you to generate 3D objects from text prompts using Roblox's **Cube 3D** foundation model". `GenerateModelAsync` accepts:
  - `TextPrompt` and/or `Image` conditioning
  - `Size`
  - `MaxTriangles` ("Lower values result in more faceted and low-poly generations")
  - `GenerateTextures`
  - A schema: `Car5`, `Body1` or a custom `SchemaDefinition` with named `Groups`

  `GenerateMeshAsync` is "scheduled for future deprecation". `SegmentMeshAsync` splits an existing MeshPart into named parts and runs in Studio only — [CD GenerationService.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/GenerationService.yaml)
- Roblox says generated meshes are "higher fidelity with better overall forms, silhouettes… textures more coherent… less pronounced baked-in lighting". Functional objects, such as drivable cars and flyable planes, come from schemas plus "retargetable" behavior scripts — [CD parts/model-generation.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/parts/model-generation.md)
- 4D generation timeline: announced in March 2025, early access in November 2025, **public (open) beta in February 2026**. Players made more than 160,000 objects during early access — [TechCrunch, Feb 4 2026](https://techcrunch.com/2026/02/04/robloxs-4d-creation-feature-is-now-available-in-open-beta/); [PocketGamer.biz](https://www.pocketgamer.biz/roblox-launches-4d-generation-creation-feature-enters-beta/); [Wikipedia: Cube 3D](https://en.wikipedia.org/wiki/Cube_3D); [Roblox Newsroom, Feb 2026 (blocked, title via search)](https://about.roblox.com/newsroom/2026/02/accelerating-creation-powered-roblox-cube-foundation-model)
- Assistant mesh generation (`/generate_mesh`):
  - Takes text **or** an image, not both in one request.
  - A selected Part acts as a bounding box.
  - The maximum triangle count defaults to **10,000**.
  - Segmentation allows up to **8 parts** and produces four previews before the final model.
  — [CD assistant/guide.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/assistant/guide.md)
- **Texture Generator (beta):**
  - Textures a selected mesh or model from a prompt, with a chosen generation angle.
  - Supports prompt-weight syntax: `++`, `--` and `(word)1.5`.
  - Has an optional **Art Style reference image** with a strength setting.
  - Outputs a **SurfaceAppearance**.
  - Is "best suited for… textures contextual to the asset". For tiling surfaces, use Material Generator.
  — [CD texture-generator.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/studio/texture-generator.md)
- **Material Generator:** produces MaterialVariants from text, with a Studs Per Tile setting and an Organic toggle against repetition. Prompting "grayscale" gives a tintable material — [CD material-generator.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/studio/material-generator.md)

**Quality reports and open-source Cube**
- A 2025 Cube update trained on 3.5M additional assets and raised output tokens from 512 to 1024, giving more detail and cleaner textures. Developer feedback was **mixed** (search summaries):
  - Some called the results "good enough to use in games".
  - Others reported "melted blob" results on detailed or irregular shapes, and topology like "sculpted decimated geometries".
  — [DevForum: Cube 3D model updates](https://devforum.roblox.com/t/beta-cube-3d-model-updates-better-quality-and-bounding-box-control/3828156); [DevForum: Cube 3D tools and APIs](https://devforum.roblox.com/t/beta-cube-3d-generation-tools-and-apis-for-creators/3558947)
- The open-source **Cube** repository:
  - Releases: v0.1 (March 2025), v0.5 (July 2025), and **CubePart** part-controllable generation (May 2026).
  - Needs 16–24 GB of VRAM to run locally.
  - Texture generation is still listed as "upcoming" in the open-source release.
  — [Roblox/cube README](https://raw.githubusercontent.com/Roblox/cube/main/README.md)

**External 3D generators** (sources are vendor or aggregator pages, so treat them as marketing-grade claims)
- **Rodin Gen-2** (Hyper3D): quad-based meshes with proper UVs; holds up when rigged.
- **Tripo**: game-ready meshes of about 20K faces, plus auto-rigging.
- **Hunyuan3D 3.0**: 4K–8K PBR, up to about 1.5M faces; open source and self-hostable.

— [3D AI Studio comparison](https://www.3daistudio.com/blog/rodin-2-5-vs-tripo-vs-hunyuan-3d-comparison); [3D AI Studio APIs 2026](https://www.3daistudio.com/blog/best-3d-model-generation-apis-2026)

**Commercial terms for 3D generators** (stated on a Tripo-owned blog, i.e. a competitor; verify on each vendor's own terms page)
- **Meshy free tier**: output is public under **CC BY 4.0**; private ownership starts on Pro.
- **Tripo free tier**: non-commercial.
- **Rodin**: commercial rights included even on free; you pay credits on download.

— [Tripo blog: AI 3D commercial-use licenses](https://www.tripo3d.ai/blog/ai-3d-commercial-use-license); [Tripo blog on Meshy terms](https://www.tripo3d.ai/blog/meshy-capabilities-and-commercial-terms); [Dupple: Rodin review](https://dupple.com/reviews/rodin-ai)

**2D: image models and skyboxes**
- Community **image-generation MCP servers for Claude Code** cover Gemini ("nano-banana"), OpenAI GPT Image and FLUX. They save the generated files directly into the project — [TamerinTECH/claude-code-generate-images-mcp](https://github.com/TamerinTECH/claude-code-generate-images-mcp); [guinacio/claude-image-gen](https://github.com/guinacio/claude-image-gen); [DEV: multi-provider image MCP](https://dev.to/mimo-3/i-built-an-image-generation-mcp-for-claude-code-gemini-openai-and-flux-in-one-place-4jpj)
- **Blockade Labs Skybox AI**:
  - Exports equirectangular images, **cube maps** and HDRI (exr/hdr) at 1K to 16K, with an API.
  - Paid plans include commercial licensing; the free plan excludes exports.
  — [Blockade Labs API: skybox exports](https://api-documentation.blockadelabs.com/api/skybox-exports.html); [The Rundown: Skybox AI](https://www.therundown.ai/tools/skybox-ai)

**Orchestration and upload**
- The **Open Cloud Assets API** (API key with `x-api-key`; some endpoints are beta) uploads:

  | Asset type | Formats | Limits / notes |
  |---|---|---|
  | Model | FBX, glTF, GLB, rbxm | Uploaded as packages |
  | Image/Decal | png, jpeg, bmp, tga | Under 8000×8000 |
  | Audio | mp3, ogg, wav, flac | Up to 7 min |
  | Animation | rbxm/rbxmx | |
  | Video | mp4, mov | Up to 5 min, up to 4096×2160 |

  Mesh-only upload is restricted to content re-downloaded from Asset Delivery — [CD usage-assets.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/cloud/guides/usage-assets.md)
- Studio's Assistant accepts **BYOK Anthropic, OpenAI and Gemini keys**. Roblox points external agents to its MCP server — [CD assistant/mcp.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/assistant/mcp.md)

### Inferences
- **How Claude orchestrates each class of tool:**
  - **Roblox generators:** called directly as MCP tools. Claude prompts, segments and caps triangles, then uses `screen_capture` to inspect and iterate.
  - **External APIs** (Rodin, Tripo, Meshy, Skybox AI, image models): Claude writes Python or PowerShell clients that read API keys from environment variables, poll the jobs and download GLB, FBX or PNG files. Alternatively it uses existing MCP servers: blender-mcp already wraps Rodin and Hunyuan3D, and the image-generation MCPs wrap the image models.
  - **Post-processing:** Claude runs it in Blender through MCP (scale to studs, split into pieces of 20k triangles or fewer, re-UV, bake PBR, OpenGL normals).
  - **Upload:** through Open Cloud or the Roblox Blender plugin. Claude then uses `insert_asset` and configures SurfaceAppearance and MaterialVariants in Studio.
- **Style consistency** is the biggest quality risk when mixing generators. Mitigations:
  1. Generate a style bible and race concept sheets with one image model first.
  2. Use those images as the conditioning input for image-to-3D and for the Texture Generator's Art Style reference.
  3. Have Claude enforce a fixed palette and roughness ranges through scripts.
- **Synthesis matrix: per-asset-type pipeline at maximum achievable quality**

| Asset type | Claude directly (code) | Claude driving tools | Still needs human or marketplace | Recommended pipeline |
|---|---|---|---|---|
| City and world architecture | Parts, CSG, ProceduralModel, EditableMesh kits | Blender MCP modular kits plus baked PBR; MaterialVariants via `generate_material` | Art direction; landmark hero buildings | Blockout by code, then a Blender-baked modular kit, then MaterialVariants, lighting, and `screen_capture` review |
| Props (filler) | Simple procedural props | `generate_mesh` / Cube with a triangle cap; Texture Generator | Little | Cube first, or Rodin/Tripo when Cube looks melted |
| Hero props and weapons | Weak | Image-to-3D (Rodin/Tripo/Meshy), then Blender cleanup and bake | Human polish recommended | Concept image, then image-to-3D, then Claude cleanup in Blender, then SurfaceAppearance |
| Six player races | Accessory attachment logic, TintMask recolors | Image-to-3D of race parts (wings, horns, tails, ears); Avatar Auto Setup | Silhouettes, faces, rig QA | Standard R15 body plus race accessories; commission or buy hero bases |
| Guiding entity (NPC) | Procedural VFX body: particles, beams, emissive shells | Image-to-3D plus Blender | Strong benefit from an artist | An abstract or ethereal design driven mostly by code and VFX plays to Claude's strengths |
| Tiling materials and terrain | Python noise PBR maps | Material Generator / `generate_material`; image models for albedo, Blender bakes for normals | Little | MaterialVariant per base material, plus TerrainDetail and overrides |
| Skybox | Gradients, stars, nebulae in Python | Skybox AI cube-map export, or Blender-rendered 6 faces | Little | Panorama converted to 6 seamless faces, uploaded via Open Cloud |
| VFX textures | Flipbooks and gradients in Python | Image models for stylized slashes and smoke | Top anime-style VFX artists add finesse | 8×8 flipbooks at 1024², beams and trails; timing driven from animation events |
| UI and icons | Vector or procedural UI in code | Image models via MCP | Logo and key art polish | Image model output, then Claude crops and slices |

### Gaps
- Independent, non-vendor benchmarks of 3D generators for Roblox-style stylized assets are lacking; most comparisons are written by competing vendors.
- It is unconfirmed whether 4D generation has left beta. Today's GenerationService docs carry no beta tag, but the last press coverage (Feb 2026) said "open beta".
- I could not confirm whether the MCP `generate_mesh` exposes the same image-input, bounding-box and max-triangle options as Assistant's `/generate_mesh`.
- I did not quantify how many Claude Pro usage-limit hours a heavy asset-orchestration session consumes.

---

## Q5. Audio/SFX: Creator Store licensing, the new Audio API (AudioPlayer, AudioEmitter, AudioListener, effects, Wires), layering for punchy impacts and cinematic moments, AI sound generation (e.g., ElevenLabs) and its licensing

### Takeaway
For maximum audio quality, combine three things:
- Roblox's licensed Creator Store library: 100k+ professional SFX and music, free but **Roblox-only**.
- Custom AI-generated SFX from ElevenLabs SFX v2 on a **paid** plan: 48 kHz, up to 30 s, seamless loops.
- Proper layering (transient, body, tail) and mixing, implemented in the **new Wire-based Audio API**. It offers per-layer faders, EQ, compressors with **sidechain**, limiters, reverb, pitch-shift, filters and built-in **acoustic simulation** (occlusion, diffraction, reverberation).

Claude can write the entire audio graph and batch-process files. Music and hero sound design still benefit from licensed libraries or a human composer or sound designer.

### Cited Findings
**New Audio API**
- Objects: `AudioPlayer` (plays an asset), `AudioEmitter` (virtual speaker), `AudioListener` (virtual microphone), `AudioDeviceOutput` and `AudioDeviceInput`, `AudioTextToSpeech`, `AudioSpeechToText`. **Wires** carry streams between objects, and effects "non-destructively modify" them — [CD audio/index.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/audio/index.md)
- Effects documented: AudioAnalyzer, Chorus, Compressor, Distortion, Echo, Equalizer, Fader, Flanger, PitchShifter, Reverb, Tremolo — [CD audio/effects.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/audio/effects.md)
- The engine reference also includes AudioFilter, AudioLimiter, AudioGate, AudioChannelMixer and AudioChannelSplitter, and AudioRecorder (each has its own class file in the reference folder) — [CD AudioFilter.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/AudioFilter.yaml); [CD AudioLimiter.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/AudioLimiter.yaml); [CD AudioGate.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/AudioGate.yaml)
- `AudioCompressor` has **Input and Sidechain pins** and ships a sidechain-compression code sample — [CD AudioCompressor.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/AudioCompressor.yaml)
- `AudioEmitter.AcousticSimulationEnabled` gives automatic occlusion ("muffled through walls"), diffraction and reverberation; it also has to be enabled on the AudioListener and in SoundService. Emitters support DistanceAttenuation and AngleAttenuation curves and AudioInteractionGroup — [CD AudioEmitter.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/AudioEmitter.yaml); [CD SoundService.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/SoundService.yaml)
- Clicking an audio asset in the Toolbox inserts a legacy `Sound`, which "don't have the same dynamic functionality as AudioPlayer objects" — [CD audio/assets.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/audio/assets.md)

**Importing audio and its limits**
- Import requirements:
  - You must have the legal rights.
  - Format mp3, ogg, wav or flac.
  - Under 20 MB and at most 7 minutes.
  - Sample rate at most 48 kHz.
  - Mono, stereo, 3.0 or 5.1.
- Monthly limits: **2,000 per 30 days if ID-verified, 100 if unverified**. Songs (not SFX) can appear on the game page if they meet conditions that include ID verification and accepting the Audio Terms.

— [CD audio/assets.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/audio/assets.md). **Conflict:** the Open Cloud guide still says "Up to 100 uploads per month if you're ID-verified, 10 if not" — [CD usage-assets.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/cloud/guides/usage-assets.md)

**Licensed library (Creator Store)**
- More than 100,000 professionally produced SFX and music tracks from audio partners are free to use in Roblox games — [CD audio/index.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/audio/index.md)
- Licensed APM music:
  - Royalty-free **on Roblox only** and may not be downloaded.
  - Up to **250 licensed tracks** per experience.
  - No in-game streaming or music-library products.
  — [Roblox Help: Using Licensed Music](https://en.help.roblox.com/hc/en-us/articles/360000927163-Using-Licensed-Music-on-Roblox); [Audio Upload License Agreement](https://en.help.roblox.com/hc/en-us/articles/23359485439124-Audio-Upload-License-Agreement)

**AI sound generation**
- **ElevenLabs SFX v2**:
  - Text to SFX, 0.5–30 s duration.
  - A `loop` parameter for seamless loops (v2 model only) and `prompt_influence`.
  - **48 kHz** output, up from 44.1 kHz.
  — [ElevenLabs API reference (blocked; via search)](https://elevenlabs.io/docs/api-reference/text-to-sound-effects/convert); [blockchain.news on SFX v2](https://blockchain.news/ainews/elevenlabs-launches-sfx-model-v2-high-quality-ai-sound-effects-with-seamless-looping-and-extended-duration)
- ElevenLabs licensing: the **free plan is non-commercial** and requires attribution; **paid plans include commercial rights** without attribution. These are aggregator summaries; the primary terms page was blocked — [Oakgen](https://oakgen.ai/blog/elevenlabs-free-commercial-use); [ElevenLabs commercial SFX page](https://elevenlabs.io/sound-effects/commercial)
- Mirelo AI offers a free Roblox Studio plugin that generates SFX and publishes them to your account (vendor claim). One comparison names ElevenLabs SFX and Stable Audio as 2026 leaders for clip quality, with ElevenLabs "especially good at punchy, game-style sounds" — [Mirelo Roblox plugin](https://mirelo.ai/plugins/roblox); [Summer Engine](https://www.summerengine.com/blog/ai-sound-effect-generator-for-games)

**Layering technique**
- An impact is built from three layers: a sharp **transient**, a weighty **body** and an atmospheric **tail**. Each layer should occupy its own frequency range. Aligning the transients maximizes punch, and staggering them changes the character of the hit. Compressing the transient and adding reverb to the tonal part produces "impact and depth" — [SFX Engine: impact sound guide](https://sfxengine.com/blog/impact-sound-effect); [Get That Pro Sound: layering](https://getthatprosound.com/sound-design-techniques-tools-series-10-key-ways-and-best-plugins-part-3-layering-plugins/)

### Inferences
- **Recipe for punchy hits in the new Audio API**, all written by Claude:
  1. Per hit, use 2–3 `AudioPlayer`s (transient "crack", low "thump" body, short tail).
  2. Give each its own `AudioFader`, then route them through a shared `AudioEqualizer`, then an `AudioCompressor`, then the character's `AudioEmitter`.
  3. Randomize pitch and volume by about ±5–10% per hit.
  4. Pair the hit with hit-stop and camera shake.
- **Bus structure:**
  - Route combat SFX into the **Sidechain** of a music-bus compressor so music ducks under big hits.
  - Put an `AudioLimiter` on the master bus.
- **Cinematic race change:**
  - Tween a low-pass `AudioFilter` sweep plus an `AudioPitchShifter` riser.
  - Swell an `AudioReverb`.
  - At the transformation, drop the music bus to silence, then hit a layered boom.
  - Turn on acoustic simulation for city and indoor spaces.
- **Claude's own audio abilities:**
  - It can synthesize simple UI blips and whooshes procedurally (Python with numpy).
  - It can batch-process files with ffmpeg or sox: trim, fade, loudness-normalize, convert to 48 kHz.
  - Organic and complex SFX are better from ElevenLabs on a paid plan or from the Creator Store.
  - Music is best taken from the licensed Creator Store library, or commissioned for main themes.
- Upload through Open Cloud. Even the stricter 100-per-month interpretation of the limit means SFX should be batched and planned.

### Gaps
- The ID-verified upload limit is contradictory between two official doc pages (2,000/30 days vs 100/month).
- I did not research AI *music* generators (Suno, Udio, ElevenLabs Music) or their licensing for Roblox use.
- ElevenLabs' primary terms page could not be fetched; the licensing claims come from secondary summaries.

---

## Q6. Moderation, licensing and IP safety for uploaded or generated assets on Roblox

### Takeaway
Every uploaded mesh, image, audio file and animation passes Roblox's automated and human moderation. The developer is **fully responsible for third-party AI outputs**. Rights holders can file removals through Rights Manager or DMCA. In the US, raw AI output may not be copyrightable without meaningful human authorship. For an isekai and anime-inspired game, the main risks are look-alike IP, generator licence tiers (free tiers can be public or non-commercial), and maturity labeling for demons and combat.

### Cited Findings
- On generative AI:
  - Roblox APIs (`GenerationService`, `TextGenerator`) moderate inputs and outputs.
  - **With third-party tools "you are responsible for the content delivered to users, even if it is AI-generated"**, and outputs must match the game's Content Maturity.
  - In-game generative interactions must be disclosed in the Content Maturity questionnaire.
  - Extended AI chat requires a Restricted (18+) label.
  — [CD generative-AI.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/generative-AI.md)
- Asset moderation is "both human and automated… proactive and reactive" and covers the Community Rules, Terms of Use and DMCA. Assets still in the queue stay invisible in published games. "Roblox may take down games and/or terminate accounts that maliciously import or publish non-compliant assets" — [CD projects/assets/index.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/projects/assets/index.md)
- `GenerationService` returns a "Moderation failed" error for flagged prompts — [CD GenerationService.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/GenerationService.yaml)
- **Rights Manager** lets any rights holder, even one with no Roblox presence, request removal of games, assets and avatar items, with up to 250 links per request — [CD rights-manager.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/production/publishing/rights-manager.md)
- Creator Store assets must comply with the Community Rules, Terms of Use and DMCA — [CD production/creator-store.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/production/creator-store.md)
- Imported audio requires "the legal rights to that audio asset" — [CD audio/assets.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/audio/assets.md)
- The Editable APIs require **13+ age verification and ID verification**, plus a review of the Terms of Use, before they work in published games — [CD EditableMesh.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/EditableMesh.yaml)
- US Copyright Office (Part 2 report, January 2025): prompts alone "do not provide sufficient human control". Protection attaches only to human-determined expressive elements, such as a human's own perceptible input or creative arrangements and modifications. AI elements inside a larger human-authored work do not void protection of the whole — [copyright.gov NewsNet 1060](https://www.copyright.gov/newsnet/2025/1060.html); [Jones Day analysis](https://www.jonesday.com/en/insights/2025/02/copyrightability-of-ai-outputs-us-copyright-office-analyzes-human-authorship-requirement)
- Licence tiers of the generators (secondary sources; see Q4 and Q5):
  - Meshy free: public CC BY 4.0
  - Tripo free: non-commercial
  - Rodin: commercial use even on free
  - ElevenLabs free: non-commercial
  - Skybox AI free: no exports
  — [Tripo blog](https://www.tripo3d.ai/blog/ai-3d-commercial-use-license); [Oakgen](https://oakgen.ai/blog/elevenlabs-free-commercial-use); [The Rundown](https://www.therundown.ai/tools/skybox-ai)
- Poly Haven assets imported through blender-mcp are CC0 — [blender-mcp README](https://raw.githubusercontent.com/ahujasid/blender-mcp/main/README.md)

### Inferences
- **IP checklist for this game:**
  1. Keep designs original for all six races and the guiding entity. Avoid names, silhouettes, color schemes and signature abilities that echo specific isekai or anime properties (DMCA and Rights Manager exposure).
  2. Never upload copyrighted music or SFX rips.
  3. Prefer Creator Store licensed audio.
  4. Pay for commercial tiers *before* generating final assets. On Meshy's free tier, output is public CC BY, so competitors could legally reuse your models.
  5. Check Sketchfab model licences one by one; Poly Haven CC0 assets are safe.
  6. Keep a **provenance log** per asset: tool, plan tier, date, prompt and source image, plus a note of human edits. This supports takedown disputes and strengthens copyright claims, because human edits and arrangements are what protection attaches to.
- **Moderation hygiene:**
  - Demon and dark-magic imagery, blood and gore in VFX can trip moderation or raise the maturity label. Answer the Content Maturity questionnaire honestly about violence and fear themes.
  - Test-upload borderline textures early.
  - Inspect any free Creator Store model for scripts before insertion. The MCP `insert_asset` makes inserting easy, so the inspection step matters more.
- Static AI-made art, such as textures or meshes created with external tools, does not need an in-game "AI" disclosure under the current page. Only *in-game* generative interactions trigger the disclosure rules.

### Gaps
- I found no Roblox-specific statistics on moderation false positives for AI-generated textures or meshes.
- I found no official Roblox statement on whether AI-generated static assets need disclosure beyond the generative-interaction rules.
- Primary licence pages for Meshy, Tripo and Rodin were not fetched; only secondary summaries were. Each vendor's current terms should be checked before purchase.
