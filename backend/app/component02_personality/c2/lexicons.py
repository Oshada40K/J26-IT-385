"""Small, openly written word categories for interpretable psycholinguistic features.

These are NOT LIWC (which is proprietary). They are short hand-built lists for
the same kinds of categories that psycholinguistic studies associate with Big
Five traits (pronoun use, emotion words, tentative vs certain language, social
and achievement words). Each category becomes one human-readable feature, which
is what the SHAP explanation layer needs. Extend or replace the lists freely.
"""

CATEGORIES: dict[str, set[str]] = {
    "i_words": {"i", "me", "my", "mine", "myself", "i'm", "i've", "i'll", "i'd", "im", "ive"},
    "we_words": {"we", "us", "our", "ours", "ourselves", "we're", "we've", "we'll"},
    "you_words": {"you", "your", "yours", "yourself", "you're", "you've", "u"},
    "social": {
        "friend", "friends", "people", "family", "mom", "dad", "mother", "father", "brother",
        "sister", "together", "talk", "talked", "talking", "party", "parties", "roommate",
        "girlfriend", "boyfriend", "team", "group", "everyone", "someone", "they", "them",
    },
    "posemo": {
        "happy", "love", "loved", "good", "great", "nice", "fun", "excited", "glad", "enjoy",
        "enjoyed", "laugh", "wonderful", "best", "awesome", "cool", "like", "liked", "proud",
        "hope", "glad", "relaxed", "calm", "beautiful",
    },
    "negemo": {
        "sad", "hate", "angry", "worried", "worry", "afraid", "scared", "stress", "stressed",
        "upset", "bad", "awful", "hurt", "lonely", "depressed", "anxious", "nervous", "tired",
        "annoyed", "cry", "crying", "miss", "fear", "terrible", "horrible", "mad", "frustrated",
        "guilty", "ashamed", "panic", "overwhelmed",
    },
    "tentative": {
        "maybe", "perhaps", "guess", "might", "probably", "possibly", "unsure", "wonder",
        "seem", "seems", "somewhat", "kind", "sort", "unclear", "suppose", "hopefully",
    },
    "certainty": {
        "always", "never", "definitely", "sure", "certainly", "absolutely", "completely",
        "totally", "clearly", "obviously", "exactly", "every", "must",
    },
    "negation": {
        "not", "no", "never", "don't", "can't", "won't", "nothing", "isn't", "didn't",
        "doesn't", "wasn't", "aren't", "nobody", "none", "dont", "cant", "wont",
    },
    "achievement": {
        "work", "working", "goal", "goals", "success", "succeed", "study", "studying", "finish",
        "finished", "achieve", "accomplish", "plan", "planned", "organized", "responsible",
        "grade", "grades", "class", "classes", "homework", "deadline", "effort", "prepare",
        "schedule", "complete", "completed",
    },
    "cognitive": {
        "think", "thinking", "know", "believe", "understand", "realize", "reason", "because",
        "idea", "ideas", "therefore", "consider", "question", "why", "meaning", "learn",
    },
    "openness_topics": {
        "art", "music", "song", "songs", "book", "books", "read", "reading", "write", "writing",
        "poem", "poetry", "philosophy", "culture", "imagine", "creative", "beauty", "travel",
        "theory", "universe", "religion", "god", "society", "experience", "curious",
    },
    "swear": {"damn", "hell", "shit", "fuck", "fucking", "crap", "sucks", "stupid", "ass"},
    "articles": {"a", "an", "the"},
}
