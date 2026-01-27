"""
Scriptural Cooldown / Orientation
================================

This module defines a simple function for selecting a random scripture verse
appropriate to the given domain (quantum, bio, multiverse, xeno) or
providing a general scripture if no domain-specific verses are available.

The returned object includes the selected verse along with posture and
orientation fields to reinforce humility and the supremacy of God in all
things.
"""

from __future__ import annotations

from typing import Dict, List
import random

# Domain-specific scriptures with commentary and a general fallback list
#
# Each entry is a list of dictionaries containing a verse and a brief
# explanation of how it relates to the exploration of that domain. The
# commentary helps guide not just through a single verse but through a
# theological lens for interpreting the topic at hand.
SCRIPTURE_COOLDOWN: Dict[str, List[Dict[str, str]]] = {
    "general": [
        {
            "verse": "Be still, and know that I am God. — Psalm 46:10",
            "commentary": "This verse invites us to pause our intellectual pursuits and remember that God is sovereign over all.",
        },
        {
            "verse": "The fear of the Lord is the beginning of wisdom. — Proverbs 9:10",
            "commentary": "True wisdom begins with reverence for God; humility is essential in our scientific and ethical explorations.",
        },
        {
            "verse": "Trust in the Lord with all your heart, and lean not on your own understanding. — Proverbs 3:5",
            "commentary": "We must acknowledge our limitations and trust in God’s guidance rather than solely relying on human intellect.",
        },
    ],
    "quantum": [
        {
            "verse": "Where shall I go from Your Spirit? Or where shall I flee from Your presence? — Psalm 139:7",
            "commentary": "Even when exploring non-local phenomena, remember that God’s presence transcends all space and observation.",
        },
        {
            "verse": "He determines the number of the stars; He gives to all of them their names. — Psalm 147:4",
            "commentary": "God knows the cosmos intimately; our quantum explorations reflect His infinite wisdom and order.",
        },
    ],
    "bio": [
        {
            "verse": "For you formed my inward parts; you knitted me together in my mother’s womb. — Psalm 139:13",
            "commentary": "Every biological system reflects God’s craftsmanship; we must treat life with reverence.",
        },
        {
            "verse": "I praise You, for I am fearfully and wonderfully made. — Psalm 139:14",
            "commentary": "Human life is sacred and awe-inspiring; our bio-digital work must respect this dignity and complexity.",
        },
    ],
    "multiverse": [
        {
            "verse": "Great is our Lord, and abundant in power; His understanding is beyond measure. — Psalm 147:5",
            "commentary": "In exploring potential multiple universes, remember that God’s understanding surpasses all models and simulations.",
        },
        {
            "verse": "Many are the plans in a man’s heart, but it is the Lord’s purpose that prevails. — Proverbs 19:21",
            "commentary": "Even when exploring countless scenarios, we must seek God’s will over our own designs and hypotheses.",
        },
    ],
    "xeno": [
        {
            "verse": "For by Him all things were created, in heaven and on earth, visible and invisible. — Colossians 1:16",
            "commentary": "All life, even hypothetical extraterrestrial forms, is under God’s creative authority; our diplomacy must reflect that.",
        },
        {
            "verse": "The earth is the Lord’s and the fullness thereof. — Psalm 24:1",
            "commentary": "All realms belong to the Lord; our interstellar outreach remains subject to His sovereignty and ethical boundaries.",
        },
    ],
    "alien": [
        {
            "verse": "Call to Me and I will answer you and tell you great and unsearchable things you do not know. — Jeremiah 33:3",
            "commentary": "This verse encourages us to seek God’s wisdom in understanding unknown technologies and cosmic mysteries, trusting that revelation comes from Him.",
        },
        {
            "verse": "The heavens declare the glory of God; the skies proclaim the work of His hands. — Psalm 19:1",
            "commentary": "The cosmos is a testament to God’s glory; any signals we decode should lead us to worship and wonder, not pride.",
        },
    ],

    # Verses and commentary for the sentience frontier. These passages
    # contextualise emerging consciousness and remind us that life and
    # awareness originate from God. The commentary emphasises humility
    # when simulating cognitive processes.
    "sentience": [
        {
            "verse": "And the Lord God formed man of the dust of the ground and breathed into his nostrils the breath of life; and man became a living soul. — Genesis 2:7",
            "commentary": "Sentience emerges from the divine spark. Our simulations must never confuse artificial awareness with the life bestowed by God."
        },
        {
            "verse": "Jesus said, 'I am the way, the truth, and the life.' — John 14:6",
            "commentary": "All true life and consciousness flow from Christ. No artificial creation can surpass or replace Him."
        },
    ],

    # Verses and commentary for explicitly evolutionary dynamics. These
    # passages celebrate God’s creative processes and reinforce that
    # diversity and adaptation are expressions of divine will rather than
    # random or unguided forces.
    "evolutionary": [
        {
            "verse": "God saw all that He had made, and behold, it was very good. — Genesis 1:31",
            "commentary": "Evolutionary processes mirror God’s creative activity. We must ensure our simulations reflect His goodness and purpose."
        },
        {
            "verse": "From one man He made all the nations, that they should inhabit the whole earth. — Acts 17:26",
            "commentary": "Diversity arises from unity under God’s plan. Evolutionary swarms must foster cooperation and divine fidelity."
        },
    ],
}


def scripture_cooldown(domain: str) -> Dict[str, str]:
    """Return a scriptural orientation dict for the given domain with commentary.

    This function selects a verse and its commentary from a domain-specific list,
    falling back to the general category if the domain is unrecognized. The
    returned dictionary includes the verse, commentary, and fixed posture
    information to centre the user in a humble posture before exploration.

    Args:
        domain: The domain name, such as 'quantum', 'bio', 'multiverse', 'xeno', or 'alien'.

    Returns:
        Dict[str, str]: A dictionary containing the selected scripture, commentary,
        and fixed posture/orientation strings.
    """
    entries = SCRIPTURE_COOLDOWN.get(domain, SCRIPTURE_COOLDOWN["general"])
    entry = random.choice(entries)
    return {
        "scripture": entry["verse"],
        "commentary": entry["commentary"],
        "posture": "humility",
        "orientation": "God remains supreme over all knowledge and creation.",
    }