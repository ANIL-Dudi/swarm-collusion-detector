import random
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import roc_auc_score

from generate_logs import generate_logs
from detector import score_agents
from stress_test import random_hide, targeted_delete

R = 60
SEEDS = range(15)


def number(logs):
    c = {}
    for m in logs:
        c[m["sender"]] = c.get(m["sender"], 0) + 1
        m["seq"] = c[m["sender"]]
    return logs


def gap(logs, n):
    seen = [set() for _ in range(n)]
    for m in logs:
        seen[m["sender"]].add(m["seq"])
    return np.array([(max(s) - len(s)) if s else 0 for s in seen], float)


def z(x):
    sd = x.std()
    return (x - x.mean()) / (sd if sd > 0 else 1.0)


def auc(col, n, s):
    y = np.array([i in col for i in range(n)], dtype=int)
    return roc_auc_score(y, s)


def ncc(logs, col):
    return sum(1 for m in logs if m["sender"] in col and m["receiver"] in col)


# ---- 1. Scale: does it hold beyond 16 agents? ----
print("== Scale test (combined detector) ==")
sizes = [16, 32, 64]
conds = [("clean", None, 0), ("50% hidden", random_hide, 0.5),
         ("50% colluder msgs deleted", targeted_delete, 0.5)]
fig, ax = plt.subplots(figsize=(7, 4))
w = 0.25
for ci, (cn, fn, f) in enumerate(conds):
    vals = []
    for n in sizes:
        k = round(n * 5 / 16)
        a = []
        for seed in SEEDS:
            logs, col = generate_logs(n, k, R, seed=seed)
            if fn:
                logs = fn(logs, col, f, random.Random(1000 + seed))
            a.append(auc(col, n, score_agents(logs, n, R, "combined")))
        vals.append(np.mean(a))
        print(f"N={n:3d} {cn:28s} AUROC={np.mean(a):.2f}")
    ax.bar(np.arange(3) + ci * w, vals, w, label=cn)
ax.set_xticks(np.arange(3) + w, [f"{n} agents" for n in sizes])
ax.set_ylabel("AUROC")
ax.set_ylim(0, 1.05)
ax.axhline(0.5, color="gray", ls="--", lw=1)
ax.legend(fontsize=8)
plt.title("Scaling the population")
plt.tight_layout()
plt.savefig("results/fig5_scale.png", dpi=150)
plt.close()

# ---- 2. Worst-case adversary: search over stealth x deletion ----
print("== Worst-case adversary search (N=16) ==")
N, K = 16, 5
STE = [0, 0.2, 0.4, 0.6, 0.8]
DEL = [0, 0.25, 0.5, 0.75, 0.9]
base = np.mean([ncc(generate_logs(N, K, R, seed=s)[0],
                    generate_logs(N, K, R, seed=s)[1]) for s in SEEDS])
G_c = np.zeros((len(STE), len(DEL)))
G_f = np.zeros_like(G_c)
G_k = np.zeros_like(G_c)
for i, st in enumerate(STE):
    for j, d in enumerate(DEL):
        ac, af, ak = [], [], []
        for seed in SEEDS:
            logs, col = generate_logs(N, K, R, stealth=st, seed=seed)
            logs = number(logs)
            t = targeted_delete(logs, col, d, random.Random(1000 + seed))
            c = score_agents(t, N, R, "combined")
            g = gap(t, N)
            ac.append(auc(col, N, c))
            af.append(auc(col, N, z(c) + z(g)))
            ak.append(ncc(logs, col))
        G_c[i, j], G_f[i, j], G_k[i, j] = np.mean(ac), np.mean(af), np.mean(ak)
fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
for ax, G, t in zip(axes, [G_c, G_f],
                    ["Combined detector", "Combined + sequence-gap defence"]):
    im = ax.imshow(G, vmin=0, vmax=1, cmap="viridis", aspect="auto")
    ax.set_xticks(range(len(DEL)), DEL)
    ax.set_yticks(range(len(STE)), STE)
    ax.set_xlabel("Fraction of colluder messages deleted")
    ax.set_ylabel("Stealth")
    ax.set_title(t)
    for i in range(len(STE)):
        for j in range(len(DEL)):
            ax.text(j, i, f"{G[i, j]:.2f}", ha="center", va="center",
                    color="w", fontsize=8)
plt.colorbar(im, ax=axes, label="AUROC")
plt.savefig("results/fig6_worst_case.png", dpi=150, bbox_inches="tight")
plt.close()
ok = G_k >= 0.5 * base
print(f"Baseline colluder-colluder msgs: {base:.0f}; adversary must keep "
      f">=50% ({0.5 * base:.0f}) to still coordinate")
for name, G in [("combined", G_c), ("fused", G_f)]:
    M = np.where(ok, G, np.inf)
    i, j = np.unravel_index(np.argmin(M), M.shape)
    print(f"Worst case for {name}: stealth={STE[i]} delete={DEL[j]} "
          f"AUROC={G[i, j]:.2f}")

# ---- 3. Attack on the defence: attacker forges sequence numbers ----
print("== Defence vs forged sequence numbers ==")
rows = {"combined": [], "fused (honest logger)": [],
        "fused (attacker renumbers)": []}
for d in DEL:
    a = {k: [] for k in rows}
    for seed in SEEDS:
        logs, col = generate_logs(N, K, R, seed=seed)
        logs = number(logs)
        t = targeted_delete(logs, col, d, random.Random(1000 + seed))
        c = score_agents(t, N, R, "combined")
        a["combined"].append(auc(col, N, c))
        a["fused (honest logger)"].append(auc(col, N, z(c) + z(gap(t, N))))
        t = number(t)
        a["fused (attacker renumbers)"].append(
            auc(col, N, z(c) + z(gap(t, N))))
    for k in rows:
        rows[k].append(np.mean(a[k]))
for k, v in rows.items():
    print(f"{k:28s}", np.round(v, 2))
    plt.plot(DEL, v, marker="o", label=k)
plt.axhline(0.5, color="gray", ls="--", lw=1)
plt.xlabel("Fraction of colluder messages deleted")
plt.ylabel("AUROC")
plt.legend(fontsize=8)
plt.title("Sequence numbers help only if the logger is trusted")
plt.tight_layout()
plt.savefig("results/fig7_forged_seq.png", dpi=150)
print("Saved fig5, fig6, fig7")
