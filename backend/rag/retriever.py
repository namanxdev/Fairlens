from typing import List

_KNOWLEDGE_CHUNKS = [
    {
        "source": "EEOC Uniform Guidelines",
        "text": "The four-fifths rule states that a selection rate for any race, sex, or ethnic group which is less than four-fifths (or 80%) of the rate for the group with the highest rate will generally be regarded by Federal enforcement agencies as evidence of adverse impact."
    },
    {
        "source": "EU AI Act Article 10",
        "text": "High-risk AI systems shall be designed and developed following the principle of EU AI Act Article 10 on data governance. Training, validation and testing datasets shall be relevant, representative, free of errors and complete in view of the intended purpose."
    },
    {
        "source": "EU AI Act Article 9",
        "text": "Risk management systems for high-risk AI systems shall consist of a continuous iterative process run throughout the entire lifecycle of a high-risk AI system, requiring regular review and updating."
    },
    {
        "source": "Equal Credit Opportunity Act",
        "text": "ECOA prohibits discrimination in any aspect of a credit transaction based on race, color, religion, national origin, sex, marital status, age, or because an applicant receives income from a public assistance program."
    },
    {
        "source": "NIST AI RMF 1.0",
        "text": "The NIST AI Risk Management Framework provides a structured process for managing AI risks through MAP (Measure), MEASURE (Analyze), MANAGE (Govern), and GOVERN (Oversee) functions."
    },
    {
        "source": "ISO/IEC TR 24027:2021",
        "text": "This technical report provides guidance on bias in AI systems and AI-aided decision making, covering sources of bias, mitigation techniques, and evaluation methods."
    },
]


def retrieve_regulatory_context(query: str, k: int = 3) -> List[str]:
    query_lower = query.lower()
    scored = []
    for chunk in _KNOWLEDGE_CHUNKS:
        score = 0
        for word in query_lower.split():
            if len(word) > 3 and word in chunk["text"].lower():
                score += 1
        scored.append((score, chunk))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:k]
    return [f"[{c['source']}] {c['text']}" for _, c in top]
