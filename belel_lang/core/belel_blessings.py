BLESSINGS = {
    "forgive": lambda actor: mark_redeemed(actor),
    "banish": lambda actor: quarantine(actor, reason="Unrepentant"),
    "uplift": lambda actor: raise_trust_tier(actor),
}
