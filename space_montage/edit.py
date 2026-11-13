"""Edit decision list for the SPACE montage, second cut (Sia - Snowman excerpt, 56 BPM, 12/8).

Beats are dotted quarters. Every cut sits on a drum hit of the track: kicks on the even
beats, snares on the odd ones, plus the snare pick-ups detected between the beats
(16.45, 18.71, 23.64, 24.40, 24.65, 26.36 ...), which is where the short cuts live.

    0-8     leaving home: sunrise from the ISS, city lights, aurora, the Moon, Earthrise, the Sun, warp
    8-14    S-P-A-C-E, one letter per beat, each letter standing behind the world it crosses
    14-15   the word falls into a black hole and settles on its photon ring
    15-16   signature: the ring condenses into the channel name, spoken once
    16-34   the other side: star birth, star death, galaxies, deep fields, a supernova
    34-40   the black hole again, slowly: simulation, then the two real images (M87*, Sgr A*)
    40-45   the way home: Pluto, Neptune, Uranus, Saturn, Jupiter, Mars, the Moon, Earth
    45-end  low orbit, aurora, and the opening sunrise run backwards as a sunset
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from engine import STILLS, Clip, Cut, Dissolve, Iris, Punch, Spin, Whip, Zoom  # noqa: E402
import overlays as ov  # noqa: E402

FONT = os.environ.get("SM_FONT", os.path.join(HERE, "fonts", "Unbounded-VF.ttf"))
ISS = "3840:2160:128:0"         # 4096x2160 -> 16:9
BAR = 0.128                     # letterbox bar (2.39:1), as a fraction of the frame height


def obj(src, cx, cy, r, R):
    """Camera that shows an object of a still (centre cx, cy and radius r, in image widths) R frame widths big."""
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    sw, sh = Image.open(os.path.join(STILLS, src)).size
    z = max(R * min(sw, sh * 16.0 / 9.0) / (r * sw), 1.0)
    return z, (cx, cy)


def ring(cid, src, k0, k1, cx, cy, r, R=0.356, grow=1.05, **kw):
    z, c = obj(src, cx, cy, r, R)
    return Clip(cid, src, k0, k1, z=(z, z * grow), c=c, **kw)


NIGHT = dict(sharpen=0.12, black=0.022)                     # high-ISO footage from the station: bury its noise floor
FLASH = dict(flash=0.8, punch=0.05, post=0.14)              # the hard cut used inside strobes and match cuts

# planet discs are pre-registered (tools/planets.py): the same camera frames every one of them
TOUR0, TOUR1 = 40.0, 45.0


def planet(cid, name, k0, k1, tin, **kw):
    za, zb = (1.0 + 0.17 * (k - TOUR0) / (TOUR1 - TOUR0) for k in (k0, k1))
    return Clip(cid, f"pl__{name}.jpg", k0, k1, z=(za, zb), c=(0.5, 0.5), tin=tin, bloom=0.35, streak=0.0, **kw)


OCC = {  # what hides the title letters in each shot (tools/fitdisc.py)
    "t1_S": dict(discs=[[(0.0, 0.6566, 1.0499, 0.8554), (0.3077, 0.6315, 1.0335, 0.8316), (0.9692, 0.5775, 0.9983, 0.7804), (1.0, 0.575, 0.9967, 0.778)]]),
    "t2_P": dict(discs=[[(0.0, 0.6927, 0.887, 0.675), (0.3438, 0.699, 0.8931, 0.6847), (0.9688, 0.7105, 0.9042, 0.7024), (1.0, 0.7111, 0.9048, 0.7033)]]),
    "t3_A": dict(discs=[[(0.0, 0.8242, 0.3135, 0.2899), (0.3438, 0.8413, 0.3094, 0.2887), (0.9688, 0.8724, 0.3019, 0.2865), (1.0, 0.874, 0.3015, 0.2864)]]),
    "t4_C": dict(discs=[[(0.0, 1.0095, 0.2422, 0.3385), (0.3385, 1.0278, 0.2458, 0.3387), (0.9692, 1.0619, 0.2526, 0.3391), (1.0, 1.0636, 0.2529, 0.3391)]]),
    "t5_E": dict(soft=0.006, horizons=[[
        (0.0, 0.2738, 0.1175, -0.0886), (0.1719, 0.28546, 0.06356, -0.01815), (0.2734, 0.29235, 0.03169, 0.02344),
        (0.375, 0.2963, 0.02054, 0.03878), (0.4766, 0.29873, 0.01039, 0.0564), (0.5781, 0.2988, 0.00686, 0.06794),
        (0.6797, 0.29771, 0.00406, 0.07864), (0.7812, 0.29592, 0.00215, 0.08943), (0.8828, 0.29401, -0.00093, 0.10155),
        (0.9844, 0.29203, -0.00574, 0.11581), (1.0, 0.2917, -0.0065, 0.118)]]),
}
LETTER = dict(punch=0.16, flash=1.0)

STROBE_SRC = ["hub__heic0715a.jpg", "hub__heic1808a.jpg", "eso__eso1520a.jpg", "hub__heic0910h.jpg", "webb__weic2219a.jpg",
              "hub__heic0503a.jpg", "hub__heic1520a.jpg", "webb__weic2425a.jpg", "hub__heic1007a.jpg"]
STROBE = [Clip(f"m{25 + i}_strobe", src, 31.13 + i * 0.87 / len(STROBE_SRC), 31.13 + (i + 1) * 0.87 / len(STROBE_SRC),
               z=(1.0 + 0.045 * i, 1.05 + 0.045 * i), c=(0.5, 0.5), tin=Cut(punch=0.05, post=0.08))
          for i, src in enumerate(STROBE_SRC)]

CLIPS = [
    # ---------------------------------------------------------- leaving home ---
    # real footage only: the film opens on the light coming over the edge of the Earth
    Clip("a1_sunrise", "nasa__iss_168.mp4", -0.42, 1, crop=ISS, t_in=8.4, speed=2.0, snare=0.7, **NIGHT,
         keys=[(0.0, 1.14, 0.47, 0.45, -1.5), (1.0, 1.22, 0.47, 0.45, -0.5)]),
    Clip("a2_sunrise", "nasa__iss_168.mp4", 1, 2, crop=ISS, t_in=11.47, speed=1.0, snare=0.7, **NIGHT,
         keys=[(0.0, 1.46, 0.40, 0.44, -0.5), (1.0, 1.56, 0.40, 0.44, 0.5)], tin=Punch(punch=0.08, flash=0.7, post=0.3)),
    Clip("a3_cities", "nasa__iss_2245.mp4", 2, 3, crop=ISS, t_in=3.2, speed=[(0.0, 5.0), (0.3, 2.0), (1.0, 1.2)],
         z=(1.10, 1.18), c=(0.5, 0.42), exposure=1.5, tin=Whip("u"), **NIGHT),
    Clip("a4_aurora", "nasa__iss_2840.mp4", 3, 4, crop=ISS, t_in=1.5, speed=[(0.0, 5.0), (0.3, 2.0), (1.0, 1.2)],
         z=(1.08, 1.16), c=(0.5, 0.5), exposure=1.3, tin=Whip("l"), **NIGHT),
    Clip("a5_moon", "nasa__moontour.mp4", 4, 4.84, t_in=120.6, speed=[(0.0, 4.0), (0.4, 1.5), (1.0, 1.0)],
         z=(1.05, 1.13), c=(0.5, 0.5), tin=Zoom("in")),
    Clip("a6_earthrise", "nasa__as08-14-2383.jpg", 4.84, 6,
         keys=[(0.0, 1.07, 0.50, 0.655, 6.5), (1.0, 1.20, 0.535, 0.625, 6.5, "out")], tin=Whip("u")),
    Clip("a7_sun", "nasa__sun_ballet.mp4", 6, 7, t_in=3.4, speed=[(0.0, 9.0), (0.3, 4.0), (1.0, 3.0)], z=(1.0, 1.08),
         c=(0.45, 0.5), bloom=0.7,
         tin=Punch(punch=0.22, flash=1.3)),
    # leaving: a real field of stars (Webb), the camera accelerating into it until the stars streak
    Clip("a8_warp", "webb__potm2409a.jpg", 7, 8, keys=[(0.0, 1.15, 0.5, 0.5, 0.0), (1.0, 4.2, 0.5, 0.5, 14.0, "in")],
         exposure=1.25, bloom=0.8, tin=Zoom("in", at=(0.42, 0.5))),

    # ---------------------------------------------------------------- title ---
    Clip("t1_S", "eso__eso2414b.ultra_hd.mp4", 8, 9, t_in=1.0, speed=2.4, z=(1.60, 1.70), c=(0.69, 0.435), occ=OCC["t1_S"],
         tin=Zoom("in", s_in=1.9, post=0.30, flash=1.0)),
    Clip("t2_P", "eso__eso1615c.ultra_hd.mp4", 9, 10, t_in=4.0, speed=2.4, z=(1.15, 1.22), c=(0.55, 0.44), occ=OCC["t2_P"],
         tin=Punch(**LETTER)),
    Clip("t3_A", "eso__eso1529a.ultra_hd.mp4", 10, 11, t_in=16.5, speed=2.4, z=(1.40, 1.48), c=(0.372, 0.5), occ=OCC["t3_A"],
         tin=Punch(**LETTER)),
    Clip("t4_C", "hub__heic1916b.ultra_hd.mp4", 11, 12, t_in=5.0, speed=1.2, z=(1.8, 1.9), c=(0.304, 0.5), occ=OCC["t4_C"],
         tin=Punch(**LETTER)),
    Clip("t5_E", "hub__heic1209g.hd_1080p25_screen.mp4", 12, 14, t_in=6.6, speed=0.45, occ=OCC["t5_E"],
         keys=[(0.0, 1.16, 0.5, 0.447, 0.0), (1.0, 1.22, 0.5, 0.482, 0.0)], tin=Punch(punch=0.16, flash=0.55)),
    # the black hole, seen as the camera crosses the plane of its disc
    Clip("t6_hole", "nasa__bh_approach_4k.mp4", 14, 15, t_in=7.55, speed=2.0, exposure=0.85, streak=0.0,
         keys=[(0.0, 1.75, 0.5, 0.5, 0.0), (1.0, 2.45, 0.5, 0.5, 0.0, "in")], tin=Punch(punch=0.2, flash=0.7, post=0.3)),

    # ------------------------------------------------------------ signature ---
    Clip("s1_signature", "nasa__bh_upclose_4k.mp4", 15, 16, t_in=2.0, speed=2.0, z=(1.06, 1.12), c=(0.5, 0.47),
         streak=0.0, exposure=0.9, tin=Zoom("in", s_out=3.2, s_in=0.86, pre=0.14, post=0.30, flash=0.0, dark=0.85)),

    # --------------------------------------------------- star birth (16-20) ---
    Clip("m01_cliffs", "webb__carinanebula3.jpg", 16, 17, keys=[(0.0, 1.55, 0.44, 0.56, -2.0), (1.0, 1.32, 0.46, 0.54, 0.0, "out")],
         tin=Iris(at=(0.5, 0.5), dur=0.40, ease="out", rim=2.2, flash=1.0, post=0.4, punch=0.2)),
    Clip("m02_pillars", "webb__weic2216b.jpg", 17, 18, z=(1.05, 1.13), c=(0.5, 0.60), c1=(0.5, 0.52), tin=Whip("u")),
    Clip("m03_tarantula", "webb__weic2212a.jpg", 18, 18.71, z=(1.25, 1.42), c=(0.5, 0.47), rot=(0.0, 3.0), tin=Spin(55)),
    Clip("m04_spire", "webb__weic2518a.jpg", 18.71, 20, z=(1.0, 1.10), c=(0.5, 0.64), c1=(0.5, 0.58), tin=Zoom("in")),

    # --------------------------------------------------- star death (20-24) ---
    Clip("m05_crab", "webb__weic2417a.jpg", 20, 21, z=(1.02, 1.13), c=(0.5, 0.5), rot=(-2.0, 1.0), tin=Zoom("out")),
    Clip("m06_casA", "webb__weic2330a.jpg", 21, 22, z=(1.0, 1.10), c=(0.5, 0.5), tin=Whip("r")),
    # three planetary nebulae, registered on each other: the ring stays, the nebula changes
    ring("m07_helix", "eso__eso0907a.jpg", 22, 23, 0.506, 0.502, 0.347, rot=(-4.0, 0.0), tin=Spin(-60)),
    ring("m08_ring", "hub__heic1310a.jpg", 23, 23.64, 0.502, 0.483, 0.356, tin=Cut(**FLASH)),
    ring("m09_southern_ring", "webb__weic2207a.jpg", 23.64, 24, 0.230, 0.542, 0.166, grow=1.03, tin=Cut(**FLASH)),

    # ----------------------------------------------------- galaxies (24-28) ---
    Clip("m10_whirlpool", "hub__heic0506a.jpg", 24, 24.40, z=(1.45, 1.52), c=(0.39, 0.484), rot=(0.0, 1.5), tin=Zoom("in", post=0.24)),
    Clip("m11_spiral", "webb__potm2412a.jpg", 24.40, 24.65, z=(1.05, 1.08), c=(0.507, 0.53), tin=Cut(**FLASH)),
    Clip("m12_spiral", "webb__potm2502a.jpg", 24.65, 25, z=(1.05, 1.09), c=(0.529, 0.432), tin=Cut(**FLASH)),
    Clip("m13_phantom", "webb__potm2208a.jpg", 25, 26, z=(1.10, 1.22), c=(0.459, 0.45), rot=(0.0, 6.0), tin=Spin(50)),
    Clip("m14_sombrero", "hub__opo0328a.jpg", 26, 26.36, z=(1.10, 1.15), c=(0.496, 0.492), tin=Zoom("out", post=0.24)),
    Clip("m15_ngc1300", "hub__opo0501a.jpg", 26.36, 26.89, z=(1.0, 1.06), c=(0.488, 0.468), tin=Cut(**FLASH)),
    Clip("m16_antennae", "hub__potw1345a.jpg", 26.89, 27.15, z=(1.0, 1.04), c=(0.55, 0.40), tin=Cut(**FLASH)),
    Clip("m17_spiral", "webb__potm2602a.jpg", 27.15, 28, z=(1.02, 1.12), c=(0.485, 0.509), rot=(0.0, -3.0), tin=Whip("l")),

    # ------------------------------------------- groups and deep fields (28-32) ---
    Clip("m18_quintet", "webb__weic2208a.jpg", 28, 28.35, z=(1.12, 1.18), c=(0.5, 0.46), tin=Zoom("in", post=0.24)),
    Clip("m19_cartwheel", "webb__weic2211a.jpg", 28.35, 29, z=(1.0, 1.08), c=(0.55, 0.53), tin=Cut(**FLASH)),
    Clip("m20_pair", "webb__weic2426a.jpg", 29, 29.38, z=(1.0, 1.05), c=(0.5, 0.5), tin=Whip("r", post=0.26)),
    Clip("m21_penguin", "webb__weic2420a.jpg", 29.38, 29.68, z=(1.0, 1.04), c=(0.5, 0.42), tin=Cut(**FLASH)),
    Clip("m22_arcs", "webb__potm2609a.jpg", 29.68, 30, z=(1.0, 1.05), c=(0.5, 0.45), tin=Cut(**FLASH)),
    Clip("m23_deep_field", "webb__weic2209a.jpg", 30, 30.66, z=(1.0, 1.16), c=(0.5, 0.5), ease="in", tin=Zoom("in")),
    Clip("m24_spiral", "webb__potm2411a.jpg", 30.66, 31.13, z=(1.02, 1.12), c=(0.523, 0.52), tin=Whip("l", post=0.26)),
    # everything at once: nine nebulae in under a second, each one closer than the last
    *STROBE,

    # ------------------------------------------------------- supernova (32-34) ---
    # a star dies on the downbeat: twenty-three seconds of the simulation in two beats, from the flash to the
    # remnant, whose core ends where the black hole of the next shot will be
    Clip("x1_supernova", "nasa__supernova_4k.mp4", 32, 34, t_in=6.3, speed=[(0.0, 20.0), (0.3, 12.0), (1.0, 4.5)],
         keys=[(0.0, 1.0, 0.5, 0.5, 0.0), (1.0, 1.5, 0.504, 0.561, 0.0, "io")], bloom=0.6,
         tin=Cut(flash=1.2, punch=0.15, post=0.3)),

    # -------------------------------------------------- the black hole (34-40) ---
    Clip("h1_hole", "nasa__bh_pullback_4k.mp4", 34, 36.1, t_in=5.0, speed=2.0, z=(1.28, 1.02), ease="out", c=(0.5, 0.5), snare=0.6,
         streak=0.0, exposure=0.9, tin=Dissolve(0.5, glow=0.5)),
    # the two black holes that have actually been photographed, on the quietest bars of the track
    ring("h2_m87", "eso__eso1907a.jpg", 36.1, 37, 0.494, 0.496, 0.116, R=0.175, grow=1.06, snare=0.5, bloom=0.4,
         tin=Dissolve(0.7, glow=0.2)),
    ring("h3_sgra", "pad__sgra.jpg", 37, 38, 0.4887, 0.503, 0.1749, R=0.175, grow=1.06, snare=0.5, bloom=0.4,
         border="black", tin=Cut(flash=0.5, punch=0.03, post=0.2)),
    Clip("h4_disc", "eso__black-hole-material.ultra_hd.mp4", 38, 40, t_in=1.0, speed=2.4, snare=0.7, exposure=0.9,
         keys=[(0.0, 1.05, 0.5, 0.5, 0.0), (0.5, 1.30, 0.62, 0.36, 0.0, "io"), (1.0, 6.0, 0.875, 0.145, 0.0, "in")],
         tin=Zoom("out", flash=0.6)),

    # ---------------------------------------------------- the way home (40-45) ---
    planet("e1_pluto", "pluto", 40, 40.71, Iris(at=(0.5, 0.5), dur=0.36, ease="out", rim=2.0, flash=0.8)),
    planet("e2_neptune", "neptune", 40.71, 41, Cut(**FLASH)),
    planet("e3_uranus", "uranus", 41, 41.52, Cut(**FLASH)),
    planet("e4_saturn", "saturn", 41.52, 42, Cut(**FLASH)),
    planet("e5_jupiter", "jupiter", 42, 42.46, Cut(flash=1.1, punch=0.08, post=0.16)),
    planet("e6_jupiter_ir", "jupiterw", 42.46, 42.92, Cut(**FLASH)),
    planet("e7_mars", "mars", 42.92, 43.45, Cut(**FLASH)),
    planet("e8_moon", "moon", 43.45, 43.91, Cut(**FLASH)),
    planet("e9_earth", "earth", 43.91, 45, Cut(flash=1.0, punch=0.07, post=0.18)),

    # ------------------------------------------------------------ home (45-end) ---
    Clip("f1_orbit", "nasa__iss_2170.mp4", 45, 46, crop=ISS, t_in=5.0, speed=[(0.0, 5.0), (0.3, 2.0), (1.0, 1.2)],
         z=(1.06, 1.14), c=(0.5, 0.45), tin=Zoom("in", s_in=1.8, flash=0.9)),
    Clip("f2_aurora", "nasa__iss_1225.mp4", 46, 47, crop=ISS, t_in=7.6, speed=[(0.0, 5.0), (0.3, 2.0), (1.0, 1.2)],
         z=(1.08, 1.16), c=(0.52, 0.45), exposure=1.15, tin=Whip("u"), **NIGHT),
    Clip("f3_sunset", "nasa__iss_168_rev.mp4", 47, 50.5, crop=ISS, t_in=0.3, speed=[(0.0, 3.4), (0.3, 2.9), (1.0, 2.6)],
         keys=[(0.0, 1.22, 0.47, 0.45, -0.5), (1.0, 1.12, 0.47, 0.45, -1.5)], kick=0.0, snare=0.5,
         tin=Dissolve(0.45, glow=0.7), **NIGHT),
]

for _c in CLIPS:                                   # the drums push the montage harder than the calm parts
    if _c.id[0] in "mx":
        _c.kick, _c.snare = 1.15 * _c.kick, 1.15 * _c.snare

KICKS = [(0, .6), (2, .95), (4, .7), (6, 1.), (8, .6), (10, .9), (12, .5), (14, .9), (16, .8), (18, 1.), (20, .7), (22, 1.),
         (24, .9), (26, .9), (28, .7), (29.68, .6), (30, 1.), (32, .9), (34, .8), (36.1, .6), (38, 1.), (40, .8), (42, .9),
         (44, .6), (46, 1.)]
SNARES = [(0.99, .9), (3, .8), (3.65, .7), (4.34, .7), (4.84, .9), (7, 1.), (7.61, 1.), (9, .8), (11, .7), (14, .8), (15, 1.),
          (16.45, .8), (17, .7), (18.71, .8), (21, .8), (23, .9), (23.64, .8), (24, .7), (24.40, .8), (24.65, .9), (25, .8),
          (26.36, .7), (26.89, .8), (27.15, .9), (28, .7), (28.35, 1.), (29, .9), (29.38, .9), (30.66, 1.), (31.13, .8),
          (31.73, .7), (33, .8), (33.32, .7), (34.13, .8), (34.34, .7), (35, .9), (35.73, 1.), (37, .9), (39, .9),
          (39.66, 1.), (40.71, .8), (41, 1.), (41.52, .7), (42, .9), (42.92, .7), (43.91, .7), (44.13, .8), (45, .9), (47, 1.)]
HITS = [(k, "k", s) for k, s in KICKS] + [(k, "s", s) for k, s in SNARES]

GRADE = dict(sat=1.12, contrast=0.26, sharpen=0.35, halation=0.45)

TAG_ENV = os.environ.get("SM_TAG_ENV", os.path.join(HERE, "voice", "song_tag.json"))
CREDIT = "FOOTAGE   NASA  ·  ESA/HUBBLE  ·  ESA/WEBB, CSA, STScI  ·  ESO/M. KORNMESSER  ·  EHT COLLABORATION"


def overlays(r):
    # scope bars for the quiet parts; the frame opens on both drops (beats 16 and 40)
    box = ov.Letterbox(r, [(-1, BAR, 0.0), (16, 0.0, 0.30), (34, BAR, 0.9), (40, 0.0, 0.30), (47, BAR, 1.2)])
    return [
        ov.Title(r, "SPACE", FONT, axes=dict(wght=800), size=0.150, tracking=0.10, y=0.47, hole=(0.5, 0.5),
                 ring=0.093, ring_z=(1.76, 2.5)),
        ov.Signature(r, "Reditor", FONT, axes=dict(wght=800), size=0.092, tracking=0.0, at=(0.5, 0.5), ring=0.17,
                     relax=0.44, env_json=TAG_ENV),
        ov.EndCard(r, [
            dict(text="REDITOR", font=FONT, axes=dict(wght=700), size=0.0190, tracking=0.75, y=0.455, level=0.9),
            dict(text=CREDIT, font=FONT, axes=dict(wght=400), size=0.0066, tracking=0.30, y=0.158, level=0.5),
        ], beat=47.45, fade=0.7),
        box,
        ov.Mark(r, "REDITOR", FONT, axes=dict(wght=600), size=0.0100, tracking=0.55, beat=16.4, until=47.0, box=box),
        ov.Fade(r, fade_in=0.42, fade_out=1.1),
    ]
