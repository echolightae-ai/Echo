"""Where every previously-missing file goes. id -> event slug. Reasons are kept so nothing disappears silently.
Judged from phone photo numbering (IMG_####), capture date/GPS, and what the frame shows."""
ASSIGN = {
 # night of wonder (RAK)
 "V0": "night-of-wonder-rak", "V1": "night-of-wonder-rak", "V2": "night-of-wonder-rak", "V4": "night-of-wonder-rak", "V98": "night-of-wonder-rak",
 "V5": "building-the-ballroom",
 # 3D mapping: wedding / gala / government / launch examples, cars
 "V100": "projection-mapping-showcase", "V104": "projection-mapping-showcase", "V106": "projection-mapping-showcase", "V102": "projection-mapping-showcase",
 "V108": "projection-mapping-showcase", "V111": "projection-mapping-showcase", "V119": "projection-mapping-showcase", "V123": "projection-mapping-showcase",
 "V126": "projection-mapping-showcase", "V128": "projection-mapping-showcase", "I134": "projection-mapping-showcase",
 "V115": "3d-mapping-on-a-car", "V116": "3d-mapping-on-a-car", "V117": "3d-mapping-on-a-car", "V118": "3d-mapping-on-a-car", "I121": "3d-mapping-on-a-car",
 # sky beams / new year
 "V103": "new-year-countdown-sky-beams-rak", "V41": "new-year-countdown-sky-beams-rak",
 # celebration night + same ballroom
 "V11": "sheraton-corniche-celebration-night", "V17": "sheraton-corniche-celebration-night", "V18": "sheraton-corniche-celebration-night", "V19": "sheraton-corniche-celebration-night",
 "V20": "sheraton-corniche-celebration-night", "V21": "sheraton-corniche-celebration-night", "V22": "sheraton-corniche-celebration-night", "I16": "sheraton-corniche-celebration-night",
 # neighbours by photo number
 "I15": "luxury-wedding-al-dhaid",
 "I122": "corporate-stage-designs", "I123": "corporate-stage-designs", "I124": "corporate-stage-designs", "I31": "corporate-stage-designs", "V113": "corporate-stage-designs",
 "V114": "laser-mapping-on-an-led-video-wall",
 "V35": "millennium-al-rawdah-beam-effects", "V36": "millennium-al-rawdah-beam-effects",
 "I29": "bab-al-qasr-bridal-entrance", "I30": "bab-al-qasr-bridal-entrance",
 "I34": "concert-scale-lighting-conference", "I37": "concert-scale-lighting-conference", "I40": "concert-scale-lighting-conference", "I45": "concert-scale-lighting-conference", "I47": "concert-scale-lighting-conference",
 "I125": "moving-bridal-walk-sheraton-corniche", "I126": "moving-bridal-walk-sheraton-corniche", "I127": "moving-bridal-walk-sheraton-corniche", "I128": "moving-bridal-walk-sheraton-corniche",
 "V44": "floral-wedding-brought-to-life", "V45": "floral-wedding-brought-to-life", "V46": "floral-wedding-brought-to-life", "V47": "floral-wedding-brought-to-life", "V48": "floral-wedding-brought-to-life",
 "V49": "floral-wedding-brought-to-life", "V50": "floral-wedding-brought-to-life", "V51": "floral-wedding-brought-to-life", "I80": "floral-wedding-brought-to-life", "I6": "floral-wedding-brought-to-life", "I120": "floral-wedding-brought-to-life",
 "V57": "garden-wedding-light-show-cold-sparks", "I130": "garden-wedding-light-show-cold-sparks",
 "V60": "light-to-the-violin", "V65": "al-nayef-group-awards-night", "I103": "wedding-stage-lighting-effects", "V110": "wedding-stage-lighting-effects",
 "I5": "emirati-kuwaiti-womens-forum", "I7": "led-screens-that-set-the-scene", "V112": "led-screens-that-set-the-scene", "V121": "led-screens-that-set-the-scene",
 "V122": "she-leads-series",
 # sorted into the catch-all until the owner places them
 "I19": "more-from-our-events", "V24": "more-from-our-events", "V25": "more-from-our-events", "V40": "more-from-our-events", "I92": "more-from-our-events", "I93": "more-from-our-events",
 "I136": "more-from-our-events", "I9": "more-from-our-events", "I12": "more-from-our-events", "V109": "more-from-our-events", "V125": "more-from-our-events", "V7": "more-from-our-events", "V99": "more-from-our-events",
}
# clip-level services for restored files (None = inherit the event's primary service)
SVC = {**{k: ["mapping"] for k in ("V100", "V104", "V106", "V102", "V108", "V111", "V119", "V123", "V126", "V128", "I134", "V115", "V116", "V117", "V118", "I121")},
       "V112": ["led"], "V121": ["led"], "I7": ["led"], "I122": ["led"], "I123": ["led"], "I124": ["led"], "V113": ["led"], "V114": ["led"], "V109": ["led"], "V99": ["led"],
       "V41": ["laser"], "V103": ["laser"], "I130": ["laser"], "V65": ["laser"]}
SKIP = {  # id -> reason (kept for the coverage report)
 "V101": "exact duplicate of V100", "V105": "exact duplicate of V104", "V124": "exact duplicate of V123", "V127": "exact duplicate of V126",
 "V120": "lower-res copy of the laser-on-LED-wall film (N1)", "V107": "lower-res copy of the hotel facade film (V9)",
 "I8": "Instagram screenshot", "I12x": "",
 "I129": "exact duplicate of a placed photo", "I131": "exact duplicate of a placed photo", "I132": "exact duplicate of a placed photo", "I133": "exact duplicate of a placed photo", "I135": "exact duplicate of a placed photo", "I137": "exact duplicate of a placed photo",
}
