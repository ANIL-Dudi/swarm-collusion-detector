import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import random
from sklearn.metrics import roc_auc_score

from generate_logs import generate_logs
from detector import score_agents
from stress_test import targeted_delete, N, R, K, SEEDS, FRACS


def add_seq(logs):
    c = {}
    for m in logs:
        c[m["sender"]] = c.get(m["sender"], 0) + 1
        m["seq"] = c[m["sender"]]
    return logs


def gap_score(logs):
    seen = {i: set() for i in range(N)}
    for m in logs:
        seen[m["sender"]].add(m["seq"])
    return np.array([(max(s) - len(s)) if s else 0 for s in seen.values()],
                    dtype=float)


def z(x):
    sd = x.std()
    return (x - x.mean()) / (sd if sd > 0 else 1.0)


res = {"combined": [], "gap (seq numbers)": [], "fused": []}
for f in FRACS:
    a = {k: [] for k in res}
    for seed in SEEDS:
        logs, col = generate_logs(N, K, R, seed=seed)
        logs = add_seq(logs)
        t = targeted_delete(logs, col, f, random.Random(1000 + seed))
        y = np.array([i in col for i in range(N)], dtype=int)
        c = score_agents(t, N, R, "combined")
        g = gap_score(t)
        a["combined"].append(roc_auc_score(y, c))
        a["gap (seq numbers)"].append(roc_auc_score(y, g) if g.std() > 0 else 0.5)
        a["fused"].append(roc_auc_score(y, z(c) + z(g)))
    for k in res:
        res[k].append(np.mean(a[k]))
for k, v in res.items():
    print(f"{k:20s}", np.round(v, 2))
    plt.plot(FRACS, v, marker="o", label=k)
plt.axhline(0.5, color="gray", ls="--", lw=1)
plt.xlabel("Fraction of colluder-to-colluder messages deleted")
plt.ylabel("AUROC")
plt.title("Tamper-evident logging defence")
plt.legend()
plt.tight_layout()
plt.savefig("results/fig4_gap_defence.png", dpi=150)
print("Saved results/fig4_gap_defence.png")
