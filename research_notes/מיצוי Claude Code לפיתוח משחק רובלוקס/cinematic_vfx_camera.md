# Cinematic VFX, Camera Work, Cutscenes and "Game Feel" in Roblox: A Technique Library for an AI Agent

> Research date: 2026-10-01. Network note: create.roblox.com, devforum.roblox.com, youtube.com, gdcvault.com, ssbwiki.com and most blogs could not be fetched (egress-blocked). Roblox API facts below come from the **Roblox/creator-docs GitHub source** (raw.githubusercontent.com). Open-source module facts come from **source code and READMEs fetched from GitHub**. DevForum, YouTube and blog facts are cited from **WebSearch result summaries** (the URL is the result that produced the summary). Treat those as lower confidence: they are paraphrased by the search tool and were not read directly.

## Q1. Roblox VFX building blocks and pro techniques (ParticleEmitter, Beam, Trail, mesh VFX, Highlight, Neon/lights, post-processing), how top anime battlegrounds games build effects, and the tools VFX artists use

### Takeaway
Pro Roblox VFX is built in layers. Each layer is a cheap primitive: flipbook/Squash ParticleEmitters fired with `:Emit()` bursts, Beams (Bézier, scrolling textures) and Trails, tweened meshes with scrolling `Texture` offsets, pre-created Highlights, and post-processing on the **Camera**, which affects only the local player. Battlegrounds games add rock/debris modules, glass-sphere distortion and impact frames made from ColorCorrection plus Highlight. They play every effect **on the client**. Several API facts have changed recently. The Highlight cap is now **255** (current docs). `FlipbookFramerate` maxes at **30 fps**. `LightInfluence` defaults differ between Studio-insert and `Instance.new`. Glass refraction does not render on mobile.

### Cited Findings

**ParticleEmitter (current API)**
- Current properties: Acceleration, Brightness, Color, Drag, EmissionDirection, FlipbookBlendFrames, FlipbookFramerate, FlipbookIncompatible, FlipbookLayout, FlipbookMode, FlipbookSizeX/Y, FlipbookStartRandom, Lifetime, LightEmission, LightInfluence, LockedToPart, Orientation, Rate, Rotation, RotSpeed, Shape, ShapeInOut, ShapePartial, ShapeStyle, Size, Speed, SpreadAngle, Squash, Texture/TextureContent (asset URIs), TimeScale, Transparency, VelocityInheritance, WindAffectsDrag, ZOffset. Methods: `Emit(count)` ("instantly emit the given number of particles") and `Clear()`. **`VelocitySpread` is deprecated**; use SpreadAngle. — [ParticleEmitter.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/ParticleEmitter.yaml)
- `FlipbookLayout` accepts None, Grid2x2 (4 frames), Grid4x4 (16), Grid8x8 (64) or Custom (FlipbookSizeX/FlipbookSizeY). `FlipbookMode` accepts Loop, OneShot, PingPong or Random. In **OneShot**, `FlipbookFramerate` is ignored and the frame rate becomes Lifetime ÷ frame count, which the docs suggest "such as an explosion that creates a puff of smoke and then fades out." `FlipbookBlendFrames` crossfades linearly between frames. — [ParticleEmitter.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/ParticleEmitter.yaml)
- The particle guide says `FlipbookFramerate` can be a min/max range "with a maximum of 30 frames per second". A sample 1024×1024 texture holds an 8×8 (64-frame) flipbook. Leave transparent spacing between frames because "mip filtering might require even more spacing." Flipbooks cost memory, and "clients automatically deactivate flipbooks when they are low on memory, which is likely for older mobile phones." Reusing textures costs less memory than unique ones. `FlipbookStartRandom` with framerate 0 gives each particle a random static frame. — [particle-emitters.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/effects/particle-emitters.md)
- Hard limits from the same guide: particle lifetime is capped at **20 s**. One emitter can create **up to 400 particles/s (100/s on mobile)**. Particle size costs GPU fill-rate. Overlapping transparent particles cause overdraw. — [particle-emitters.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/effects/particle-emitters.md)
- `LightEmission`: 0 = normal blending, 1 = **additive** blending. It does *not* light the environment; use a PointLight for that. `LightInfluence`: 0 = particles ignore environmental light (full brightness), 1 = fully lit (black in darkness). **The default is 1 when inserted with Studio tools and 0 when created with `Instance.new()`.** `Brightness` scales emitted light when LightInfluence is 0. — [ParticleEmitter.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/ParticleEmitter.yaml)
- For grayscale textures with no alpha channel, the guide recommends LightEmission = 1 to hide the dark regions. — [particle-emitters.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/effects/particle-emitters.md)
- `Squash` is a NumberSequence for non-uniform scale over the particle's lifetime. Values >0 make particles thinner and taller; values <0 make them wider and flatter. — [ParticleEmitter.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/ParticleEmitter.yaml)
- `ZOffset` moves particles toward (+) or away from (−) the camera in studs without changing their on-screen size. It accepts fractions and is used to control draw order. Strongly negative values can hide particles inside the parent part. — [ParticleEmitter.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/ParticleEmitter.yaml)
- `LockedToPart` makes particles move rigidly with their emitter. VelocityInheritance = 1 is the alternative. Orientation modes are FacingCamera, FacingCameraWorldUp, VelocityParallel and VelocityPerpendicular. `TimeScale` runs from 0 to 1, where 0 "freezes in time". `Drag` is the half-life in seconds of particle speed (exponential decay); negative values make particles accelerate. `ShapeInOut` sets outward, inward or both directions. — [ParticleEmitter.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/ParticleEmitter.yaml)

**Beam and Trail**
- A Beam is a Bézier curve between Attachment0 and Attachment1. `CurveSize0` and `CurveSize1` place the 2nd and 3rd control points. The appearance is controlled by `Segments`, `Width0`/`Width1`, `TextureMode`, `TextureLength`, `TextureSpeed` (scrolling) and `FaceCamera`. `ZOffset` is in studs relative to the camera. LightEmission, LightInfluence and Brightness work as on emitters. `SetTextureOffset()` sets the scroll phase. — [Beam.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/Beam.yaml)
- A Trail draws between two moving attachments. Its key properties are `Lifetime` (seconds per segment), `MinLength`/`MaxLength`, `WidthScale` (NumberSequence over lifetime), `TextureMode`, `FaceCamera`, Transparency and Color over lifetime, and `Clear()`. — [Trail.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/Trail.yaml)

**Mesh-based VFX, materials and textures**
- A `Texture` has `OffsetStudsU`/`OffsetStudsV` (offset in studs) and `StudsPerTileU`/`V` (tile size), which makes scrolling surfaces possible. — [Texture.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/Texture.yaml)
- Community practice (search summary): tween `OffsetStudsU` and `StudsPerTileV` with TweenService to animate surfaces. For animated slash meshes, keep **multiple mesh instances** instead of swapping the texture rapidly on one mesh, which causes rendering issues. — [DevForum: Special Mesh texture not rendering properly](https://devforum.roblox.com/t/special-mesh-texture-not-rendering-properly/3234952); [Textures and decals docs](https://create.roblox.com/docs/parts/textures-decals)
- Glass material: "Refraction of light through the glass material is **not supported on mobile devices** due to computational limitations." — [materials.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/parts/materials.md)
- "Mesh flipbooks" are prebaked mesh sequences, the mesh equivalent of particle flipbooks. They are offered as community packs and take considerable time to bake and import. — [DevForum: Open-Source Mesh Flipbook Pack](https://devforum.roblox.com/t/open-source-mesh-flipbook-pack/3635032)

**Highlight**
- Current limit: "Studio only displays **255** simultaneous Highlight instances on the client-side at a time". Extras are silently ignored. Properties: Adornee, DepthMode (AlwaysOnTop / Occluded), Enabled, FillColor, FillTransparency, OutlineColor, OutlineTransparency. — [highlighting.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/effects/highlighting.md); [Highlight.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/Highlight.yaml)
- Performance rules from the docs:
  - **Adding or removing a Highlight "can cause a geometry rebuilding step that might lead to performance spikes"**. Changing its properties (including Enabled) is lightweight.
  - Do not nest highlighted objects inside other highlighted objects.
  - **The first Highlight on screen costs up to 1 ms of GPU on mobile**. Additional highlights cost little.
  - On mobile, cost grows with screen coverage.
  - Disabled or fully transparent highlights cost nothing.
  
  — [highlighting.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/effects/highlighting.md)

**Post-processing and Atmosphere**
- The available effects are BloomEffect, BlurEffect, ColorCorrectionEffect, DepthOfFieldEffect, SunRaysEffect and **ColorGradingEffect** (TonemapperPreset `Default` = post-2019 vivid look, `Retro` = pre-2019). Effects under **Lighting show to all players**. Effects under **Camera show only to that player**. Some effects are hidden at low Studio editor quality. — [post-processing-effects.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/environment/post-processing-effects.md)
- ColorCorrectionEffect:
  - `Brightness` −1 = all pixels black, +1 = all pixels white.
  - `Contrast` <0 reduces contrast and >0 increases it.
  - `Saturation` −1 = fully desaturated, >1 = more vivid.
  - `TintColor` multiplies the RGB channels.
  
  — [ColorCorrectionEffect.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/ColorCorrectionEffect.yaml)
- Bloom has `Intensity`, `Size` (radius in pixels) and `Threshold` (1 = only pure white blooms, 0 = everything blooms). Blur `Size` is a pixel radius. DepthOfField has `FocusDistance` (studs), `InFocusRadius` (studs either side), `NearIntensity` and `FarIntensity`. SunRays has `Intensity` and `Spread`, both 0–1. — [BloomEffect.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/BloomEffect.yaml); [BlurEffect.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/BlurEffect.yaml); [DepthOfFieldEffect.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/DepthOfFieldEffect.yaml); [SunRaysEffect.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/SunRaysEffect.yaml)
- Atmosphere:
  - `Density` hides objects and terrain, not the skybox itself.
  - `Offset`: raise it "to create a horizon silhouette against the sky" or lower it "to blend distant objects into the sky". A low offset can cause "ghosting".
  - `Haze` adds haziness. `Glare` is the sun glow and needs Haze > 0.
  - `Color` and `Decay` set the hue toward and away from the sun.
  
  — [Atmosphere.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/Atmosphere.yaml)
- Rendering-performance notes:
  - Decals, textures and particles "don't batch well and introduce additional draw calls".
  - "Property changes to ParticleEmitters can have a dramatic impact on performance."
  - Layered transparency causes overdraw.
  - Dense shadow-casting lights are expensive.
  
  — [performance-optimization/improve.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/performance-optimization/improve.md)

**How top anime battlegrounds games build effects (community evidence, search summaries)**
- The Strongest Battlegrounds (TSB)-style effects use **glass spheres** for light-warping distortion, plus **rock/debris modules** for ground destruction. A recommended architecture stores an ability's effects in a table on the server, sends the table to the client, and the client plays them all. — [DevForum: How did the creator of Strongest Battleground create this effect?](https://devforum.roblox.com/t/how-did-the-creator-of-strongest-battleground-create-this-effect/2730449); [DevForum: Rock Module based on Battlegrounds game](https://devforum.roblox.com/t/rock-module-based-on-battlegrounds-game/2894908); [DevForum: Optimization for heavy VFX/Parts fighting games](https://devforum.roblox.com/t/optimization-for-heavy-vfxparts-fighting-games/3824000)
- Paired cinematic moves (e.g., a TSB-inspired "20-20-20 dropkick" effect by an artist called Pew) are animated with **two rigs placed at the same CFrame**, named e.g. "Player" and "Opponent", in one animation file. This comes from a search summary; attribution to this exact thread is likely but unverified. — [DevForum: RUNUP – VFX breakdown part 4](https://devforum.roblox.com/t/runup-vfx-breakdown-part-4/3669430)
- The common Roblox impact-frame recipe runs **speed-line particles → black ColorCorrection → white Highlight on the player → more particles**. Variants swap Lighting/ColorCorrection between black and white, or raise saturation. One tutorial builds an anime impact frame "using only one LocalScript and a ColorCorrectionEffect." TSB is cited as the popularizer. — [DevForum: Advanced impact frames](https://devforum.roblox.com/t/advanced-impact-frames/2468478); [YouTube: How to Make Impact Frames in Roblox Studio](https://www.youtube.com/watch?v=8XsfwlHTmZY); [DevForum: How do I make these type of impact frames](https://devforum.roblox.com/t/how-do-i-make-these-type-of-impact-frames-and-what-programs-do-people-use-to-make/3539568)
- Chromatic-aberration fakes:
  - (a) Use three ViewportFrames (R, G, B), tinted, transparent, offset by a few pixels, with CurrentCamera = workspace.CurrentCamera.
  - (b) Use three ColorCorrectionEffects tinted R, G and B.
  
  For dash/speed screen effects, overlay an animated spritesheet ImageLabel and cycle `ImageRectOffset`. — [DevForum: How to Create Chromatic Aberration Effect](https://devforum.roblox.com/t/how-to-create-chromatic-aberration-effect/3119178); [DevForum: chromatic aberration #2](https://devforum.roblox.com/t/how-do-i-make-chromatic-aberration-effect/2394934/2); [DevForum: dash/speed screen effect](https://devforum.roblox.com/t/how-would-i-go-about-making-a-dashspeed-screen-effect/1669992)
- Jujutsu Shenanigans: I found only community asset packs (e.g., "Jujutsu Shenanigans VFX Mesh IDs"), not developer breakdowns. — [Creator Store: JJS VFX Mesh IDs](https://create.roblox.com/store/asset/122937767206848/Jujutsu-Shenegians-VFX-Mesh-IDs)

**Plugins and external tools Roblox VFX artists use (search summaries)**
- **VFX Suite**: works on ParticleEmitters, Beams and Trails. It has "Better Emit" and "Emit Delay", a Sequence Copier, and a Bézier graph editor with presets. — [DevForum: Introducing the VFX Suite Plugin](https://devforum.roblox.com/t/introducing-the-vfx-suite-plugin/2545686)
- **Ros Particle Editor** edits Size/Transparency/Squash across many emitters with no size/squash limits. **VFX Designer** is a graph editor for smooth curves. **Jad's Emit Plugin** pops up on selecting an emitter, beam or mesh. **CIX Library** offers 600+ free particles. **SteakParticles** is paid, at 200 Robux. **Voxel Particles Plugin** is open source on GitHub. **VFX Forge** is described as "an advanced custom VFX system". A search summary also mentions plugins that import and upload mesh and beam flipbooks, but did not name the plugin, so it may not be VFX Forge. — [DevForum: Best Particle Editor Plugin](https://devforum.roblox.com/t/the-worlds-best-particle-editor-plugin-99-sure/1668424); [DevForum: VFX Designer Plugin](https://devforum.roblox.com/t/vfx-designer-plugin/2092568); [DevForum: Jad's Emit Plugin](https://devforum.roblox.com/t/dear-vfx-makers-i-present-to-you-jads-emit-plugin/1986838); [DevForum: CIX Library](https://devforum.roblox.com/t/over-600-free-particle-with-cix-library-a-particle-library-plugin/2864815); [DevForum: SteakParticles](https://devforum.roblox.com/t/steakparticles-plugin-for-creating-vfx-and-particle-emitters/2908779); [GitHub: Voxel-Particles-Plugin](https://github.com/WildCake/Voxel-Particles-Plugin); [DevForum: VFX Forge](https://devforum.roblox.com/t/plugin-vfx-forge-an-advanced-custom-vfx-system/3867553)
- External tools:
  - **Blender** builds slash meshes (simple-deform circles, then Voronoi and gradient shaders).
  - **EmberGen** (JangaFX) gives real-time volumetric fire/smoke simulation with fast flipbook export.
  - **Photopea** removes black backgrounds from rendered sprite sheets.
  
  — [DevForum: Animated Slash Effects with only Blender](https://devforum.roblox.com/t/how-to-make-animated-slash-effects-with-only-blender/1794034); [JangaFX EmberGen](https://jangafx.com/software/embergen)
- Roblox's public roadmap lists **"2D particles"** for UI surfaces (sparks, smoke, fireworks in screen space) for **late 2026**. This is a roadmap item, not shipped as of the search. — [Roblox Creator Roadmap](https://create.roblox.com/updates/roadmap)

### Inferences
- **Layered anatomy of an anime-style hit**: combine 6–8 cheap layers rather than one heavy emitter. These are my synthesis of the cited primitives:
  1. Anticipation: charge particles pulled inward (`ShapeInOut` = inward, or negative Speed) plus a small glow.
  2. Core flash: one large particle or OneShot flipbook with LightEmission 1, LightInfluence 0 and a lifetime of about 0.08–0.15 s.
  3. Shockwave: a mesh ring tweened from scale ≈0.2→3 while transparency goes 0→1 over about 0.25–0.35 s with an Out easing, or a Beam ring with scrolling texture.
  4. Sparks/streaks: Orientation VelocityParallel, Squash >0 for streak stretching, Drag ≈0.1–0.2 s half-life so they "snap" then hang.
  5. Smoke/debris: LightInfluence ≈1 so it sits in scene lighting, lifetime 0.6–1.5 s, plus a rock module.
  6. Screen layer: impact frame, shake, FOV punch, hitstop (see Q2).
  7. Linger: embers and ground scorch decals fading over 2–4 s.
  
  All numbers are starting points to tune, not sourced constants.
- **Energy vs. matter rule:**
  - Energy (auras, flashes, beams) uses LightEmission ≈0.5–1 and LightInfluence 0 so it glows at night.
  - Matter (dust, rocks, smoke) uses LightEmission 0 and LightInfluence ≈1 so it reads as physical.
  
  This follows directly from the documented blending semantics.
- **MCP/agent pitfall:** emitters created by script (`Instance.new`, which is how an agent working through an MCP server often builds them) default to LightInfluence 0, while Studio-inserted ones default to 1. An agent must **set LightInfluence explicitly** or effects will look inconsistent between hand-made and generated assets.
- **Six race colors:** additive blending (LightEmission 1) on bright scenes drives colors toward white. The **white race** therefore needs value contrast: darken the background briefly (ColorCorrection Brightness −0.1 to −0.3 during its moments) and use a faintly tinted white (warm or cool) with a dark-edged ColorSequence. Bloom `Threshold` should stay high (≈0.9+) so only the intended cores bloom. **Yellow and green** lose saturation fastest under additive blending, so give them a more saturated ColorSequence midpoint. **Purple and blue** read darker, so raise Brightness (with LightInfluence 0).
- **Highlights**: create one Highlight per character, and per major VFX model, at spawn. Toggle `Enabled` and colors at the moment of use; never `Instance.new`/`Destroy` a Highlight at an impact peak. The 255 cap is generous, so the real cost is the add/remove rebuild spike and the ~1 ms mobile GPU cost of the first visible one.
- **Glass-sphere distortion** (TSB-style) shows nothing on mobile because refraction is unsupported there. Pair it with a fallback layer (e.g., a faint white shockwave ring) that carries the effect on phones.
- **Flipbooks**: author 8×8 at ≤1024² with padding and reuse one texture across race variants by tinting `Color`. This avoids six unique textures, given the documented low-memory auto-disable and the 30 fps framerate ceiling.

### Gaps
- No primary breakdowns (GDC-style talks or official devlogs) from TSB, Jujutsu Shenanigans, Blox Fruits, Deepwoken or Type Soul VFX teams were found. The battlegrounds evidence is DevForum and community material seen only through search summaries.
- The DevForum impact-frame recipe implies a white Highlight stays visible over a black ColorCorrection. Whether Highlights render after post-processing is not documented in what I could read, so verify in Studio.
- Exact draw-call or GPU costs per Beam, Trail or emitter are not documented.

## Q2. Game feel / "juice": trauma screen shake, hitstop, impact frames, FOV punches, slow motion, springs, speed lines, chromatic aberration, anticipation/follow-through, easing (durations and magnitudes)

### Takeaway
Use **Eiserloh's trauma model**: trauma ∈ [0,1], it decays linearly, shake = trauma² (or ³) times *smooth noise*. In 3D use **rotation, not translation**. Add **hitstop** (freeze both parties). Fighting-game references put it at roughly 8–15 frames at 60 fps (≈130–250 ms) per hit, and Smash caps it at 30 frames (0.5 s). Make the victim shake more than the attacker. Add **single high-contrast impact frames**, **frame-rate-independent smoothing** (`1−e^(−k·dt)`, `TweenService:SmoothDamp`, or springs) and **anticipation → fast action → slow settle** timing. Roblox has no global time scale, so slow motion must be orchestrated per system.

### Cited Findings

**Canon and definitions**
- Steve Swink defines game feel as "Real-time control of virtual objects in a simulated space, with interactions emphasized by polish." Polish is "all of the additional work, like art, sound, or animations" that sells that control. — [Wikipedia: Game feel](https://en.wikipedia.org/wiki/Game_feel); [Swink ch.1 PDF](http://mycours.es/gamedesign2014/files/2014/10/Game-Feel-Steve-Swink-chapter-1.pdf)
- "Juice it or lose it" (Martin Jonasson and Petri Purho, 2012) live-transformed a Breakout clone. It added tweening/easing, squash-and-stretch ("the first of Disney's twelve principles"), particles, trails and sound. It is the canonical origin of "juice". — [RPG Playground: Making a 'juicy' game](https://rpgplayground.com/research-making-a-juicy-game/); [valdemird: Game feel on the web](https://valdemird.com/blog/game-feel-on-the-web/)
- Jan Willem Nijman (Vlambeer), "The Art of Screenshake" (INDIGO Classes 2013), gives about 30 tips. They include enemy knockback, permanence, camera lerp, camera position (look-ahead), screen shake, player knockback and "sleep" (a pause on hit). — [Internet Archive: The Art of Screenshake](https://archive.org/details/the-art-of-screenshake); [Make Games SA summary](https://makegamessa.com/discussion/1537/the-art-of-screenshake-by-flambeer-s-jan-willem-nijman)
- **Conflict on "sleep" duration:** one write-up says Nijman's sleep paused the game "for about 0.2 seconds" per bullet hit. Another game-feel article says hit-stop micro-pauses are "often as short as 40 to 80 milliseconds". A Nuclear Throne analysis says detonations freeze the whole game "for a couple of milliseconds" and shake the screen more. The most common Nuclear Throne explosion is a 9-frame animation plus a loud crunchy SFX. — [Blue Tengu: Art of Screenshake experiments](https://www.bluetengu.com/2014/12/12/art-of-screenshake-experiments/); [egmatic: Game Feel and Juice](https://egmatic.com/blog/how-to-make-your-game-feel-good); [ctrl500: Explosions in Nuclear Throne](https://ctrl500.com/game-design/explosions-in-vlambeers-nuclear-throne/)

**Screen shake: the trauma model and concrete parameter sets**
- Squirrel Eiserloh, GDC 2016, "Math for Game Programmers: Juicing Your Cameras With Math":
  - Keep trauma in [0,1]. Damage adds trauma, and trauma **decreases linearly** over time.
  - Shake = **trauma² or trauma³**.
  - Use **Perlin noise, not random values**.
  - In 2D, translational shake "feels nice" and rotational is "kind of lame". **In 3D, translational shake is "super lame" and rotational "feels nice"**, partly because translation can clip the camera into geometry.
  
  — [Eiserloh GDC2016 slides (PDF)](http://www.mathforgameprogrammers.com/gdc2016/GDC2016_Eiserloh_Squirrel_JuicingYourCameras.pdf); [Internet Archive: GDC2016Eiserloh](https://archive.org/details/GDC2016Eiserloh); [Roystan: Camera shake](https://roystan.net/articles/camera-shake/)
- Bevy's official screen-shake example follows Eiserloh's talk:
  - `TRAUMA_DECAY_PER_SECOND = 0.5`, so full trauma reaches 0 in 2 s.
  - `TRAUMA_EXPONENT = 2.0` ("shakes don't feel punchy when they go up linearly").
  - `MAX_ANGLE = 10°` ("somewhat high but still reasonable").
  - `MAX_TRANSLATION = 20 px` (2D).
  - `NOISE_SPEED = 20` ("fairly fast"; lower is "more dreamy").
  - `TRAUMA_PER_PRESS = 0.4`.
  - Three noise channels at offsets t, t+100 and t+200.
  - The shake offset is applied for rendering only and reset each frame so game logic never sees it.
  
  — [bevy/examples/camera/2d_screen_shake.rs](https://raw.githubusercontent.com/bevyengine/bevy/main/examples/camera/2d_screen_shake.rs)
- The `screen-shake` JS library (Eiserloh-based) defaults to maxAngle 12, maxOffsetX/Y 70 px, `duration` 28 updates (trauma 1→0) and speed 0.4. It uses simplex noise and exponential trauma. — [sajmoni/screen-shake README](https://raw.githubusercontent.com/sajmoni/screen-shake/main/README.md)
- **Roblox: RbxCameraShaker** (Sleitnick, port of Unity's EZ Camera Shake):
  - `ShakeOnce(magnitude, roughness, fadeIn, fadeOut, posInfluence, rotInfluence)`; it is bound with `BindToRenderStep` at a chosen priority.
  - Presets:
    - **Bump**: magnitude 2.5, roughness 4, fadeIn 0.1, fadeOut 0.75, pos 0.15, rot (1,1,1).
    - **Explosion**: 5, 10, 0, 1.5, pos 0.25, rot (4,1,1).
    - **Earthquake**: 0.6, 3.5, 2, 10, pos 0.25, rot (1,1,4).
    - **HandheldCamera**: 1, 0.25, 5, 10, pos 0, rot (1,0.5,0.5).
    - **Vibration**: 0.4, 20, 2, 2.
    - **RoughDriving**: 1, 2, 1, 1.
  - Shake comes from `math.noise(...) * 0.5` per axis times magnitude times fade. Roughness scales how fast noise time advances. Rotation influence is in **degrees** (`math.rad` applied), position in studs.
  
  — [RbxCameraShaker README](https://raw.githubusercontent.com/Sleitnick/RbxCameraShaker/master/README.md); [CameraShakePresets.lua](https://raw.githubusercontent.com/Sleitnick/RbxCameraShaker/master/src/CameraShaker/CameraShakePresets.lua); [CameraShakeInstance.lua](https://raw.githubusercontent.com/Sleitnick/RbxCameraShaker/master/src/CameraShaker/CameraShakeInstance.lua); [init.lua](https://raw.githubusercontent.com/Sleitnick/RbxCameraShaker/master/src/CameraShaker/init.lua)
- **Roblox: RbxUtil `Shake`** (Sleitnick) has Amplitude, Frequency, FadeInTime, FadeOutTime, SustainTime, Sustain, and Position/RotationInfluence, and supports `BindToRenderStep` and `OnSignal`. **Drift fix:** when layering shake over Roblox's default camera scripts, shake "causes odd side-effects, especially noticeable at higher FPS". The fix is to store the camera CFrame before applying shake and **restore it on Heartbeat** (after render) so the camera scripts never read the shaken CFrame. — [RbxUtil shake/init.luau](https://raw.githubusercontent.com/Sleitnick/RbxUtil/main/modules/shake/init.luau)
- Roblox `math.noise` "is most often between −1 and 1". For fractional inputs it "gradually fluctuate[s] between −0.5 and 0.5". **If x, y and z are all integers it returns 0.** It repeats with period 256 per axis. — [math.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/libraries/math.yaml)

**Hitstop / hitlag numbers**
- Sakurai (Smash Bros.):
  - Hitstop freezes **both parties for the exact same time**, with a **cap** on the maximum.
  - The victim **vibrates**, which "simulates a sense of shock more than having the characters freeze".
  
  — [Source Gaming: "Thinking About Hitstop"](https://sourcegaming.info/2015/11/11/thoughts-on-hitstop-sakurais-famitsu-column-vol-490-1/); [My Nintendo News](https://mynintendonews.com/2015/11/12/sakurai-talks-about-the-term-hitstop-used-in-fighting-games/)
- Sakurai's "Eight Hit Stop Techniques":
  1. Shake the character being hit more.
  2. Don't move the hitbox.
  3. Shake horizontally on the ground and vertically in the air.
  4. Gradually lessen the shake.
  5. Control the amount of hitstop.
  6. Interpolate frames into the damage pose.
  7. Keep the attacker moving just a little.
  8. Scale shaking with camera distance.
  
  — [Nintendo Wire: This Week in Sakurai](https://nintendowire.com/news/2022/12/12/this-week-in-sakurai-12-5-12-11-fine-tuning-hit-stop-and-cheating-the-system/); [TV Tropes: Masahiro Sakurai on Creating Games](https://tvtropes.org/pmwiki/pmwiki.php/WebVideo/MasahiroSakuraiOnCreatingGames)
- Smash Ultimate hitlag formula: ⌊⌊⌊(d × 0.65 + 6) × h × e × s⌋ × p⌋ × c⌋ frames.
  - d = damage, h = per-hitbox multiplier, e = electric 1.5×, c = crouch-cancel 0.67×.
  - **Cap: 30 frames** (20 when crouch-cancelling).
  
  — [SmashWiki: Hitlag](https://www.ssbwiki.com/Hitlag)
- Street Fighter V (on block): light **8**, medium **12**, heavy **15** frames of hitstop. Ken deviates with 8/10/12. Across "most games", light ≈9, medium ≈11, hard ≈13 frames. — [Shoryuken: Hitstop in SFV](http://shoryuken.com/2016/06/07/hitstop-in-street-fighter-v-kens-not-so-little-secret/); [Sonic Hurricane: Impact Freeze](https://sonichurricane.com/?p=1043)
- Roblox hitstop practice: `AnimationTrack:AdjustSpeed(0)` freezes a track. The docs say "0 pauses it". Community caveats:
  - On the **last keyframe** the animation may end instead of pausing; adjust TimePosition too.
  - Tracks sometimes keep moving briefly before freezing.
  - Some developers report inconsistent results.
  
  — [AnimationTrack.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/AnimationTrack.yaml); [DevForum: AdjustSpeed on last keyframe](https://devforum.roblox.com/t/is-it-possible-to-adjust-the-speed-of-animation-track-on-its-last-keyframe-to-0/3102771/2); [DevForum: Animation continues after freezing](https://devforum.roblox.com/t/animation-still-sometimes-continue-after-freezing-it/2927980); [DevForum: AdjustSpeed inconsistently](https://devforum.roblox.com/t/adjustspeed-working-inconsistently/2643111)

**Impact frames (anime/sakuga)**
- Impact frames are "single, high-contrast frames inserted … to simulate a powerful collision". They often use **inverted colors or extreme black-and-white silhouettes**, or swap the palette for stark blacks, whites or neons. They exploit retinal afterimage. These sources are SEO-style explainers, so treat them as moderate-quality. — [BrainVoyage: Impact Frames Meaning](https://brainvoyage.blog/impact-frames-meaning-animation-guide); [ArhFoundation: Impact frames meaning](https://www.arhfoundation.org/impact-frames-meaning); [Sakugabooru forum: Black and white and impact frames](https://www.sakugabooru.com/forum/show/1448)

**Anticipation, action, follow-through, easing**
- Attacks have three phases: **anticipation, attack (active), recovery**. A pattern that works for almost any action is "**slow start, fast action, slow settle**": wind-up frames are held longest, the action frame shortest, and recovery eases out. Longer wind-ups feel more impactful but add input delay. Follow-through (hair, cloth, weapon, torso) keeps motion from stopping abruptly. — [GDKeys: Anatomy of an Attack](https://gdkeys.com/keys-to-combat-design-1-anatomy-of-an-attack/); [sprite-ai: Sprite animation frames](https://www.sprite-ai.art/blog/sprite-animation-frames); [12 Principles for Game Animation](https://totter87.medium.com/12-principles-for-game-animation-a9137ef44345)

**Smoothing math (springs, damping)**
- Frame-rate-independent damping: `current = lerp(current, target, 1 − exp(−λ·dt))`. Plain `lerp(a, b, k)` per frame is frame-rate dependent. — [Rory Driscoll: Frame Rate Independent Damping using Lerp](https://www.rorydriscoll.com/2016/03/07/frame-rate-independent-damping-using-lerp/); [lisyarus: exponential smoothing](https://lisyarus.github.io/blog/posts/exponential-smoothing.html)
- Roblox now has a built-in **`TweenService:SmoothDamp(current, target, velocity, smoothTime, maxSpeed?, dt?)`**. It returns `(newValue, newVelocity)` from a critically damped spring and supports number, Vector2, Vector3 and **CFrame** (initialize the CFrame velocity with `CFrame.identity`). — [TweenService.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/TweenService.yaml)
- `spr` (Fraktality) uses `spr.target(instance, dampingRatio, frequency, {props})`. Damping <1 overshoots ("extra pop"), =1 is critical ("most visually neutral"), >1 is overdamped. It supports CFrame, Color3 (animated in CIELUV), number, UDim2 and Vector3, among others. Quenty's `Spring` (Nevermore) exposes Position, Velocity, Target, Damper and Speed, evaluated lazily on index. — [spr README](https://raw.githubusercontent.com/Fraktality/spr/master/README.md); [Quenty Spring.lua](https://raw.githubusercontent.com/Quenty/NevermoreEngine/main/src/spring/src/Shared/Spring.lua)

**FOV and slow motion in Roblox**
- `Camera.FieldOfView` is **vertical**, clamped to **1–120°**, default **70**. The docs suggest lowering FOV for magnification and **"Increasing FOV when the player is 'sprinting'"**. — [Camera.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/Camera.yaml)
- Roblox has **no native global time scale**: physics and networking assume a hard-coded step. Workarounds:
  - Scale gravity and assembly velocities.
  - Lerp CFrames after each physics step.
  - Use community frameworks such as MoonScale (scales velocities, forces and "time-like properties") or a Time Scale Framework.
  
  `ParticleEmitter.TimeScale` (0–1) and `AnimationTrack:AdjustSpeed` cover particles and animation. — [DevForum: Slow down physics (feature request)](https://devforum.roblox.com/t/slow-down-or-speed-up-part-physics-for-slow-motion-and-time-control-effects/30727); [DevForum: MoonScale](https://devforum.roblox.com/t/moonscale-slow-motion-on-roblox/4143911); [DevForum: Time Scale Framework](https://devforum.roblox.com/t/time-scale-framework/861231); [ParticleEmitter.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/ParticleEmitter.yaml)

### Inferences
**Recommended starting magnitudes for a Roblox 3D action game.** These are derived from the cited numbers; they are not sourced constants, so tune them in play:

| Event | Trauma add | Hitstop (s) | FOV punch | Impact frame | Notes |
|---|---|---|---|---|---|
| Light hit | +0.12–0.2 | 0.05–0.08 | none / +2° | no | victim vibrates; attacker barely |
| Heavy hit | +0.3–0.45 | 0.10–0.15 | +4–6°, out 0.05 s, back 0.25 s | optional 1 frame | horizontal shake grounded, vertical airborne (Sakurai) |
| Finisher / ultimate | +0.6–0.8 | 0.18–0.30 | +8–12° | 2–3 flashes, 0.03–0.06 s each | follow with 0.3–0.6 s slow-mo at 0.2–0.35× |
| Transformation climax | 0.9–1.0 | 0.2–0.35 | +12–15°, then settle | B/W, then white flash | cap total freeze ≤0.5 s (Smash cap: 30 f) |
| Earthquake / rumble | sustained 0.2–0.35 | — | slow −3–5° creep | no | low noise speed (2–6), decay 0.3–0.5/s |

- **Conversions:** SFV's 8/12/15 frames are ≈0.133/0.200/0.250 s at 60 fps. Smash's floor (d = 0) is 6 frames = 0.1 s and its cap is 0.5 s. Roblox players can cap at 60/120/144/240 fps (see Q3), so **always express hitstop, impact frames and shake in seconds, never in frames**.
- **3D shake shape for Roblox:**
  - Rotation-only, with per-axis maxima at trauma = 1 of about pitch 4–6°, yaw 2–4° and roll 3–8°. Bevy uses 10° roll for 2D. RbxCameraShaker's Explosion upper bound is ≈5° pitch (5 × 0.25 × 4) and ≈1.25° yaw/roll.
  - Translation ≤0.15–0.3 studs, or none.
  - Noise speed 15–25 for hits, 2–6 for handheld drift.
  - Decay 1–2 trauma/s for combat, so heavy shakes die in 0.3–0.6 s.
  - Use trauma². Normalize `math.noise` by ×2, since it mostly spans ±0.5, and use **non-integer seeds** because integer coordinates return 0.
- **Hitstop on Roblox should be client-side and visual only.** On the attacker's and victim's clients: `AdjustSpeed(0)` on the relevant tracks (store the previous `Speed` and restore it); `TimeScale = 0` on attached emitters; pause the cutscene/VFX clock; give the victim a small vibration (Sakurai). Server hit validation and timers must not pause.
- **Impact frame implementation:** two to three alternating looks, each held 0.03–0.06 s:
  1. B/W: ColorCorrection Saturation −1, Contrast ≈+1; character Highlight black or white.
  2. "Inverted feel": a white Highlight fill on characters over a darkened world (Brightness −0.6 to −1), per the community recipe.
  3. Normal.
  
  Fire it at the **start** of hitstop so the frozen pose is what the eye sees. Pre-create both the ColorCorrectionEffect (parented to the Camera, local only) and the Highlights, and only toggle them.
- **FOV punch:** set FOV instantly to base + Δ, then return with a spring (spr damping ≈0.5–0.7, frequency 2–4 Hz, for a slight overshoot) or a 0.2–0.35 s Quad/Expo-Out tween on the client. Sprint: base + 8–12° sustained, eased over about 0.3 s, in line with the docs' sprint suggestion.
- **Slow motion recipe:** drive *all* cutscene-owned time from one clock with a `scale`. Each frame, apply the scale to:
  - `AnimationTrack:AdjustSpeed(scale × baseSpeed)`
  - `ParticleEmitter.TimeScale = scale` (only on emitters in the shot)
  - custom tweens and springs, by advancing them with `dt × scale`
  - `Sound.PlaybackSpeed`, where a pitch drop is desirable
  
  Anchor and CFrame-drive actors during slow motion instead of fighting physics.
- **Speed lines:** use either (a) a camera-attached part with a disc/cylinder ParticleEmitter (Orientation VelocityParallel, inward or outward ShapeInOut, high Squash), or (b) a screen-space spritesheet ImageLabel cycling `ImageRectOffset` (DevForum recipe). The roadmap's 2D UI particles may replace (b) in late 2026.
- **Chromatic aberration:** the 3-ViewportFrame method re-renders cloned scene content and is costly. Reserve it for short UI-like moments. Prefer the cheaper 3× ColorCorrection tint pulse, or bake RGB-split into the impact-frame flipbook/texture instead. This is an inference: ViewportFrame cost was not measured.

**Luau pattern: trauma shake, layered on any camera driver**
```lua
-- client
local trauma, seed = 0, math.random() * 100 + 0.37   -- non-integer seed: math.noise(int,int,int) == 0
local MAX = Vector3.new(math.rad(5), math.rad(3), math.rad(6)) -- pitch, yaw, roll at trauma = 1
local SPEED, DECAY = 20, 1.5                                   -- noise units/s, trauma/s
local t = 0
local function addTrauma(x) trauma = math.min(1, trauma + x) end
local function shakeCFrame(dt: number): CFrame
	t += dt
	trauma = math.max(0, trauma - DECAY * dt)
	local s, n = trauma * trauma, t * SPEED
	return CFrame.Angles(
		MAX.X * s * 2 * math.noise(seed, n),
		MAX.Y * s * 2 * math.noise(seed + 17.3, n),
		MAX.Z * s * 2 * math.noise(seed + 41.7, n))
end
-- In a Scriptable cutscene: camera.CFrame = baseCF * shakeCFrame(dt)
-- Over default camera scripts: apply in render step, restore the un-shaken CFrame on Heartbeat (RbxUtil Shake drift fix)
```

### Gaps
- I could not access Eiserloh's slides or Nijman's talk directly (both blocked). The exact recommended max-angle and offset values from the slides are unverified. The "0.2 s sleep" figure conflicts with "40–80 ms" figures from other blogs.
- No published hitstop or shake values from Roblox battlegrounds games were found.
- I found no primary source on recommended FOV-punch magnitudes. The table values are inferences.

## Q3. Cutscene architecture in Roblox: scriptable camera, render-loop choice, dt-based interpolation, Bézier/Catmull-Rom paths, data-driven timelines that sync camera/animation/VFX/SFX/UI, letterboxing, fades, skippability, existing modules

### Takeaway
Run every cutscene **entirely on the client**. Drive it from **one clock** advanced in a `BindToRenderStep` callback (or `PreRender`) at the camera priority. Evaluate a continuous spline (Catmull-Rom or Bézier) instead of chaining Tweens. Fire timeline cues by comparing the clock against cue times, which stays robust to frame drops. Sync animation-driven moments through `GetMarkerReachedSignal`. Restore all camera/UI state on end or skip. `RenderStepped` is superseded by `PreRender`. `Camera:Interpolate` and `SetRoll` are deprecated.

### Cited Findings

**Render loop and priorities**
- `RunService.PreRender` is the "replacement for RenderStepped". It fires every frame before render. "The engine cannot start to render the frame until code running in this event has finished executing." It is client-only. `RenderStepped` has a migration note: "superseded by PreRender". `Stepped` is "superseded by PreSimulation". `RunService:Reset` is deprecated. — [RunService.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/RunService.yaml)
- `BindToRenderStep(name, priority, fn)` binds to PreRender. A lower priority runs sooner, and equal priorities run in random order. Default scripts run at **Input 100** and **Camera 200**. The `Enum.RenderPriority` values are First 0, Input 100, Camera 200, Character 300 and Last 2000; you must pass `.Value`. "All rendering updates will wait until the code in the render step finishes." — [RunService.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/RunService.yaml); [RenderPriority.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/enums/RenderPriority.yaml)
- `Heartbeat` fires after physics. "It's also when any waiting scripts are executed, such as those scheduled with the task library." After that step the engine sends replication. `PreAnimation` fires before animations are stepped and is useful for adjusting speed or priority. — [RunService.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/RunService.yaml)
- New fixed-step APIs: `BindToSimulation` / `BindToAnimation` run at a fixed frequency when `Workspace.UseFixedSimulation` is on. They are meant for physics/prediction (server-authority model), not camera. — [RunService.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/RunService.yaml); [Workspace.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/Workspace.yaml)
- Players can set a **maximum framerate of 60, 120, 144 or 240 FPS** natively (Windows first). 240 Hz matches the scheduler/physics tick ceiling. — [DevForum: Introducing the Maximum Framerate setting](https://devforum.roblox.com/t/introducing-the-maximum-framerate-setting/2995965); [Bloxstrap wiki: 240 FPS](https://github.com/bloxstraplabs/bloxstrap/wiki/Why-you-can't-(or-shouldn't)-go-faster-than-240-FPS)

**Camera API state (as of the current docs)**
- **Deprecated:**
  - `Camera:Interpolate` and the `InterpolationFinished` event: "use TweenService to smoothly animate the Camera".
  - `Camera:SetRoll` and `GetRoll`: "use the CFrame property to 'roll'".
  - `CoordinateFrame`: use `CFrame`.
  - `focus` (lowercase).
  - `GetLargestCutoffDistance`, `PanUnits`, `TiltUnits`, `GetPanSpeed`, `GetTiltSpeed`, `SetCameraPanMode`.
  
  — [Camera.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/Camera.yaml)
- `Camera.Focus` tells the engine which area to prioritize for operations such as lighting. PointLights may not render far from it. It is **not** updated automatically when CameraType is **Scriptable**, "you should update Focus every frame" at `Enum.RenderPriority.Camera`. — [Camera.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/Camera.yaml)

**Interpolation and animation sync**
- `TweenService:SmoothDamp` is a critically damped spring that works on CFrame (see Q2). — [TweenService.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/TweenService.yaml)
- `AnimationTrack:GetMarkerReachedSignal(name)` fires at KeyframeMarkers. **`KeyframeReached` is superseded.** `Play(fadeTime = 0.1, weight = 1, speed = 1)` and `Stop(fadeTime = 0.1)`. `Length` is 0 until the animation has loaded. — [AnimationTrack.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/AnimationTrack.yaml)
- `Workspace:GetServerTimeNow()` returns the client's approximation of server time. It is monotonic and moves at the local clock's rate within 0.6%, which suits synchronized starts. — [Workspace.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/Workspace.yaml)

**Community guidance on smooth cutscene cameras (search summaries)**
- Don't combine TweenService with per-frame RenderStepped writes on the camera; set `camera.CFrame` directly in the render step. Use RenderStepped/render-step, **not Heartbeat**, for camera updates, which "will cause stuttering". Bind with `BindToRenderStep` and a priority. Tweens "are only choppy on the server", so use the client. Quadratic Bézier with t advanced by elapsed time in the render loop is a common pattern. — [DevForum: Super Choppy Camera Tweening](https://devforum.roblox.com/t/super-choppy-camera-tweening/2437339); [DevForum: Camera is stuttering during cutscene](https://devforum.roblox.com/t/camera-is-stuttering-during-cutscene/2534430); [DevForum: Jittering when tweening Camera in RenderStepped](https://devforum.roblox.com/t/jittering-effect-when-tweening-camera-in-renderstepped/3108323); [DevForum: Camera choppy when tweening](https://devforum.roblox.com/t/camera-choppy-when-tweening-it/861786)

**Existing open-source modules and plugins**
- **CutsceneService** (bstummer):
  - Multi-point **Bézier** camera paths built from numbered parts in a folder, whose front faces give the look direction.
  - `CutsceneService:Create(folder, duration, easing…)`, including an `OutIn` direction. Queues and looping. Special functions such as `DisableControls`, `FreezeCharacter` and `CurrentCameraPoint`.
  - **Auto-caches and restores** the previous CameraType and CoreGuis.
  - Uses GoodSignal, plus a Studio helper plugin to visualize paths.
  - Its rationale: "chaining multiple linear tweens together often results in stiff, robotic camera transitions."
  
  — [CutsceneService README](https://raw.githubusercontent.com/bstummer/CutsceneService/main/README.md)
- **Grim's Cutscene Engine** (module + plugin) animates characters, instances and the camera. It has **"Actions"** keyframes that run code (play a sound, create an explosion) and subtitles. — [grims-cutscene-engine README](https://raw.githubusercontent.com/Reapimus/grims-cutscene-engine/master/README.md)
- **Easy-Roblox-Cutscenes** offers camera tweening, player/NPC animations, timed sound and movement lock. — [Easy-Roblox-Cutscenes README](https://raw.githubusercontent.com/timoursfoil/Easy-Roblox-Cutscenes/main/README.md)
- **CutsceneManager 2.0** has a splines API and attach/detach to follow an object's CFrame. **Moon Animator 2** is a plugin with a timeline, camera and FOV tracks. **Moon2Cutscene** plays Moon Animator 2 files in-game. The **RX Camera System** is open-sourced. — [DevForum: CutsceneManager 2.0](https://devforum.roblox.com/t/cutscenemanger-20-%E2%94%81-create-and-manage-cutscenes-in-a-clean-and-organised-way/3635714); [DevForum: Moon2Cutscene](https://devforum.roblox.com/t/v2-moon2cutscene-play-moon-animator-2-files/3001411); [ExitLag: Moon Animator guide](https://www.exitlag.com/blog/moon-animator-roblox/); [DevForum: RX Camera System](https://devforum.roblox.com/t/rx-camera-system-open-sourced/2165742)
- Shake and spring libraries: RbxCameraShaker, RbxUtil Shake, spr and Quenty Spring (see Q2).

### Inferences
**Reference architecture ("Director") for an AI agent to implement once and reuse:**
1. **Server** decides *that* a cutscene happens (validation, state change such as race = Red). It sends `RemoteEvent:FireClient(player, "Transform_Red", startServerTime)`. For shared moments, use `FireAllClients` with `workspace:GetServerTimeNow() + 0.3` so all clients start together. Make the gameplay state change on the server *before or at the start*, so a skip never desyncs.
2. **Client Director** loads a **sequence data module**, a pure table with no logic (see Q6). Preloading and pooling are already done during a fade or earlier (see Q4).
3. At play time:
   - Cache CameraType, FOV, CameraSubject, CoreGui states and Lighting/post-effect states.
   - Set `CameraType = Scriptable` and disable controls.
   - `BindToRenderStep("Cutscene", Enum.RenderPriority.Camera.Value + 1, step)`.
4. `step(dt)` does the following, all in one callback with no allocation-heavy work:
   - `clock += dt * timeScale`.
   - Fire **every** cue whose `t ≤ clock` that hasn't fired, so frame drops never skip cues.
   - Evaluate the camera track (position spline + look-at spline + FOV and roll curves).
   - Multiply by the shake CFrame.
   - Write `camera.CFrame`, `camera.FieldOfView` and `camera.Focus`.
5. Animation-driven beats (a punch landing, eyes opening) are cued from **`GetMarkerReachedSignal`** on the actor's track, not from absolute times. Absolute-time cues can drift if the animation loads late or a hitstop pauses it.
6. **End/skip** jumps the clock to the end and applies every remaining cue's **end state** (lighting restored, model swapped, letterbox removed). It unbinds the render step and restores the cached state. The camera returns to gameplay through a short SmoothDamp blend (0.3–0.6 s) from the last shot, not a snap.

**Camera path math (pure Luau, no allocation-heavy calls):**
```lua
-- Uniform Catmull-Rom through key positions: C1-continuous, passes through every key (unlike Bézier control points)
local function catmullRom(p0: Vector3, p1: Vector3, p2: Vector3, p3: Vector3, t: number): Vector3
	local t2, t3 = t * t, t * t * t
	return 0.5 * ((2 * p1) + (p2 - p0) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (3 * p1 - p0 - 3 * p2 + p3) * t3)
end
-- Evaluate position AND a separate look-at target spline, then: CFrame.lookAt(pos, look) * CFrame.Angles(0, 0, roll)
-- Apply ONE global easing to the whole segment's parameter (not per-key tweens) to avoid velocity kinks at keys.
```
- Use **centripetal** Catmull-Rom (alpha = 0.5) if keys are unevenly spaced; uniform splines can overshoot or loop. This is a general spline property, not sourced here.
- For "hero orbit" shots, interpolate an angle around a pivot (`CFrame.new(pivot) * CFrame.Angles(0, θ(t), 0) * CFrame.new(0, h, r)`), which is cleaner than a positional spline.

**Director skeleton (client):**
```lua
local RunService = game:GetService("RunService")
local camera = workspace.CurrentCamera
local Director = {}
Director.__index = Director

function Director.new(seq) -- seq = { duration, cues = {{t=..., type=..., ...}}, cameraAt = function(t) -> CFrame, fov, look }
	table.sort(seq.cues, function(a, b) return a.t < b.t end)
	return setmetatable({ seq = seq, clock = 0, scale = 1, nextCue = 1,
		shake = function(_dt) return CFrame.identity end }, Director) -- replace with the trauma shaker from Q2
end

function Director:_step(dt)
	self.clock += dt * self.scale
	local cues, t = self.seq.cues, self.clock
	while self.nextCue <= #cues and cues[self.nextCue].t <= t do
		local cue = cues[self.nextCue]; self.nextCue += 1
		task.spawn(self.seq.handlers[cue.type], cue, self) -- handlers must be cheap; heavy work was pre-done
	end
	local cf, fov, look = self.seq.cameraAt(math.min(t, self.seq.duration))
	camera.CFrame = cf * self.shake(dt)
	camera.FieldOfView = fov
	camera.Focus = CFrame.new(look) -- Scriptable cameras must update Focus themselves
	if t >= self.seq.duration then self:Finish() end
end

function Director:Play()
	self.saved = { type = camera.CameraType, fov = camera.FieldOfView }
	camera.CameraType = Enum.CameraType.Scriptable
	RunService:BindToRenderStep("Cutscene", Enum.RenderPriority.Camera.Value + 1, function(dt) self:_step(dt) end)
end

function Director:Finish()
	RunService:UnbindFromRenderStep("Cutscene")
	-- Skip() sets self.clock = duration and calls Finish(); end states must be idempotent, applied to ALL cues
	-- (fired ones may still be mid-tween), so a skip at any moment lands in the exact final state
	for _, cue in self.seq.cues do self.seq.applyEndState(cue) end
	camera.FieldOfView = self.saved.fov
	camera.CameraType = self.saved.type
end
```

**Letterbox, fades, skip:**
- **Letterbox:** compute bars from the real viewport so every device ends at the same target aspect: `bar = max(0, 1 − (ViewportSize.X/ViewportSize.Y)/2.39)/2`. That gives ≈12.8% per bar on 16:9, ≈8% on 2:1 and ≈4.6% on 19.5:9 phones. Put the bars in a ScreenGui that ignores the GUI inset, with the highest DisplayOrder. Tween them in over 0.4–0.6 s (Quad Out) and out over 0.3–0.5 s.
- **Fades:** a black or white full-screen Frame tween (0.15–0.4 s) hides UI too. `ColorCorrectionEffect.Brightness` → −1 (black) or +1 (white) fades only the 3D world, leaving the UI and subtitles visible. Per the docs, −1 is all black and +1 all white. Use the white version for transformation flashes.
- **Skip:**
  - Show "Hold [key/button] to skip" after about 1 s.
  - Hold to confirm (0.5–0.8 s) on first viewing; allow a tap on repeat viewings.
  - On skip: fade to black (0.15 s), call `Finish()` (applies end states), fade in (0.25 s).
  - Never skip without applying end states. The race change must already be committed server-side.
- **Repeats:** store a "seen" flag (server-side profile) and play a **short version** of race transformations after the first time (see Q5).

### Gaps
- No official Roblox cutscene framework or sequencer exists in the docs I could access. The architecture above is synthesized from API docs plus community modules.
- I could not read the CutsceneService or Moon2Cutscene source to confirm which render event they use internally.

## Q4. Smoothness: root causes of micro-stutter in Roblox cutscenes and death/run-over animations, and their fixes

### Takeaway
Most cutscene "micro-stutters" have a short list of causes:
- Content loaded on first use: animations, particle textures, meshes and sounds.
- Instance work at the peak frame: `Instance.new`/`Clone`/parent-first, adding a Highlight, or swapping a humanoid or skinned model.
- Motion computed on the server, or replicated physics: server tweens, server-owned ragdolls and vehicles.
- Camera logic on the wrong loop: Heartbeat or `task.wait` loops, Tweens fighting per-frame writes, default camera scripts fighting a shake.
- Frame-count-based timing at variable FPS.

The fixes are preload, pool and prewarm before the sequence; do everything visual on the client; drive everything from one render-step clock; and verify with the MicroProfiler that no frame exceeds budget.

### Cited Findings
- **Animations on first play:** characters can T-pose or "hesitate" the first time an animation plays because it isn't downloaded yet.
  - Fix 1: load all tracks at startup and store them.
  - Fix 2: `ContentProvider:PreloadAsync({Animation…})`, which yields, so use `task.spawn`, often from ReplicatedFirst.
  
  — [DevForum: How to properly preload animations](https://devforum.roblox.com/t/how-to-properly-preload-animations/218347); [DevForum: How to preload animations #2](https://devforum.roblox.com/t/how-to-preload-animations/853322/2); [DevForum: Best way to preload animations](https://devforum.roblox.com/t/whats-the-best-way-to-preload-animations/1917889)
- `Animator:LoadAnimation()` "always creates a **new** AnimationTrack instance which may impact game performance if overused". Use `GetTrackByAnimationId()` to look up loaded tracks. Animations on a player's character started on that client replicate. Non-player Animators must load and play on the server to replicate. — [Animator.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/Animator.yaml)
- `ContentProvider:PreloadAsync(instances, callback)` yields until the content of the given instances (Decals, Sounds and so on) is loaded, reporting an `AssetFetchStatus` per asset.
  - **SurfaceAppearance and MaterialVariant are not supported.**
  - Textures of instances that aren't visible may be kept only in the disk cache and unloaded from memory after preloading.
  - `ContentProvider:Preload` is superseded.
  
  — [ContentProvider.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/ContentProvider.yaml)
- **Particle first use:** cloned emitters show an initial delay "easily 100+ms" while textures load. Later emitters with the same texture are instant "until textures are unloaded when no particle systems are actively using them." Emitters also "warm up", starting below their Rate. Suggested fixes: keep emitters loaded in parts and call `:Emit()`, or preload textures. A bug report also notes `:Emit()` lag spikes when the camera is very close to the emitter, which relates to fill-rate. — [DevForum: Significant delay on displaying particle effects](https://devforum.roblox.com/t/significant-delay-on-displaying-particle-effects-even-after-first-load-and-on-repeated-reuse/2718982); [DevForum: Particle emitter starts very slow](https://devforum.roblox.com/t/particle-emitter-starts-very-slow-and-speeds-up/3326969); [DevForum: How To Instantly Emit A Particle](https://devforum.roblox.com/t/how-to-instantly-emit-a-particle/3030685); [DevForum: Emit() lag spikes when camera is close](https://devforum.roblox.com/t/particleemitteremit-causes-huge-lag-spikes-when-camera-is-close-to-particleemitter/2543010)
- **Instance creation:** a Roblox engineer's (zeuxcg) PSA says to set **Parent last**. Setting Parent first (including via `Instance.new(class, parent)`) "practically guarantees redundant work" that ranges from slightly worse to "catastrophically worse". — [DevForum PSA: Don't use Instance.new() with parent argument](https://devforum.roblox.com/t/psa-dont-use-instancenew-with-parent-argument/30296)
- **Pooling:** PartCache pre-creates parts and CFrames them "far away" when unused. CFrame is described as the only "fast" property to change every frame, whereas reparenting costs extra work. ObjectCache is a newer model/part cache. — [DevForum: PartCache](https://devforum.roblox.com/t/partcache-for-all-your-quick-part-creation-needs/246641); [DevForum: ObjectCache](https://devforum.roblox.com/t/objectcache-a-modern-blazing-fast-model-and-part-cache/3104112); [DevForum: Part Pooling](https://devforum.roblox.com/t/part-pooling-increase-performance-with-many-parts/518433)
- **Humanoids and skinned meshes:** "Instantiating, modifying, and respawning models with Humanoids or skinned MeshParts" is intensive, especially with layered clothing. MicroProfiler **`updateInvalidatedFastClusters` over 4 ms** signals this. **Size/scale changes rebuild FastClusters.** Playing animations on many NPCs from the server is overhead. — [performance-optimization/improve.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/performance-optimization/improve.md)
- **Highlights:** adding or removing them causes geometry-rebuild spikes; toggling properties is cheap (see Q1). — [highlighting.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/effects/highlighting.md)
- **Server-driven motion:** a tween run on the server "has to tell every single client every single time it moves". Forum answers describe a 30 Hz server clock. Fixes: tween on clients via `FireAllClients`, TweenService V2 (server API, client execution), or a replicated-tweening module that sends only tween info. — [DevForum: Tween is Choppy](https://devforum.roblox.com/t/tween-is-choppy/941705); [DevForum: TweenService V2](https://devforum.roblox.com/t/tweenservice-v2/199815); [GitHub: roblox-replicated-tweening](https://github.com/kipuki/roblox-replicated-tweening); [DevForum: Tweening on the client](https://devforum.roblox.com/t/tweening-on-the-client/1472967)
- **Ragdolls and death physics:** NPC ragdolls look choppy because the server simulates them "at a lower frequency" and clients correct toward replicated positions. Player ragdolls are smooth because the client simulates them. Setting the network owner to the player is smoother but adds latency for other viewers. A fully client-side ragdoll (triggered by a death event) needs no networking but may diverge per client. — [DevForum: Choppy NPC ragdolls on the server](https://devforum.roblox.com/t/choppy-npc-ragdolls-on-the-server/4252671); [DevForum: Seamless ragdolls](https://devforum.roblox.com/t/how-do-you-achieve-seamless-ragdolls-r6/731339); [DevForum: Ragdolling on death on client](https://devforum.roblox.com/t/ragdolling-on-death-on-client-freezes-the-character/3540705)
- `Workspace.ImprovedPhysicsReplication` exists ("uses the improved physics replication path"). `Workspace.InterpolationThrottling` is hidden: "Do not use it for new work." — [Workspace.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/Workspace.yaml)
- **Camera loop choice and drift:** see Q3 (Heartbeat causes stutter; don't mix tweens with render-step writes). See also Q2 for the RbxUtil drift fix ("especially noticeable at higher FPS"). — [DevForum: Camera is stuttering during cutscene](https://devforum.roblox.com/t/camera-is-stuttering-during-cutscene/2534430); [RbxUtil shake/init.luau](https://raw.githubusercontent.com/Sleitnick/RbxUtil/main/modules/shake/init.luau)
- **Budget and diagnosis:** open the MicroProfiler with **Ctrl+Alt+F6** (⌘⌥F6) and check whether frames exceed **16.67 ms**. It is "particularly useful for identifying 'spikes'". The script scopes for PreRender and Heartbeat are labeled. — [performance-optimization/identify.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/performance-optimization/identify.md); [performance-optimization/improve.md](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/performance-optimization/improve.md)
- **Cutscene-specific streaming hooks** (full streaming coverage is in another note):
  - `Player:RequestStreamAroundAsync(position, timeOut)` asks the server to stream around a location "if the experience knows that the player's CFrame will be set to the specified location in the near future". There are no guarantees; client memory and network conditions matter.
  - `Workspace.PredictiveStreamingMode`'s Default currently behaves as Disabled.
  - `Camera.Focus` prioritizes lighting around the focus point.
  
  — [Player.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/Player.yaml); [Workspace.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/Workspace.yaml); [Camera.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/Camera.yaml)

### Inferences
**Mapping the user's three pain points to likely causes and fixes:**

| Symptom | Most likely cause(s) | Fix pattern |
|---|---|---|
| Micro-stutter "throughout" a cutscene | Camera written from Heartbeat or a `task.wait` loop (these resume on Heartbeat, after render), or several chained Tweens with velocity kinks at joins, or a Tween plus per-frame writes on the same property; possibly server-side tweens | One `BindToRenderStep` callback at Camera+1 writes CFrame/FOV/Focus from a continuous spline evaluated by an accumulated-dt clock; no TweenService on the camera during the sequence; everything on the client |
| Hitch at specific beats (flash, explosion, transformation) | First-use loads (particle textures 100+ ms, meshes, sounds, animations), `Clone()`/`Instance.new` of big VFX models, adding Highlights, swapping a humanoid/skinned model (FastCluster rebuild >4 ms), scaling the character | Preload during the fade or loading screen; pool and pre-parent effect models; prewarm emitters with a tiny `Emit` just before the cut; pre-create Highlights and toggle `Enabled`; build the new race model before the climax and swap visibility inside the white flash; never resize skinned rigs at the peak |
| Death / run-over animation stutter | Server-owned vehicle or ragdoll physics interpolating on clients; network-ownership flip on collision; death joints breaking under server simulation; first-play animation load | Play the run-over as a **client-side canned sequence**: on the death event, each client poses its local copy (anchored, CFrame-driven or animation-driven), or ragdolls locally; preload the death animations; keep the server authoritative only for the outcome (dead / alive) |
| Reveal shot where the distant world "loaded slowly" | Content not streamed or loaded when the camera got there | During the previous shot: `RequestStreamAroundAsync(cityPos)`, `PreloadAsync` on key city meshes and decals (SurfaceAppearance excluded), set `Camera.Focus` to the city; keep a persistent low-detail silhouette or impostor so the skyline never pops; let Atmosphere haze cover LOD transitions |

**Pre-flight checklist for every sequence (agent-enforceable):**
1. All assets in the sequence's manifest are passed to `PreloadAsync` before `Play()`, with a timeout fallback that plays without the missing piece rather than waiting.
2. Every VFX model is pooled: cloned at load, properties set, **Parent last**, parked far away, anchored, with CanCollide/CanTouch/CanQuery false. The emitter lists are cached so there is no `GetDescendants()` at the peak.
3. No `Instance.new`, `Clone`, `Destroy`, `LoadAnimation` or `Highlight` creation inside the sequence; only CFrame or property toggles and `Emit`.
4. All timing is in seconds from the Director clock; nothing counts frames.
5. One render-step binding owns the camera. The default camera is disabled via Scriptable, and the drift-fix pattern is used if shaking a non-Scriptable camera.
6. Instrumentation: in debug builds, log any `dt > 1/45` during the sequence together with the active cue, so the agent can attribute spikes to specific beats.
7. Test at 60 and 240 FPS caps and on a low-end mobile device: flipbooks may be auto-disabled and glass refraction is absent there.

**Prewarm pattern:**
```lua
-- during fade-in, ~0.5–1 s before the peak: load textures without visible output
for _, e in pooledEmitters do e:Emit(1) end   -- emitter parked out of the shot; or set its Transparency sequence to 1 for this burst
-- at the peak: move + burst (no allocation)
holder.CFrame = hitCF
for _, e in pooledEmitters do e:Emit(e:GetAttribute("EmitCount")) end
```
I have not confirmed that an emitter parked out of view, or with Transparency 1, actually triggers the texture load. This needs a Studio test (see Gaps).

### Gaps
- No Roblox-official statement on Luau GC pause behavior at cutscene peaks was found. "Avoid garbage spikes" here is general practice, not a documented Roblox number.
- Whether parked or invisible emitters keep textures resident, and how long textures stay cached after the last use, is undocumented. It is known only from a bug-report summary.
- The "server 30 Hz" tween replication figure comes from forum answers, not official docs.
- The user's actual code was not inspected, so the root-cause table is a ranked hypothesis list.

## Q5. Cinematography for mystery and anticipation: "glimpse" shots that tease a location, mysterious entity reveals, and anime transformation/power-up structure and timing

### Takeaway
Tease, don't show:
- Use **partial reveals**: foreground obstruction, silhouettes, haze, pan/tilt/crane reveals and rack focus.
- Lead with the **character's reaction** (the "Spielberg face") before the place.
- Make the capital a persistent **"weenie"**, a landmark visible on the horizon that promises a payoff, as BotW does with Hyrule Castle.

Anime transformations are dramatized build-up → peak → release sequences. They range from about 3 s (the "actual" change) to 34–40 s (Sailor Moon), and they lean on stock "bank" reuse plus power-up tropes: aura, dramatic wind, rising debris and ground cracks. A game needs a long first-time version and a short repeat version.

### Cited Findings

**Reveal and glimpse technique**
- A reveal shot "starts by showing something partially or not at all, then discloses the full picture through camera movement or editing." Tools include:
  - Slow push-ins or pullbacks.
  - Tracking past obstacles.
  - Doors, curtains or silhouettes as concealment.
  - **Foreground obstruction** (doorway, window, fence, foliage, another character's shoulder) for "voyeurism, mystery".
  - **Pan reveals** to off-screen elements.
  - Entrance reveals.
  - Tilts "to reveal the grandeur of a scene".
  
  — [Morphic: Reveal shot](https://morphic.com/ai-glossary/Reveal-Shot); [Beverly Boy: What Is a Reveal Shot?](https://beverlyboy.com/filmmaking/what-is-a-reveal-shot/); [StudioBinder: Foreground in Film](https://www.studiobinder.com/camera-shots/composition/foreground-in-film/); [TV Tropes: Reveal Shot](https://tvtropes.org/pmwiki/pmwiki.php/Main/RevealShot)
- **Weenie** (Walt Disney's term): a large, highly visible landmark with long sightlines (e.g., Cinderella's Castle) that draws visitors and "promise[s] guests that where they are travelling to is worth the effort". In games it attracts the eye, gives navigation without HUD, and whets "the player's appetite in anticipation of what is to come". — [Level Design Book: Disneyland](https://book.leveldesignbook.com/studies/irl/disneyland); [Game Developer: What Mario Learned from Mickey Mouse, Part 3](https://www.gamedeveloper.com/design/what-mario-learned-from-mickey-mouse---part-3-decision-making-and-weenies); [Boing Boing: Game-design lessons from Disneyland](https://boingboing.net/2009/03/27/gamedesign-lessons-f.html)
- *Breath of the Wild*: when Link exits the Shrine of Resurrection, the player takes in the view of Hyrule Castle. The camera then pans to the Old Man to guide the player without explicit instruction. — [Cultured Vultures: Great Plateau](https://culturedvultures.com/breath-of-the-wild-great-plateau-masterpiece/); [Elite Rev: Quiet Guidance on the Great Plateau](https://eliterev.wordpress.com/2017/03/16/breath-of-the-wilds-quiet-guidance-and-the-lessons-of-the-great-plateau/)
- **Spielberg face**: a close-up of a character looking slightly upward, eyes wide, mouth slightly open, often shot from below eye line. The reaction tells the audience how to feel before, or instead of, showing the object. One source claims *Jurassic Park* holds on stunned faces for a long stretch before showing the dinosaurs; its "40 seconds" figure is unverified. — [Monarch Studios: Spielberg Face](https://monarchstudiosla.com/spielberg-face-a-cinematic-technique-that-resonates-with-audiences/); [Pixflow: Spielberg reaction shots](https://pixflow.net/blog/spielberg-reaction-shots-emotion/); [Hollywood Reporter: Hereditary flips Spielberg's shot](https://www.hollywoodreporter.com/movies/movie-news/hereditary-flips-steven-spielbergs-trademark-movie-shot-1118716/)
- **Pacing:** James Cutting's research found average shot length fell from about 12 s (1930) to **≈2.5 s (2014)**, and from 8–10 s in the 1960s to 3–4 s by 2005. — [Cornell Chronicle](https://news.cornell.edu/node/271563); [Keegan Phillips: Shot length in modern film](https://www.keeganphillipsdesign.com/writing/shot-length-in-modern-film)

**Mysterious entity appearance**
- **Silhouette/backlighting** places the subject before a bright light, obscuring features "to create a sense of mystery and suspense". Viewers become active and read posture and composition instead of the face. Backlight also creates a "luminous halo". Related: "Face Framed in Shadow", chiaroscuro and Rembrandt lighting. — [Medium: How Silhouettes Create Mystery in Film](https://medium.com/@tikit3426/how-silhouettes-create-mystery-in-film-b26d1cd08c6e); [TV Tropes: Face Framed in Shadow](https://tvtropes.org/pmwiki/pmwiki.php/Main/FaceFramedInShadow); [Render Factory: Lighting up a character](https://www.renderfactorycgi.com/lessons-lighting/lighting-up-a-character)

**Anime transformation and power-up structure**
- "Henshin" sequences are budget-friendly reusable stock ("bank") footage. Lengths:
  - Cutey Honey (original): ≈5 s.
  - Princess Tutu: ≈14 s.
  - High School DxD Balance Breaker: ≥15 s.
  - **Sailor Moon: 34–40 s**.
  - *Kamen Rider W*: the scene runs over a minute, but "the actual transformation takes only three seconds". The rest dramatizes the process.
  
  — [TV Tropes: Transformation Sequence (Anime & Manga)](https://tvtropes.org/pmwiki/pmwiki.php/TransformationSequence/AnimeAndManga); [TV Tropes: Transformation Sequence](https://tvtropes.org/pmwiki/pmwiki.php/Main/TransformationSequence); [Fantasy/Animation: Henshin to Life](https://www.fantasy-animation.org/current-posts/henshin-to-life-the-real-the-cartoonish-and-the-impossibilities-of-animated-tokusatsu-with-kamen-rider-w-and-fuuto-pi)
- Power-up tropes: a **Battle Aura** with **Dramatic Wind** and **Chunky Updraft** (debris lifting), circular ground indentations or craters, and ground breaking apart and floating (popularized by *Dragon Ball Z*). One AI-video site summarizes what reads well as "energy grows from one held stance, with slow builds that flare on a beat and ground-crack shockwaves". — [TV Tropes: Chunky Updraft](https://tvtropes.org/pmwiki/pmwiki.php/Main/ChunkyUpdraft); [All The Tropes: Power Floats](https://allthetropes.org/wiki/Power_Floats); [TV Tropes: Super Mode](https://tvtropes.org/pmwiki/pmwiki.php/Main/SuperMode); [Morphic: Anime power-up videos](https://morphic.com/resources/videos/anime-power-up-videos)
- Anime timesheets use "tome (止め)" to mark a single drawing held for an entire cut, i.e., a hold. — [Sakuga Wiki: Timesheet](https://sakuga.fandom.com/wiki/Timesheet)
- Impact frames as the peak "shock" device: see Q2. — [BrainVoyage: Impact Frames](https://brainvoyage.blog/impact-frames-meaning-animation-guide)

### Inferences
**A. World-reveal "glimpse" of the capital (≈10–12 s, four shots, each 2–4 s per modern ASL norms):**

| # | Time | Shot | Camera (Roblox) | Look and lighting | Audio | Purpose |
|---|---|---|---|---|---|---|
| 1 | 0.0–2.5 | MCU, low angle, character's awe face (Spielberg face) | FOV 40–50 (≈30 mm look), slow 0.3 stud/s push-in | DOF: FocusDistance = face distance, InFocusRadius ≈2, FarIntensity 0.6–0.8 (background unreadable) | wind; music drops to a single sustained note | the reaction sells the scale before it is seen |
| 2 | 2.5–6.5 | Crane up and over a foreground obstruction (cliff lip, ruins, trees) | Catmull-Rom rise of 15–30 studs; FOV eases 50→35 (telephoto compression enlarges distant skyline) | Rack focus: DOF FocusDistance animates near→far (≈1.5 s); Atmosphere Haze up and Offset raised so the city reads as a **silhouette** against the sky; sun placed *behind* the tallest spire (ClockTime) with SunRays and mild Bloom | swell begins | partial reveal: silhouette only |
| 3 | 6.5–9.5 | Locked or very slow push on the skyline, framed by obstruction edges | FOV 30–35, ≤1°/s drift | Clouds (large slow particles or moving cloud meshes) drift across ~30–50% of the city; ColorCorrection slight warm tint | motif or leitmotif of the capital | never show it all |
| 4 | 9.5–11 | Clouds close, or cut back to character, then gameplay | SmoothDamp blend to gameplay camera (0.5 s) | restore post-processing | music resolves | afterwards the capital stays visible as the in-game weenie |

Loading: issue `RequestStreamAroundAsync(cityCenter)` and `PreloadAsync(cityKeyMeshes)` before shot 1 (ideally a few seconds earlier). Set `Camera.Focus` to the city during shots 2–3. Keep a persistent low-detail silhouette model of the capital so shot 2 never shows popping. Haze is both mood and an LOD mask.

**B. Mysterious guiding entity (≈8–10 s):**
1. **Omen (0–1.5 s):** ambient audio ducks; wind particles reverse toward a point; nearby PointLights flicker (Brightness tween with noise); ColorCorrection Saturation drifts to −0.4.
2. **Silhouette (1.5–4 s):** the entity appears **backlit**. A strong light, a Neon halo and Bloom sit behind it. Its body reads dark via a pre-created Highlight (FillColor black, FillTransparency ≈0.1, glowing OutlineColor, DepthMode Occluded). The face stays in shadow. Use a low angle and a slow push.
3. **Single detail (4–6 s):** an extreme close-up on one feature only: eyes (Neon plus a small PointLight) or a hand. Never the full face.
4. **Guidance gesture (6–8 s):** the entity points; the camera **pans along the gesture** to the capital or objective (pan reveal plus weenie). This ties the entity to the glimpse shot.
5. **Vanish (8–9.5 s):** particles implode (`ShapeInOut` inward), the Highlight fades, there is a quick white flash, and saturation returns. A sound tail lingers 1–2 s after the visual is gone.

**C. Race transformation (first-time ≈8–10 s, repeat ≈2.5–3.5 s), structured build-up → hold → peak → release:**
- **Build-up (≈45%):**
  - Desaturate the world (Saturation −0.5); spawn race-colored aura particles drawn inward (anticipation).
  - Rocks and debris lift (chunky updraft); the ground crack decal grows.
  - Sustained trauma ramps 0.1→0.35; a slow 20–30° orbit; FOV narrows 70→55 to build tension.
  - Rising rumble and choir/synth riser.
- **Hold, "tome" (≈5–8%):**
  - Sudden silence (cut SFX) and a slow-mo scale of 0.1.
  - Extreme close-up as the eyes ignite in the race color.
  - One heartbeat SFX.
- **Peak (≈3–6%):**
  - Impact frame (B/W 0.05 s, then white 0.05 s); hitstop 0.2–0.3 s.
  - ColorCorrection Brightness 1→0 over 0.3 s (white flash).
  - Shockwave ring, crater decal and burst `Emit`; trauma 0.9–1.0; FOV punch +12–15°.
  - **Swap to the pre-built race model inside the white flash** so the change never visibly pops.
- **Release and reveal (≈35–40%):**
  - Low-angle hero shot with a slow push-in.
  - The aura settles into the race's idle loop; subtle TintColor in the race color.
  - Title card (race name) in UI.
  - Letterbox out; SmoothDamp back to gameplay.
- **Repeat version:** keep only peak plus release (≈2.5–3.5 s), always skippable. This mirrors anime bank footage reuse: the same sequence for all six races, parameterized by color, aura flipbook and title.

### Gaps
- I found no primary industry source (studio postmortem or GDC talk) giving shot-by-shot timing for game "world reveal" shots. The tables are synthesized from film technique sources plus game-design analyses.
- I found no English-language production source defining the Japanese "tame" (溜め, wind-up hold) term. Only "tome" (止め, hold) was sourced.
- The Morphic and BrainVoyage-type sources are AI-tool and SEO sites. Their descriptive claims match TV Tropes but are not authoritative.

## Q6. How to specify cinematic sequences for an AI agent: beat sheets, shot lists, timing tables with camera/VFX/SFX/lighting columns

### Takeaway
Give the agent three layered documents:
1. A **beat sheet**: intent and emotion per beat, which is the contract.
2. A **shot list**: shot size, angle, movement, lens→FOV, duration, subject.
3. A **cue table / X-sheet**: time-stamped events per lane, covering camera, animation, VFX, SFX, music, lighting/post, UI and gameplay state.

Add an **asset manifest** for preloading and **acceptance tests** (frame-time, skip, restore). Encode the cue table as a pure-data Luau module consumed by one generic Director, so the agent edits data, not engine code.

### Cited Findings
- Standard shot-list columns: scene/shot number, **shot size** (wide, medium, close-up, extreme close-up, two-shot), **camera angle** (high, low, eye-level, Dutch), **movement** (static, pan, tilt, dolly, tracking, crane), **lens** (e.g., 24/50/85 mm), **duration**, and a **description** of subject, action and props. Some templates list 14 columns including audio and equipment. — [Boords: Shot List Template](https://boords.com/shot-list-template); [ifilmthings: Shot List Template](https://ifilmthings.com/shot-list-template/); [Seikan: Shot List Template Guide](https://seikan.app/blog/shot-list-template-guide)
- In game cutscene production, a **beat sheet** maps each script line to camera intent, character blocking and **gameplay state requirements**. It "becomes the contract between narrative, animation, and engineering". In-engine **previs** with proxy characters locks timing; the locked previs then serves as the shot list. — [Mocap Online: Cutscene Direction & Game Cinematics](https://mocaponline.com/blogs/mocap-news/cutscene-direction-game-cinematics); [VFX Voice: How Previs Has Gone Real-Time](https://vfxvoice.com/how-previs-has-gone-real-time/)
- Traditional animation planned timing on exposure sheets (dope sheets / X-sheets) that map frame counts to dialogue, camera moves and action beats. Modern scene timelines use lanes for dialogue, foley, ambience, music, voice, transitions, VFX and camera. — [Sunstrike Studios: Timing in Animation](https://sunstrikestudios.com/en/blog/timing_in_animation/); [GitHub issue: PlotPickle scene timeline lanes](https://github.com/BryanHarrisScripts/PlotPickle/issues/2125); [Wikipedia: Cue sheet](https://en.wikipedia.org/wiki/Cue_sheet)
- `Camera.FieldOfView` is the **vertical** FOV in degrees (1–120, default 70). — [Camera.yaml](https://raw.githubusercontent.com/Roblox/creator-docs/main/content/en-us/reference/engine/classes/Camera.yaml)

### Inferences
**Lens-to-FOV translation for Roblox.** Vertical FOV = 2·atan(12 mm / f), full-frame 36×24 sensor, computed:

| Film lens | 18 mm | 24 mm | 35 mm | 50 mm | 85 mm | 135 mm |
|---|---|---|---|---|---|---|
| Roblox FieldOfView (vertical) | ≈67° | ≈53° | ≈38° | ≈27° | ≈16° | ≈10° |

Roblox's default 70° is roughly a 17 mm wide-angle look. Close-ups on faces read better at 25–40° than at 70°.

**Spec package the agent should produce or receive per sequence:**
1. **Intent card:** name, emotional goal, what the player knows before and after, total length (first-time and repeat), skippable (Y/N), gameplay state changes and when they commit (server), and target devices.
2. **Beat sheet:**

   | Beat | Start–end (s) | Emotion/intent | Story/gameplay state |
   |---|---|---|---|

3. **Shot list:**

   | Shot | Start–end (s) | Size | Angle | Movement and path keys | FOV | DOF | Easing | Subject/framing |
   |---|---|---|---|---|---|---|---|---|

4. **Cue table (X-sheet):** one row per event.

   | t (s) or marker | Lane (CAM/ANIM/VFX/SFX/MUSIC/LIGHT/POST/UI/STATE) | Action | Params | End state if skipped |
   |---|---|---|---|---|

5. **Asset manifest:** every animation, sound, texture and mesh ID plus pool sizes, to feed `PreloadAsync` and the pools.
6. **Acceptance tests:**
   - At 60 and 240 FPS caps, no frame >16.7 ms (60 fps target) and no cue drift >1 frame.
   - Skip at any time restores the camera, UI and lighting and applies end states.
   - No `Instance.new`/`Clone`/`LoadAnimation`/Highlight creation during playback, checked by code review or instrumentation.
   - Works on mobile, where flipbooks may be disabled and glass refraction is missing.

**Worked example: "Transform_Red", first-time version (9.0 s). Timing values are design recommendations:**

| t (s) | Lane | Action | Params |
|---|---|---|---|
| 0.00 | UI | letterbox in | target 2.39:1, 0.5 s Quad Out |
| 0.00 | POST | ColorCorrection (Camera) | Saturation 0→−0.5 over 1.0 s |
| 0.00 | CAM | shot 1: medium, low angle, orbit 25° around player | FOV 60→55, 0–4.0 s, Sine InOut |
| 0.20 | SFX | rumble riser | 4.0 s, volume ramps up |
| 0.50 | VFX | AuraBuild_Red enable (inward ShapeInOut) | Rate ramps 20→120 by 3.5 s |
| 1.00 | VFX | RockLift module | 8 rocks, rise 2–6 studs over 3 s |
| 1.00 | CAM | shake sustain | trauma 0.1→0.35 by 3.8 s, noise speed 12 |
| 4.00 | CAM | shot 2: ECU eyes | FOV 25, hard cut |
| 4.00 | SFX/MUSIC | silence (duck all), heartbeat | duck 0.05 s |
| 4.00 | STATE | clock scale 0.1 (slow-mo) | until 4.5 s |
| 4.30 | ANIM marker "EyesIgnite" | Highlight outline Red on, Neon eyes | outline transparency 1→0 in 0.1 s |
| 4.50 | POST | impact frame B/W, then white | 0.05 s + 0.05 s |
| 4.50 | STATE | hitstop | 0.25 s (clock scale 0) |
| 4.60 | POST | white flash | Brightness 1→0 over 0.3 s |
| 4.60 | STATE | swap to pre-built Red model (inside flash) | visibility swap, no instantiation |
| 4.75 | VFX | Shockwave ring, crater decal, Burst_Red | Emit counts from attributes |
| 4.75 | CAM | trauma +0.9, FOV punch +14 | spring damping 0.6, 3 Hz |
| 5.00 | CAM | shot 3: hero low angle, slow push | FOV 45→40, 5.0–8.4 s |
| 5.20 | VFX | AuraIdle_Red loop | — |
| 5.50 | UI | title card "RED" in race font | in 0.3 s, hold 2 s, out 0.4 s |
| 8.40 | UI | letterbox out | 0.4 s |
| 8.40 | CAM | blend to gameplay | SmoothDamp smoothTime 0.25 |
| 9.00 | STATE | restore camera, controls, post-processing | end |

The repeat version keeps rows from 4.50 onward, re-timed to start at 0. The other five races reuse this table with `color`, `auraFlipbook`, `title` and `sfxSet` parameters (bank-footage principle).

### Gaps
- I found no published game-industry template that combines beat sheet, shot list and X-sheet for real-time engines. The package above merges film and animation conventions with Roblox APIs.
- No evidence was found on how well current LLM agents follow such tables in Roblox Studio via MCP. Validation should come from in-Studio playtests and MicroProfiler captures.
