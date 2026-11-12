"""Edit decision list for the SPACE montage (Sia - Snowman excerpt, 56 BPM, 12/8).

Beats are dotted quarters: kick on even beats, snare on odd beats.
    0-8    intro: four long nebula flights (cut on every kick)
    8-16   title: S-P-A-C-E, one letter per beat, then the word falls into a black hole
    16-32  montage: a cut on every beat, eighth-note triplet bursts closing each phrase
    32-end outro: supernova, then the solar system on a shuffle rhythm, then home
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import Shot  # noqa: E402

F_TITLE = "/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf"
F_SMALL = "/usr/share/fonts/opentype/inter/Inter-Medium.otf"

SQ4096 = "4096:2304:0:896"      # 16:9 band out of 4096x4096 sources
SQ3840 = "3840:2160:0:840"
ISS = "3840:2160:128:0"         # 4096x2160 -> 16:9

E = 1.0 / 3.0                   # one eighth note, in beats


def intro(sid, clip, t_in, k0, **kw):
    d = dict(step=1.0, ramp=1.2, ramp_tau=0.18, z0=1.02, z1=1.09, flash=1.1, zp=0.14,
             zo=0.26, fo=0.7, shake=0.003, accent=0.22, bloom=0.6)
    d.update(kw)
    return Shot(sid, clip, t_in, k0, k0 + 2, **d)


def letter(sid, clip, t_in, k0, **kw):
    d = dict(step=1.0, ramp=2.0, z0=1.03, z1=1.09, flash=1.5, zp=0.2, rays=0.55, bloom=0.6)
    d.update(kw)
    return Shot(sid, clip, t_in, k0, k0 + 1, **d)


def beat(sid, clip, t_in, k0, dur=1.0, **kw):
    d = dict(step=1.0, ramp=3.0, z0=1.03, z1=1.10, pulse=0.05)
    d.update(kw)
    return Shot(sid, clip, t_in, k0, k0 + dur, **d)


def trip(sid, clip, t_in, k0, **kw):
    d = dict(step=1.0, ramp=2.0, ramp_tau=0.08, z0=1.04, z1=1.09, flash=1.0, zp=0.12,
             shake=0.004, tout="none", ca=0.007)
    d.update(kw)
    return Shot(sid, clip, t_in, k0, k0 + E, **d)


def hit(sid, clip, t_in, k0, dur=1.0, **kw):
    """Strobe hit: big flash, then a calm drift."""
    d = dict(step=1.0, ramp=1.5, z0=1.03, z1=1.08, flash=2.0, zp=0.24, shake=0.008,
             tout="none", bloom=0.6)
    d.update(kw)
    return Shot(sid, clip, t_in, k0, k0 + dur, **d)


SHOTS = [
    # ------------------------------------------------------------- intro ---
    Shot("i0_deepfield", "webb__weic2603c.hd_1080p25_screen.mp4", 8.0, -0.5, 0, tin="fade", fade_in=0.3,
         step=1.5, exposure=1.7, z0=1.05, z1=1.12, zo=0.4, fo=1.0, bloom=0.7),
    intro("i1_orion", "hub__hubblecast106d.hd_1080p25_screen.mp4", 1.3, 0, flash=1.5, zp=0.2),
    intro("i2_pillars", "hub__heic1501g.ultra_hd.mp4", 1.0, 2),
    intro("i3_westerlund", "hub__heic1509e.hd_1080p25_screen.mp4", 27.6, 4),
    intro("i4_bubble", "hub__heic1608e.hd_1080p25_screen.mp4", 1.2, 6, zo=0.5, fo=1.2),

    # ------------------------------------------------------------- title ---
    letter("t1_S", "eso__eso2414b.ultra_hd.mp4", 1.0, 8),
    letter("t2_P", "eso__eso1615c.ultra_hd.mp4", 4.0, 9),
    letter("t3_A", "eso__eso1529a.ultra_hd.mp4", 13.2, 10),
    letter("t4_C", "hub__heic1209g.hd_1080p25_screen.mp4", 7.4, 11),
    letter("t5_E", "eso__eso2610b.ultra_hd.mp4", 2.0, 12),
    Shot("t6_blackhole", "eso__black-hole-material.ultra_hd.mp4", 0.6, 13, 16, step=1.0, ramp=2.0,
         flash=1.8, zp=0.2, exposure=0.62, bloom=0.4, streak=0.15, tout="none", accent=0.18,
         keys=[(0.0, 1.04, 0.5, 0.5), (0.64, 1.13, 0.5, 0.5, "lin"), (1.0, 14.0, 0.84, 0.21, "in")]),

    # ----------------------------------------------------------- montage ---
    # bar 1 (beats 16-20): violent stars, ending on a triplet of the Sun
    beat("b01_kilonova", "eso__eso1733b.ultra_hd.mp4", 30.2, 16, step=1.3, ramp=4.0, flash=2.6, zp=0.3,
         shake=0.012, pulse=0.0),
    beat("b02_magnetar", "eso__eso2403b.ultra_hd.mp4", 11.6, 17, tin="whip_l"),
    beat("b03_quasar_blue", "eso__eso1229a.ultra_hd.mp4", 0.6, 18, tin="spin_r"),
    trip("b04a_sun", "nasa__sun_ballet.mp4", 5.0, 19),
    trip("b04b_sun", "nasa__sun_march7.mp4", 2.0, 19 + E),
    trip("b04c_sun", "nasa__sun_trebuchet.mp4", 5.5, 19 + 2 * E, tout="zoom"),
    # bar 2 (beats 20-24): other worlds
    beat("b05_rogue", "eso__eso2120b.ultra_hd.mp4", 0.4, 20),
    beat("b06_trappist", "eso__eso1615b.ultra_hd.mp4", 2.0, 21, tin="whip_r"),
    beat("b07_rings", "hub__heic2021b.ultra_hd.mp4", 6.0, 22, tin="spin_l"),
    trip("b08a_field", "eso__eso2606b.ultra_hd.mp4", 2.0, 23),
    trip("b08b_blue", "hub__heic1312a.hd_1080p25_screen.mp4", 13.0, 23 + E),
    trip("b08c_mars", "eso__eso1509a.ultra_hd.mp4", 3.0, 23 + 2 * E, tout="zoom"),
    # bar 3 (beats 24-28): the outer solar system
    beat("b09_triton", "eso__eso1015a.hd_1080p25_screen.mp4", 2.0, 24),
    beat("b10_saturn_pole", "hub__heic1815a.hd_1080p25_screen.mp4", 2.0, 25, tin="whip_u"),
    beat("b11_europa", "hub__heic1322b.hd_1080p25_screen.mp4", 10.0, 26, tin="spin_r"),
    trip("b12a_comet", "eso__eso2106c.ultra_hd.mp4", 20.0, 27),
    trip("b12b_asteroid", "eso__eso2107c.ultra_hd.mp4", 5.4, 27 + E),
    trip("b12c_tail", "eso__cs0025c.ultra_hd.mp4", 2.0, 27 + 2 * E, tout="zoom"),
    # bar 4 (beats 28-32): black holes
    beat("b13_gold_hole", "eso__eso1907f.ultra_hd.mp4", 6.0, 28),
    beat("b14_quasar", "eso__eso2402b.ultra_hd.mp4", 1.5, 29, tin="whip_l"),
    beat("b15_binary", "nasa__bh_binary_main_4k.mp4", 40.3, 30, crop="2560:1440:686:1287", ramp=1.5,
         z0=1.0, z1=1.06, zp=0.14),
    trip("b16a_spaghetti", "eso__eso2018b.ultra_hd.mp4", 13.0, 31),
    trip("b16b_spiral", "nasa__smbh_thin0.mp4", 0.5, 31 + E),
    trip("b16c_disk", "nasa__bh_disk_360_4k.mp4", 13.0, 31 + 2 * E, crop=SQ3840, tout="zoom", zo=0.5, fo=1.3),

    # ------------------------------------------------------------- outro ---
    # the hook: a supernova on the downbeat
    Shot("c01_supernova", "nasa__supernova_4k.mp4", 6.5, 32, 34, step=2.5, ramp=9.0, ramp_tau=0.35,
         flash=2.8, zp=0.3, shake=0.012, z0=1.02, z1=1.12, accent=0.3, bloom=0.7),
    beat("c02_vela", "eso__eso2214a.ultra_hd.mp4", 6.0, 34, pulse=0.0, tout="none"),
    # shuffle rhythm (beat, pickup eighth, beat): the solar system, one body per hit
    hit("c03_sun", "nasa__sun_cme304_4k.mp4", 16.0, 35, 2 * E, crop=SQ4096, step=2.0, z0=1.0, z1=1.06),
    hit("c04_jupiter", "hub__heic1914b.ultra_hd.mp4", 1.0, 35 + 2 * E, E, flash=1.2, zp=0.14),
    hit("c05_redspot", "hub__heic1914b.ultra_hd.mp4", 21.0, 36),
    hit("c06_saturn", "hub__heic1814b.hd_1080p25_screen.mp4", 5.2, 37, 2 * E),
    hit("c07_moon", "nasa__moontour.mp4", 272.5, 37 + 2 * E, E, flash=1.2, zp=0.14),
    hit("c08_crater", "nasa__moontour.mp4", 124.0, 38),
    hit("c09_peak", "nasa__moontour.mp4", 134.2, 39, tout="zoom"),
    # the hook returns: home, seen from the ISS
    beat("c10_iss_day", "nasa__iss_1150.mp4", 38.0, 40, crop=ISS, pulse=0.0, z0=1.17, z1=1.24,
         c0=(0.62, 0.40)),
    beat("c11_iss_clouds", "nasa__iss_2170.mp4", 9.0, 41, crop=ISS, pulse=0.0, tin="whip_r"),
    beat("c12_iss_aurora", "nasa__iss_2840.mp4", 2.0, 42, crop=ISS, pulse=0.0),
    beat("c13_iss_night", "nasa__iss_2245.mp4", 2.6, 43, crop=ISS, pulse=0.0, tin="whip_l"),
    beat("c14_iss_sunrise", "nasa__iss_168.mp4", 8.6, 44, crop=ISS, pulse=0.0, tout="none"),
    # last four beats, pulling away from Earth
    hit("c15_limb", "hub__hubble_earth_4k_rising.ultra_hd.mp4", 28.5, 45),
    hit("c16_globe", "eso__eso1729b.ultra_hd.mp4", 1.0, 46),
    hit("c17_earthrise", "nasa__earthrise.mp4", 128.0, 47),
    Shot("c18_home", "eso__eso1712a.ultra_hd.mp4", 0.3, 48, 50, step=0.5, ramp=1.0, flash=2.0, zp=0.16,
         tout="none", bloom=0.6,
         keys=[(0.0, 1.62, 0.665, 0.60), (1.0, 1.30, 0.665, 0.60, "out")]),
]

# a shot that precedes a whip leaves in the same direction
for a, b in zip(SHOTS, SHOTS[1:]):
    if b.tin.startswith(("whip", "spin")) and a.tout == "zoom":
        a.tout = "whip"

TITLE = dict(word="SPACE", font=F_TITLE, size=0.105, tracking=0.62, y=0.5,
             beats=[8, 9, 10, 11, 12], full=13, exit=15.0, end=15.92, exit_to=(0.5, 0.5),
             alpha_pre=0.82)

CREDIT = dict(text="FOOTAGE   NASA  ·  ESA/HUBBLE  ·  STScI  ·  ESO (M. KORNMESSER, L. CALÇADA)", font=F_SMALL,
              size=0.0105, tracking=0.26, y=0.928, t0=52.25, t1=54.0, level=0.5)
FADE_OUT = 1.0
