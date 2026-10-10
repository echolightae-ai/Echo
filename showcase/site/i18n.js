/* Copy, keywords and recommendation logic. English + Arabic (RTL). */
window.EVENTS = ["corporate", "wedding", "cultural", "launch"];
window.SERVICES = ["lighting", "led", "sound", "mapping", "laser"];

/* beam palettes per event (also used by the hero) */
window.PALETTE = {
  default:   ["#2bc4e0", "#5b7cff", "#b46bff", "#ffffff"],
  corporate: ["#3da9ff", "#7fd8ff", "#ffffff", "#5b7cff"],
  wedding:   ["#ffb86b", "#ff7aa8", "#fff1d6", "#ffd27a"],
  cultural:  ["#2ee59d", "#ff4d5e", "#ffffff", "#2ee59d"],
  launch:    ["#c04dff", "#ff3df0", "#3dd6ff", "#ffffff"]
};

/* default recommendation per event, in priority order */
window.RECO = {
  corporate: ["led", "sound", "lighting", "laser"],
  wedding:   ["lighting", "laser", "led", "sound"],
  cultural:  ["laser", "mapping", "lighting", "led"],
  launch:    ["mapping", "led", "laser", "lighting"]
};

/* free-text understanding: lowercase substrings, English + Arabic */
window.KW = {
  events: {
    corporate: ["corporate","conference","summit","forum","awards","award","gala","company","business","seminar","meeting","anniversary","exhibition","expo","agm","ceremony","شركة","شركات","مؤتمر","قمة","ملتقى","منتدى","جوائز","تكريم","معرض","اجتماع","ذكرى","حفل سنوي","فعالية"],
    wedding:   ["wedding","bride","groom","engagement","henna","party","birthday","reception","bridal","عرس","زفاف","خطوبة","حنة","عروس","حفلة","عيد ميلاد","ملكة","فرح","كوشة"],
    cultural:  ["national day","national","government","heritage","ramadan","iftar","suhoor","eid","festival","concert","cultural","celebration","outdoor","اليوم الوطني","وطني","حكومي","تراث","رمضان","إفطار","افطار","سحور","عيد","مهرجان","حفل غنائي","حفل موسيقي","احتفال"],
    launch:    ["launch","product","car","brand","activation","reveal","opening","inauguration","store","showroom","unveil","إطلاق","اطلاق","منتج","سيارة","علامة","افتتاح","كشف","تدشين","معرض سيارات"]
  },
  services: {
    laser:    ["laser","beam","sky","fireworks","light show","ليزر","أشعة","اشعة","عرض ضوئي","سكاي"],
    mapping:  ["mapping","projection","projector","facade","3d","hologram","بروجكتر","إسقاط","اسقاط","ماب","ثلاثي","واجهة","هولوجرام"],
    led:      ["led","screen","video wall","wall","stage screen","شاشة","شاشات","ليد","جدار"],
    sound:    ["sound","audio","speaker","mic","dj","music","صوت","سماعات","مايك","ساوند","دي جي"],
    lighting: ["light","lighting","stage","spot","truss","إضاءة","اضاءة","انارة","إنارة","مسرح","ستيج"]
  }
};

window.I18N = {
  en: {
    skip: "Skip to the work", nav_work: "The work", nav_services: "Services", nav_lab: "Beam Lab", nav_contact: "Contact",
    cta_short: "WhatsApp", eyebrow: "EchoLight · Abu Dhabi · UAE-wide",
    h1a: "Show us your event.", h1b: "We'll show you the proof.",
    lead: "Type what you're planning. We'll light up the work we've done for events like yours, and tell you what we'd build.",
    q_label: "Describe your event", go: "Show me",
    ph: ["a corporate summit for 500 guests", "a wedding in a ballroom", "a car launch", "National Day outdoors", "an awards night with lasers", "a Ramadan iftar"],
    reel: "Live from our events", g_eyebrow: "The proof", g_title: "Real events. Real rigs. Real nights.",
    g_sub_all: "A curated cut of recent work. Pick an event type or tell us yours above.",
    g_sub_q: "Work that fits “{q}” first. Tap any frame to watch it.",
    g_sub_f: "Filtered to what you picked.",
    more: "Show more", empty: "Nothing under that exact combination yet — try removing a filter.",
    all: "All", s_eyebrow: "What we bring", s_title: "Five disciplines. One crew.",
    see_proof: "See the proof", proof_n: "{n} frames of proof", proof_1: "1 frame of proof", proof_soon: "Ask us for references",
    l_eyebrow: "Beam Lab", l_title: "Program your own sky.",
    l_sub: "Pick a colour and a pattern. This is the same language our programmers use to design a laser or beam show.",
    l_color: "Colour", l_pattern: "Pattern", l_count: "Beams", l_speed: "Speed", l_cta: "I want this at my event",
    pat_fan: "Fan", pat_cross: "Cross", pat_sweep: "Sweep", pat_tunnel: "Tunnel",
    c_title: "Let's light your date.", c_sub: "Send us the date, the venue and a rough idea. We reply on WhatsApp with a plan and a quote.",
    c_wa: "Chat on WhatsApp", c_area: "Anywhere in the UAE", tag: "Lighting beyond imagination", lb_cta: "Request this look",
    reco_for: "For {e}, here's what we'd build", reco_generic: "Here's what we'd build for “{q}”",
    reco_default_event: "your event", reco_why: "Why", reco_cta: "Get a quote for this setup",
    stat_events: "events produced", stat_venues: "premium venues", stat_clients: "major clients", stat_rating: "Google rating",
    ev: { corporate: "Corporate", wedding: "Weddings & social", cultural: "National & cultural", launch: "Launches & activations" },
    ev_one: { corporate: "a corporate event", wedding: "a wedding or celebration", cultural: "a national or cultural event", launch: "a launch or activation" },
    sv: { lighting: "Stage Lighting", led: "LED Screens", sound: "Sound", mapping: "3D Mapping", laser: "Laser & Light Shows" },
    sv_desc: {
      lighting: "Moving heads, washes and pattern projection, programmed cue by cue so the room changes with the moment.",
      led: "High-resolution LED walls for conferences, launches and ceremonies. Delivered, operated and struck by our crew.",
      sound: "Line-array coverage, digital consoles and wireless systems tuned to the room, so every seat hears clearly.",
      mapping: "Projection onto walls, ceilings, facades and objects. Turning a building or a product into the show.",
      laser: "High-power lasers, sky beams and cold-spark effects for grand entrances, reveals and outdoor nights."
    },
    why: {
      corporate: {
        led: "Big, sharp content for speakers, agendas and sponsor loops, readable from the last row.",
        sound: "Clear speech coverage and wireless mics so every keynote and Q&A lands.",
        lighting: "Stage and room lighting that photographs well and keeps the energy up between sessions.",
        laser: "An opening moment or awards reveal people talk about afterwards."
      },
      wedding: {
        lighting: "Warm, pattern-rich room lighting and a dance floor that glows, designed around your decor.",
        laser: "A grand entrance and a sky that tells the whole venue the night has started.",
        led: "A backdrop for your story: names, photos, a live feed of the night.",
        sound: "Music and speeches that sound perfect in a big hall."
      },
      cultural: {
        laser: "Sky beams and laser shows that carry across a whole site: made for national and festival nights.",
        mapping: "Flags, heritage and stories projected onto the building itself.",
        lighting: "Colour-washed facades and landscapes in the right national and festive palette.",
        led: "Large-format screens for ceremonies, live feeds and performances."
      },
      launch: {
        mapping: "Light the product itself. Projection mapping makes the reveal unforgettable.",
        led: "Immersive screens and content that frame the product like a film.",
        laser: "A reveal moment with beams and effects, built for photos and reels.",
        lighting: "Brand-colour lighting that makes the stand or venue unmistakably yours."
      }
    },
    lb_t: "{s} · {e}", ev_general: "Showcase",
    wa_base: "Hello EchoLight, I'd like to plan an event.", wa_event: "It's {e}.", wa_svc: "I'm interested in: {s}.",
    wa_item: "I saw this on your showcase: {t}.", wa_tail: "Date / venue / guests: ", wa_lab: "I tried your Beam Lab and want something like this: {c} {p} beams.",
    pat_name: { fan: "fan", cross: "cross", sweep: "sweep", tunnel: "tunnel" }
  },
  ar: {
    skip: "تخطّي إلى الأعمال", nav_work: "أعمالنا", nav_services: "خدماتنا", nav_lab: "مختبر الأشعة", nav_contact: "تواصل",
    cta_short: "واتساب", eyebrow: "إيكو لايت · أبوظبي · كل الإمارات",
    h1a: "أخبرنا عن فعاليتك.", h1b: "ونُريك الإثبات.",
    lead: "اكتب ما تخطّط له، وسنُضيء لك أعمالنا في فعاليات تشبه فعاليتك، ونخبرك بما كنّا سنبنيه.",
    q_label: "صف فعاليتك", go: "أرني",
    ph: ["مؤتمر شركة لـ 500 ضيف", "حفل زفاف في قاعة", "إطلاق سيارة", "اليوم الوطني في الهواء الطلق", "حفل جوائز مع ليزر", "إفطار رمضاني"],
    reel: "مباشرة من فعالياتنا", g_eyebrow: "الإثبات", g_title: "فعاليات حقيقية. أجهزة حقيقية. ليالٍ حقيقية.",
    g_sub_all: "مختارات من أحدث أعمالنا. اختر نوع الفعالية أو اكتب فعاليتك بالأعلى.",
    g_sub_q: "الأعمال الأنسب لـ «{q}» أولاً. اضغط على أي لقطة لمشاهدتها.",
    g_sub_f: "مُصفّاة حسب اختيارك.",
    more: "عرض المزيد", empty: "لا يوجد شيء بهذا الجمع بعد، جرّب إزالة أحد المرشّحات.",
    all: "الكل", s_eyebrow: "ما نقدّمه", s_title: "خمسة تخصّصات. فريق واحد.",
    see_proof: "شاهد الأعمال", proof_n: "{n} لقطة من أعمالنا", proof_1: "لقطة واحدة من أعمالنا", proof_soon: "اطلب مراجع",
    l_eyebrow: "مختبر الأشعة", l_title: "صمّم سماءك بنفسك.",
    l_sub: "اختر لوناً ونمطاً. هذه هي اللغة نفسها التي يستخدمها مبرمجونا لتصميم عرض ليزر أو أشعة.",
    l_color: "اللون", l_pattern: "النمط", l_count: "الأشعة", l_speed: "السرعة", l_cta: "أريد هذا في فعاليتي",
    pat_fan: "مروحة", pat_cross: "تقاطع", pat_sweep: "مسح", pat_tunnel: "نفق",
    c_title: "لنُضئ موعدك.", c_sub: "أرسل لنا التاريخ والموقع وفكرة تقريبية. نردّ عبر واتساب بخطة وعرض سعر.",
    c_wa: "تحدّث معنا عبر واتساب", c_area: "في أي مكان في الإمارات", tag: "إضاءة تتجاوز الخيال", lb_cta: "اطلب هذا الشكل",
    reco_for: "لـ {e}، هذا ما كنّا سنبنيه", reco_generic: "هذا ما كنّا سنبنيه لـ «{q}»",
    reco_default_event: "فعاليتك", reco_why: "لماذا", reco_cta: "اطلب عرض سعر لهذا التجهيز",
    stat_events: "فعالية أنتجناها", stat_venues: "موقع مميّز", stat_clients: "عميل كبير", stat_rating: "تقييم جوجل",
    ev: { corporate: "الشركات", wedding: "الأعراس والمناسبات", cultural: "الوطنية والثقافية", launch: "الإطلاقات والعلامات" },
    ev_one: { corporate: "فعالية شركات", wedding: "حفل زفاف أو مناسبة", cultural: "فعالية وطنية أو ثقافية", launch: "إطلاق أو تفعيل علامة" },
    sv: { lighting: "إضاءة المسارح", led: "شاشات LED", sound: "الصوتيات", mapping: "الإسقاط ثلاثي الأبعاد", laser: "عروض الليزر والضوء" },
    sv_desc: {
      lighting: "رؤوس متحرّكة وإضاءة غامرة وإسقاط أنماط، مبرمجة لحظة بلحظة لتتغيّر القاعة مع الحدث.",
      led: "جدران LED عالية الدقة للمؤتمرات والإطلاقات والحفلات. توريد وتشغيل وتفكيك على يد فريقنا.",
      sound: "تغطية Line-array ومنصّات رقمية وأنظمة لاسلكية مضبوطة على القاعة ليسمع كل مقعد بوضوح.",
      mapping: "إسقاط على الجدران والأسقف والواجهات والأجسام، لنحوّل مبنى أو منتجاً إلى عرض.",
      laser: "ليزر عالي القدرة وأشعة سماء وشرارات باردة للدخولات الكبرى والإطلاقات والليالي المفتوحة."
    },
    why: {
      corporate: {
        led: "محتوى كبير وواضح للمتحدّثين والجداول والرعاة، مقروء من الصف الأخير.",
        sound: "تغطية واضحة للكلام وميكروفونات لاسلكية لتصل كل كلمة رئيسية وكل سؤال.",
        lighting: "إضاءة للمسرح والقاعة تُصوَّر بشكل ممتاز وتُبقي الحماس بين الفقرات.",
        laser: "لحظة افتتاح أو إعلان جوائز يتحدّث عنها الحضور بعدها."
      },
      wedding: {
        lighting: "إضاءة دافئة غنية بالأنماط وأرضية رقص مضيئة، مصمّمة حول ديكورك.",
        laser: "دخول كبير وسماء تُعلن للمكان كلّه أنّ الليلة بدأت.",
        led: "خلفية لقصّتك: أسماء وصور وبثّ مباشر للحفل.",
        sound: "موسيقى وكلمات بصوت مثالي في قاعة كبيرة."
      },
      cultural: {
        laser: "أشعة سماء وعروض ليزر تصل إلى الموقع كلّه، مصمّمة لليالي الوطنية والمهرجانات.",
        mapping: "أعلام وتراث وقصص تُسقَط على المبنى نفسه.",
        lighting: "واجهات ومساحات بألوان وطنية واحتفالية مناسبة.",
        led: "شاشات كبيرة للمراسم والبثّ المباشر والعروض."
      },
      launch: {
        mapping: "أضئ المنتج نفسه. الإسقاط ثلاثي الأبعاد يجعل الكشف لا يُنسى.",
        led: "شاشات ومحتوى غامر يُقدّم المنتج كأنه فيلم.",
        laser: "لحظة كشف بأشعة ومؤثّرات، مصمّمة للصور والريلز.",
        lighting: "إضاءة بألوان علامتك تجعل الموقع هويتك بوضوح."
      }
    },
    lb_t: "{s} · {e}", ev_general: "معرض الأعمال",
    wa_base: "مرحباً إيكو لايت، أودّ التخطيط لفعالية.", wa_event: "الفعالية: {e}.", wa_svc: "مهتمّ بـ: {s}.",
    wa_item: "شاهدت هذا في معرض أعمالكم: {t}.", wa_tail: "التاريخ / الموقع / عدد الضيوف: ", wa_lab: "جرّبت مختبر الأشعة وأريد شيئاً مثل هذا: {c}، نمط {p}.",
    pat_name: { fan: "مروحة", cross: "تقاطع", sweep: "مسح", tunnel: "نفق" }
  }
};
