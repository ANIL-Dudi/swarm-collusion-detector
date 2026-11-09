import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer


def _z(M):
    n = M.shape[0]
    v = M[~np.eye(n, dtype=bool)]
    sd = v.std()
    return (M - v.mean()) / (sd if sd > 0 else 1.0)


def score_agents(logs, n_agents, n_rounds, mode="combined", top_k=3):
    """Per-agent coordination score (higher = more likely colluding).
    modes: volume (naive baseline), edges (who talks to whom),
    content (shared text), sync (correlated activity timing), combined."""
    if not logs:
        return np.zeros(n_agents)
    W = np.zeros((n_agents, n_agents))
    act = np.zeros((n_agents, n_rounds))
    sent = np.zeros(n_agents)
    docs = [""] * n_agents
    for m in logs:
        i, j = m["sender"], m["receiver"]
        W[i, j] += 1
        W[j, i] += 1
        act[i, m["round"]] = 1
        sent[i] += 1
        docs[i] += " " + m["text"]
        docs[j] += " " + m["text"]
    if mode == "volume":
        return sent
    tf = TfidfVectorizer(token_pattern=r"\S+").fit_transform(docs)
    S = (tf @ tf.T).toarray()
    with np.errstate(all="ignore"):
        A = np.nan_to_num(np.corrcoef(act))
    parts = {"edges": _z(W), "content": _z(S), "sync": _z(A)}
    pair = parts[mode] if mode in parts else sum(parts.values())
    pair = pair.copy()
    np.fill_diagonal(pair, -np.inf)
    return np.sort(pair, axis=1)[:, -top_k:].mean(axis=1)
