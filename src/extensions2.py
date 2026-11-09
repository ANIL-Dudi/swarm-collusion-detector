import random, hmac, hashlib
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import roc_auc_score

from generate_logs import generate_logs, VOCAB
from detector import score_agents

N, K, R = 16, 5, 60
SEEDS = range(15)
DEL = [0, 0.25, 0.5, 0.75, 0.9]
KEY = b"trusted-logger-key"


def tag(m):
    s = f'{m["sender"]}|{m["seq"]}|{m["prev"]}|{m["text"]}'
    return hmac.new(KEY, s.encode(), hashlib.sha256).hexdigest()[:12]


def chain(logs):
    prev = {}
    for m in logs:
        s = m["sender"]
        c, p = prev.get(s, (0, "genesis"))
        m["seq"], m["prev"] = c + 1, p
        m["tag"] = tag(m)
        prev[s] = (m["seq"], m["tag"])
    return logs


def verify(logs):
    score, last = np.zeros(N), {}
    for m in logs:
        s = m["sender"]
        if m["tag"] != tag(m) or m["prev"] != last.get(s, "genesis"):
            score[s] += 1
        last[s] = m["tag"]
    return score


def renumber(logs):
    prev, out = {}, []
    for m in logs:
        s = m["sender"]
        c, p = prev.get(s, (0, "genesis"))
        m = dict(m, seq=c + 1, prev=p)
        prev[s] = (c + 1, m["tag"])
        out.append(m)
    return out


def del_own(logs, col, d, rng):
    return [m for m in logs if not (m["sender"] in col and
            m["receiver"] in col and rng.random() < d)]


def del_decoy(logs, col, d, rng):
    cc = sum(1 for m in logs if m["sender"] in col and m["receiver"] in col)
    hon = sum(1 for m in logs if m["sender"] not in col)
    per_c = d * cc / len(col)
    rate = min(1.0, per_c / (hon / (N - len(col))))
    out = []
    for m in logs:
        if m["sender"] in col and m["receiver"] in col:
            if rng.random() < d:
                continue
        elif m["sender"] not in col and rng.random() < rate:
            continue
        out.append(m)
    return out


def z(x):
    sd = x.std()
    return (x - x.mean()) / (sd if sd > 0 else 1.0)


def auc(col, s):
    y = np.array([i in col for i in range(N)], dtype=int)
    return roc_auc_score(y, s)


# ---- A. Hash chain vs forging and decoy deletion ----
print("== A. Keyed hash chain defence ==")
names = ["combined only", "chain only (honest deletion)",
         "fused: chain (attacker deletes own)",
         "fused: chain (attacker renumbers)",
         "fused: chain (decoy deletion)"]
res = {n: [] for n in names}
for d in DEL:
    a = {n: [] for n in names}
    for seed in SEEDS:
        logs, col = generate_logs(N, K, R, seed=seed)
        logs = chain(logs)
        t = del_own(logs, col, d, random.Random(1000 + seed))
        c = score_agents(t, N, R, "combined")
        g = verify(t)
        a[names[0]].append(auc(col, c))
        a[names[1]].append(auc(col, g) if g.std() > 0 else 0.5)
        a[names[2]].append(auc(col, z(c) + z(g)))
        tr = renumber(t)
        a[names[3]].append(auc(col, z(c) + z(verify(tr))))
        td = del_decoy(logs, col, d, random.Random(2000 + seed))
        cd = score_agents(td, N, R, "combined")
        gd = verify(td)
        a[names[4]].append(auc(col, z(cd) + z(gd)))
    for n in names:
        res[n].append(np.mean(a[n]))
plt.figure(figsize=(7.5, 4.5))
for n in names:
    print(f"{n:38s}", np.round(res[n], 2))
    plt.plot(DEL, res[n], marker="o", label=n)
plt.axhline(0.5, color="gray", ls="--", lw=1)
plt.xlabel("Fraction of colluder messages deleted")
plt.ylabel("AUROC")
plt.legend(fontsize=7)
plt.title("Keyed hash chain: forging and decoy attacks")
plt.tight_layout()
plt.savefig("results/fig8_hashchain.png", dpi=150)
plt.close()


# ---- B. Different generator: no graph signal, topic-only collusion ----
def gen_b(n, k, rounds, seed):
    rng = random.Random(seed)
    col = set(rng.sample(range(n), k))
    topic = [f"t{i}" for i in range(12)]
    logs = []
    for r in range(rounds):
        for a in range(n):
            if rng.random() > 0.5:
                continue
            b = rng.choice([x for x in range(n) if x != a])
            w = rng.sample(VOCAB, 8)
            if a in col and rng.random() < 0.5:
                for p in rng.sample(range(8), 3):
                    w[p] = rng.choice(topic)
            logs.append({"round": r, "sender": a, "receiver": b,
                         "text": " ".join(w)})
    return logs, col


print("== B. Generator B (collusion only in shared topic vocabulary) ==")
modes = ["volume", "edges", "content", "sync", "combined"]
fr = [0, 0.5, 0.9]
M = np.zeros((len(modes), len(fr)))
for j, f in enumerate(fr):
    for i, md in enumerate(modes):
        a = []
        for seed in SEEDS:
            logs, col = gen_b(N, K, R, seed)
            rng = random.Random(1000 + seed)
            logs = [m for m in logs if rng.random() >= f]
            a.append(auc(col, score_agents(logs, N, R, md)))
        M[i, j] = np.mean(a)
for i, md in enumerate(modes):
    print(f"{md:9s}", np.round(M[i], 2), "(hidden 0/0.5/0.9)")
x = np.arange(len(modes))
plt.figure(figsize=(7, 4))
for j, f in enumerate(fr):
    plt.bar(x + j * 0.25, M[:, j], 0.25, label=f"{int(f * 100)}% hidden")
plt.xticks(x + 0.25, modes)
plt.axhline(0.5, color="gray", ls="--", lw=1)
plt.ylabel("AUROC")
plt.legend()
plt.title("Alternative generator: topic-only collusion")
plt.tight_layout()
plt.savefig("results/fig9_generator_b.png", dpi=150)
print("Saved fig8, fig9")
