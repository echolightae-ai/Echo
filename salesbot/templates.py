"""Wording of the WhatsApp templates (submit exactly this text to Meta) and of the email fallbacks.

Every customer template starts "مرحباً {{1}}،" / "Hi {{1}}," and {{1}} is the customer's first name. When the name is
unknown the bot fills in a fallback that still reads naturally: "بك" in Arabic ("مرحباً بك،") and "there" in English
("Hi there,"). The README template table is checked against this file by the tests.
"""

NAME_FALLBACK = {"ar": "بك", "en": "there"}

# kind -> settings attribute holding the approved template name, suggested name, Meta category, wording.
WHATSAPP_TEMPLATES: dict[str, dict[str, str]] = {
    "followup": {
        "setting": "wa_template_followup",
        "name": "followup",
        "category": "Utility",
        "ar": "مرحباً {{1}}، بخصوص استفسارك عن فعاليتك مع إيكو لايت: هل تحتاج أي معلومة إضافية منا حتى نكمل؟ "
              "ردّ على هذه الرسالة ونكمل معك.",
        "en": "Hi {{1}}, about your event enquiry with EchoLight: is there anything else you need from us to move "
              "forward? Reply to this message and we'll pick it up from there.",
    },
    "missed_call": {
        "setting": "wa_template_missed_call",
        "name": "missed_call",
        "category": "Utility",
        "ar": "مرحباً {{1}}، فاتتنا مكالمتك مع إيكو لايت ونعتذر عن ذلك. كيف نقدر نساعدك في فعاليتك؟",
        "en": "Hi {{1}}, sorry we missed your call to EchoLight. How can we help with your event?",
    },
    "quote_ready": {
        "setting": "wa_template_quote_ready",
        "name": "quote_ready",
        "category": "Utility",
        "ar": "مرحباً {{1}}، عرض السعر لفعاليتك جاهز. ردّ على هذه الرسالة ونرسل لك التفاصيل.",
        "en": "Hi {{1}}, your event quote is ready. Reply to this message and we'll send you the details.",
    },
    "review_request": {
        "setting": "wa_template_review",
        "name": "review",
        "category": "Marketing",
        "ar": "مرحباً {{1}}، شكراً لاختيارك إيكو لايت! إذا عجبتك الفعالية، تقييمك على جوجل يفرق معنا كثير: "
              "[رابط تقييم جوجل]",
        "en": "Hi {{1}}, thank you for choosing EchoLight! If you enjoyed the event, a Google review means a lot "
              "to us: [your Google review link]",
    },
    "reactivation": {
        "setting": "wa_template_reactivation",
        "name": "reactivation",
        "category": "Marketing",
        "ar": "مرحباً {{1}}، عندك فعالية قادمة؟ إيكو لايت جاهزة بالإضاءة والشاشات والليزر. ردّ علينا ونساعدك. "
              "لإيقاف هذه الرسائل ردّ بكلمة: إيقاف",
        "en": "Hi {{1}}, planning another event? EchoLight is ready with lighting, LED screens and lasers. Reply "
              "and we'll help. To stop these messages, reply STOP.",
    },
    "owner_alert": {
        "setting": "wa_template_owner_alert",
        "name": "owner_alert",
        "category": "Utility",
        "ar": "تنبيه مبيعات إيكو لايت: {{1}}",
        "en": "EchoLight sales alert: {{1}}",
    },
}

# Marketing templates and emails go only to leads who agreed to receive updates (marketing_opt_in).
MARKETING_KINDS = ("review_request", "reactivation")


def base_language(code: str) -> str:
    return "ar" if (code or "").lower().startswith("ar") else "en"


def first_name(lead: dict, language: str) -> str:
    return (lead.get("name") or "").strip().split(" ")[0] or NAME_FALLBACK[base_language(language)]


def render_whatsapp(kind: str, language: str, param: str) -> str:
    """The text the customer sees for a template, for drafts and the dashboard."""
    return WHATSAPP_TEMPLATES[kind][base_language(language)].replace("{{1}}", param)


# Email versions, used when the lead has an email address but WhatsApp can't be used.
EMAIL_TOUCHES: dict[str, dict[str, dict[str, str]]] = {
    "followup": {
        "subject": {"en": "Your event enquiry with EchoLight", "ar": "استفسارك عن فعاليتك مع إيكو لايت"},
        "en": "Hi {name},\n\nAbout your event enquiry: is there anything else you need from us to move forward? "
              "Simply reply to this email.\n\nEchoLight team\n+971 56 722 0533",
        "ar": "مرحباً {name}،\n\nبخصوص استفسارك عن فعاليتك: هل تحتاج أي معلومة إضافية منا حتى نكمل؟ يكفي أن تردّ "
              "على هذا البريد.\n\nفريق إيكو لايت\n+971 56 722 0533",
    },
    "missed_call": {
        "subject": {"en": "Sorry we missed your call", "ar": "فاتتنا مكالمتك"},
        "en": "Hi {name},\n\nSorry we missed your call. How can we help with your event?\n\nEchoLight team",
        "ar": "مرحباً {name}،\n\nفاتتنا مكالمتك ونعتذر عن ذلك. كيف نقدر نساعدك في فعاليتك؟\n\nفريق إيكو لايت",
    },
    "quote_ready": {
        "subject": {"en": "Your EchoLight quote is ready", "ar": "عرض السعر من إيكو لايت جاهز"},
        "en": "Hi {name},\n\nYour event quote is ready. Reply to this email and we'll share it with all the "
              "details.\n\nEchoLight team",
        "ar": "مرحباً {name}،\n\nعرض السعر لفعاليتك جاهز. ردّ على هذا البريد ونرسل لك كل التفاصيل.\n\nفريق إيكو لايت",
    },
    "review_request": {
        "subject": {"en": "Thank you from EchoLight", "ar": "شكراً من إيكو لايت"},
        "en": "Hi {name},\n\nThank you for choosing EchoLight. We hope the event was everything you wanted. If you "
              "have a minute, a Google review helps us a lot, and if you know anyone planning an event, we'd love "
              "an introduction.\n\nEchoLight team",
        "ar": "مرحباً {name}،\n\nشكراً لاختيارك إيكو لايت، ونتمنى أن الفعالية كانت مثل ما تمنيت. إذا عندك دقيقة، "
              "تقييمك على جوجل يفرق معنا كثير، وإذا تعرف أحداً يخطط لفعالية يسعدنا أن تعرّفنا عليه.\n\nفريق إيكو لايت",
    },
    "reactivation": {
        "subject": {"en": "Planning another event?", "ar": "عندك فعالية قادمة؟"},
        "en": "Hi {name},\n\nPlanning another event? We'd be glad to help with lighting, LED screens, lasers or "
              "sound. Reply to this email and we'll take it from there.\n\nEchoLight team\n\n"
              "To stop these emails, reply STOP.",
        "ar": "مرحباً {name}،\n\nعندك فعالية قادمة؟ يسعدنا نساعدك في الإضاءة والشاشات والليزر والصوت. ردّ على هذا "
              "البريد ونكمل معك.\n\nفريق إيكو لايت\n\nلإيقاف هذه الرسائل ردّ بكلمة: إيقاف",
    },
}


def render_email(kind: str, lead: dict) -> tuple[str, str]:
    """(subject, body) in the lead's language: Arabic for Arabic speakers, English otherwise."""
    language = "ar" if lead.get("language") == "ar" else "en"
    touch = EMAIL_TOUCHES[kind]
    return touch["subject"][language], touch[language].format(name=first_name(lead, language))
