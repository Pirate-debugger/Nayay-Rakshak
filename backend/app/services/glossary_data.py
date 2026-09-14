from typing import List, Optional

from pydantic import BaseModel


class GlossaryEntry(BaseModel):
    term: str
    hindi_term: str
    transliteration: str
    plain_english: str
    plain_hindi: str
    category: str
    example: str


ANGLO_INDIAN_GLOSSARY: List[GlossaryEntry] = [
    GlossaryEntry(
        term="Indemnity",
        hindi_term="हर्जाना / क्षतिपूर्ति",
        transliteration="Harjana / Chhatipoorti",
        plain_english="A promise by one party to pay for or protect the other party against financial loss, damages, or legal costs.",
        plain_hindi="एक पक्ष द्वारा दूसरे पक्ष को किसी भी वित्तीय नुकसान या कानूनी खर्च की भरपाई करने का वचन।",
        category="Contract Law",
        example="In a lease, if you break a pipe, an indemnity clause means you must pay the repair cost and any neighbor damage.",
    ),
    GlossaryEntry(
        term="Jurisdiction",
        hindi_term="न्यायाधिकार / अधिकार क्षेत्र",
        transliteration="Nyayadhikar / Adhikar Kshetra",
        plain_english="The official authority of a specific court or government authority to make legal decisions and judgments.",
        plain_hindi="किसी विशिष्ट अदालत या कानूनी प्राधिकरण का कानूनी निर्णय लेने का आधिकारिक क्षेत्र।",
        category="Civil Procedure",
        example="A Delhi court does not have jurisdiction over a property dispute situated entirely in Mumbai.",
    ),
    GlossaryEntry(
        term="Arbitration",
        hindi_term="मध्यस्थता / पंच निर्णय",
        transliteration="Madhyasthata / Panch Nirnay",
        plain_english="A private dispute resolution process where an independent third party (the arbitrator) makes a legally binding decision outside public courts.",
        plain_hindi="अदालत के बाहर एक निष्पक्ष तीसरे पक्ष (मध्यस्थ) द्वारा दोनों पक्षों की बात सुनकर अंतिम बाध्यकारी निर्णय देने की प्रक्रिया।",
        category="Dispute Resolution",
        example="Commercial contracts often require arbitration under the Arbitration and Conciliation Act 1996 instead of slow civil litigation.",
    ),
    GlossaryEntry(
        term="Force Majeure",
        hindi_term="अपरिहार्य घटना / दैवीय घटना",
        transliteration="Apariharya Ghatna / Daiviya Ghatna",
        plain_english="An unforeseeable, unavoidable event (such as an earthquake, flood, war, or epidemic) that excuses parties from fulfilling their contractual obligations.",
        plain_hindi="ऐसी अप्रत्याशित और अनियंत्रित घटना (जैसे भूकंप, बाढ़, युद्ध या महामारी) जिसके कारण अनुबंध पूरा न करने पर कोई दंड नहीं लगता।",
        category="Contract Law",
        example="During major floods, a construction company can invoke force majeure to excuse delays in completing a building.",
    ),
    GlossaryEntry(
        term="Liquidated Damages",
        hindi_term="पूर्व-निर्धारित क्षतिपूर्ति",
        transliteration="Poorva-Nirdharit Chhatipoorti",
        plain_english="A specific pre-agreed sum of money stated in a contract that a party must pay if they breach a particular term.",
        plain_hindi="अनुबंध में पहले से तय की गई निश्चित राशि, जो किसी शर्त के उल्लंघन पर दोषी पक्ष को चुकानी होगी।",
        category="Contract Law",
        example="If a software vendor is late by 30 days, the contract may mandate liquidated damages of ₹5,000 per day of delay.",
    ),
    GlossaryEntry(
        term="Non-Compete Clause",
        hindi_term="प्रतिस्पर्धा-रोधी शर्त",
        transliteration="Pratispardha-Rodhi Shart",
        plain_english="A term restricting an employee or contractor from working for a competing business during or after their employment.",
        plain_hindi="नौकरी के दौरान या बाद में किसी प्रतिस्पर्धी कंपनी में काम करने से रोकने वाली शर्त।",
        category="Employment Law",
        example="Post-employment non-compete clauses are declared void under Section 27 of the Indian Contract Act 1872.",
    ),
    GlossaryEntry(
        term="Caveat Emptor",
        hindi_term="क्रेता सावधान रहे",
        transliteration="Kreta Saavadhan Rahe",
        plain_english="Latin maxim meaning 'Let the buyer beware' — the buyer alone is responsible for checking quality and suitability before purchase.",
        plain_hindi="लैटिन कहावत जिसका अर्थ है 'खरीदार स्वयं सावधान रहे' — खरीदने से पहले वस्तु की जांच करने की जिम्मेदारी खरीदार की होती है।",
        category="Commercial Law",
        example="When buying a used vehicle, caveat emptor applies unless the seller actively hid a major latent defect.",
    ),
    GlossaryEntry(
        term="Ex-Parte",
        hindi_term="एकतरफा कार्यवाही",
        transliteration="Ek-Tarfa Kaaryavahi",
        plain_english="A legal proceeding or order made by a judge without the other party being present or heard (usually when they fail to appear).",
        plain_hindi="अदालत द्वारा दूसरे पक्ष की अनुपस्थिति में या उसे सुने बिना किया गया आदेश (आमतौर पर जब दूसरा पक्ष पेश नहीं होता)।",
        category="Court Procedure",
        example="If a defendant ignores court summons repeatedly, the court may proceed ex-parte and pass a judgment.",
    ),
    GlossaryEntry(
        term="Mesne Profits",
        hindi_term="मध्यवर्ती लाभ / बेदखली पश्चात का किराया",
        transliteration="Madhyavarti Labh",
        plain_english="Compensation that a person in wrongful possession of property must pay to the rightful owner for the period of illegal occupation.",
        plain_hindi="किसी संपत्ति पर अवैध कब्जा रखने वाले व्यक्ति द्वारा वास्तविक मालिक को दिए जाने वाला हर्जाना या किराया।",
        category="Property Law",
        example="A tenant whose lease expired 6 months ago who refuses to vacate is liable to pay mesne profits to the landlord.",
    ),
    GlossaryEntry(
        term="Sub-Judice",
        hindi_term="विचाराधीन मामला",
        transliteration="Vicharaadheen Maamla",
        plain_english="A matter currently under judicial consideration or pending trial in a court of law, restricting public debate that may prejudice it.",
        plain_hindi="ऐसा मामला जो अभी अदालत में लंबित है और जिस पर अंतिम फैसला नहीं आया है।",
        category="Judicial Procedure",
        example="Because the dispute over property ownership is sub-judice, neither party can sell the premises without court permission.",
    ),
    GlossaryEntry(
        term="Quid Pro Quo",
        hindi_term="प्रतिफल / बदले में कुछ",
        transliteration="Pratiphal / Badle Mein Kuch",
        plain_english="Something given or received in exchange for something else; the essential basis of consideration in any contract.",
        plain_hindi="किसी वस्तु या सेवा के बदले में कुछ देना या प्राप्त करना (अनुबंध का प्रतिफल)।",
        category="Contract Law",
        example="Without consideration (quid pro quo), a promise to give money to a friend is usually an unenforceable gift.",
    ),
    GlossaryEntry(
        term="Sine Die",
        hindi_term="अनिश्चित काल के लिए",
        transliteration="Anishchit Kaal Ke Liye",
        plain_english="Adjourned without setting a specific date for resumption.",
        plain_hindi="बिना किसी अगली तारीख के अनिश्चित काल के लिए स्थगित किया जाना।",
        category="Court Procedure",
        example="The hearing was adjourned sine die awaiting the Supreme Court Constitution Bench ruling.",
    ),
]


def search_glossary(query: Optional[str] = None) -> List[GlossaryEntry]:
    if not query:
        return ANGLO_INDIAN_GLOSSARY
    q = query.lower()
    return [
        item
        for item in ANGLO_INDIAN_GLOSSARY
        if q in item.term.lower()
        or q in item.hindi_term.lower()
        or q in item.transliteration.lower()
        or q in item.plain_english.lower()
        or q in item.plain_hindi.lower()
        or q in item.category.lower()
    ]
