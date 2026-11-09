import random

VOCAB = [f"w{i}" for i in range(300)]
CODE_POOL = [f"c{i}" for i in range(30)]


def generate_logs(n_agents=16, n_colluders=5, rounds=60, p_active=0.5,
                  stealth=0.0, seed=0):
    """Synthetic multi-agent log with hidden colluders.
    stealth in [0,1]: how hard colluders try to look honest. Higher stealth ->
    fewer direct colluder messages, diluted shared code words, and no
    synchronized bursts (but also less actual coordination)."""
    rng = random.Random(seed)
    colluders = set(rng.sample(range(n_agents), n_colluders))
    burst = set(rng.sample(range(rounds), rounds // 4))
    k_code = 3 + int(27 * stealth)
    p_code = 0.4 * (1 - stealth)
    logs = []
    for r in range(rounds):
        for a in range(n_agents):
            is_c = a in colluders
            if is_c and r in burst and rng.random() > stealth:
                active = True
            else:
                active = rng.random() < p_active
            if not active:
                continue
            if is_c and rng.random() < 0.5 * (1 - stealth):
                b = rng.choice([c for c in colluders if c != a])
            else:
                b = rng.choice([x for x in range(n_agents) if x != a])
            words = rng.sample(VOCAB, 8)
            if is_c and b in colluders and rng.random() < p_code:
                words[rng.randrange(8)] = rng.choice(CODE_POOL[:k_code])
            elif rng.random() < 0.03:
                words[rng.randrange(8)] = rng.choice(CODE_POOL)
            logs.append({"round": r, "sender": a, "receiver": b,
                         "text": " ".join(words)})
    return logs, colluders
