"""Bounded public facts and deterministic email fallback; no sending."""
from app.models.ai import PitchDraft


def fact_catalog(record, analysis):
    if not analysis:
        return []
    business = record["business"]
    provenance = record.get("provenance") or {}
    listing_date = (provenance.get("collected_at") or record["created_at"])[:10]
    facts = []
    for field, label in (("name", "Business name"), ("address", "Listed address"),
                         ("website", "Listed website"), ("phone", "Listed phone")):
        value = business.get(field)
        if value:
            facts.append({"fact": f"{label}: {str(value)[:240]}",
                          "source": f"listing.{field}", "observed_on": listing_date})
    for index, item in enumerate(analysis.get("evidence") or []):
        detail = item.get("detail")
        if detail:
            facts.append({"fact": str(detail)[:300], "source": f"analysis.evidence.{index}",
                          "observed_on": str(item.get("observed_at") or analysis["created_at"])[:10]})
    return facts[:16]


def check_facts(draft, catalog, language, sender):
    if draft.language != language:
        return False
    allowed = {(item["fact"], item["source"], item["observed_on"]) for item in catalog}
    if any((item.fact, item.source, item.observed_on.isoformat()) not in allowed
           for item in draft.personalization_used):
        return False
    body = draft.body.casefold()
    return (sender.name.casefold() in body and sender.company.casefold() in body
            and draft.opt_out_line.casefold() in body)


def fallback_pitch(record, sender, language, analysis, rule_draft=None):
    business = record["business"]["name"]
    if language == "ur":
        opt_out = "اگر آپ مزید پیغام نہیں چاہتے تو جواب دیں، ہم رابطہ بند کر دیں گے۔"
        body = (f"السلام علیکم ٹیم، میرا نام {sender.name} ہے اور میں {sender.company} سے ہوں۔ "
                f"ہم {sender.offer} پیش کرتے ہیں۔ مجھے یہ معلوم نہیں "
                "کہ آپ کی ٹیم نئی پوچھ گچھ، اپائنٹمنٹ کی یاد دہانی، مشاورت کے بعد رابطہ، یا دوبارہ بکنگ کو اس وقت "
                "کیسے سنبھالتی ہے۔ اگر آپ مناسب سمجھیں تو میں صرف یہ سمجھنا چاہوں گا "
                "کہ موجودہ طریقہ کیسے کام کرتا ہے اور آیا کسی مرحلے پر مدد مفید ہو سکتی ہے۔ کیا آپ اپنی سہولت کے مطابق "
                "پندرہ منٹ کی مختصر گفتگو کے لیے تیار ہوں گے؟ "
                f"{opt_out} شکریہ، {sender.name}، {sender.company}۔")
        subjects = [f"{business} کے لیے مختصر تعارف", "آپ کی ٹیم کے طریقہ کار کے بارے میں سوال", "مختصر گفتگو کی درخواست"]
        cta = "کیا آپ پندرہ منٹ کی مختصر گفتگو کے لیے تیار ہوں گے؟"
        follow = ["صرف پچھلے پیغام کے بارے میں پوچھ رہا ہوں۔ اگر مناسب نہ ہو تو بتا دیں۔ " + opt_out,
                  "یہ آخری یاد دہانی ہے۔ اگر گفتگو مفید لگے تو اپنی سہولت کا وقت بتا دیں۔ " + opt_out]
    elif language == "roman_ur":
        opt_out = "Agar aap mazeed paigham nahin chahte to jawab dein, hum rabta band kar dein ge."
        body = (f"Assalam-o-alaikum team, mera naam {sender.name} hai aur main {sender.company} se hoon. "
                f"Hum {sender.offer} pesh karte hain. Aap ki public listing mein business ka naam dekha, lekin mujhe "
                "nahin maloom ke aap ki team nayi inquiries, appointment reminders, consultation ke baad follow-up, "
                "ya dobara booking ko filhal kaise sambhalti hai. "
                "Agar aap munasib samjhein to main sirf aap ka mojooda tareeqa samajhna chahta hoon aur dekhna chahta "
                "hoon ke kisi marhalay par madad waqai mufeed ho sakti hai ya nahin. Kya aap apni sahulat ke mutabiq "
                f"pandrah minute ki mukhtasar guftagu ke liye tayyar hon ge? {opt_out} Shukriya, {sender.name}, {sender.company}.")
        subjects = [f"{business} ke liye mukhtasar ta'aruf", "Aap ki team ke process par aik sawal", "Mukhtasar guftagu ki darkhwast"]
        cta = "Kya aap pandrah minute ki mukhtasar guftagu ke liye tayyar hon ge?"
        follow = ["Pichlay paigham ke baray mein sirf aik martaba pooch raha hoon. " + opt_out,
                  "Yeh aakhri yaad dehani hai; agar guftagu mufeed ho to apna munasib waqt batayein. " + opt_out]
    else:
        opt_out = "If you prefer no further messages, please reply and we will stop contacting you."
        body = (f"Hello team, my name is {sender.name} and I work with {sender.company}. "
                f"We offer {sender.offer}. I found your business through a public listing, but I do not know how "
                "your team currently handles new inquiries, appointment reminders, consultation follow-up, or "
                "rebooking. I do not want to assume there is a problem. I would first like to understand what "
                "already works well for your team and whether any part of the customer journey is worth reviewing "
                "together. If it would be useful, could we arrange a brief fifteen-minute conversation at a time "
                "you choose? "
                f"{opt_out} Best regards, {sender.name}, {sender.company}.")
        subjects = [(rule_draft or {}).get("subject") or f"A short introduction for {business}", "A question about your customer follow-up process",
                    "Would a brief conversation be useful?"]
        cta = "Could we arrange a brief fifteen-minute conversation at a time you choose?"
        follow = ["Following up once on my earlier note. No pressure if this is not relevant. " + opt_out,
                  "This is my final follow-up. If a short conversation would help, please suggest a convenient time. " + opt_out]
    return PitchDraft.model_validate({
        "language": language, "subject_options": subjects, "body": body,
        "personalization_used": [], "call_to_action": cta,
        "follow_ups": [{"after_days": 3, "body": follow[0]}, {"after_days": 7, "body": follow[1]}],
        "opt_out_line": opt_out,
        "assumptions_and_unknowns": (["No saved analysis; internal process and category are unverified"] if not analysis
                                     else ["Internal process and outreach suitability remain unconfirmed"]),
    })
