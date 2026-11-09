import os
import csv
import random
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import roc_auc_score

from generate_logs import generate_logs, VOCAB
from detector import score_agents

N, R, K = 16, 60, 5
SEEDS = range(30)
MODES = ["volume", "edges", "content", "sync", "combined"]
FRACS = [0, 0.25, 0.5, 0.75, 0.9]
STEALTH = [0, 0.2, 0.4, 0.6, 0.8, 1.0]


def random_hide(logs, col, frac, rng):
    return [m for m in logs if rng.random() >= frac]


def targeted_delete(logs, col, frac, rng):
    return [m for m in logs if not (m["sender"] in col and m["receiver"] in col
                                    and rng.random() < frac)]


def spoof_text(logs, col, frac, rng):
    out = []
    for m in logs:
        if m["sender"] in col and rng.random() < frac:
            m = dict(m, text=" ".join(rng.sample(VOCAB, 8)))
        out.append(m)
    return out


CONDITIONS = {"Partial view (random hide)": random_hide,
              "Targeted deletion by colluders": targeted_delete,
              "Content spoofing by colluders": spoof_text}


def evaluate(mode, fn=None, frac=0.0, stealth=0.0):
    aucs, pks, coord = [], [], []
    for seed in SEEDS:
        logs, col = generate_logs(N, K, R, stealth=stealth, seed=seed)
        coord.append(sum(1 for m in logs
                         if m["sender"] in col and m["receiver"] in col))
        if fn:
            logs = fn(logs, col, frac, random.Random(1000 + seed))
        s = score_agents(logs, N, R, mode)
        y = np.array([i in col for i in range(N)], dtype=int)
        aucs.append(roc_auc_score(y, s))
        pks.append(y[np.argsort(-s)[:K]].mean())
    ci = 1.96 * np.std(aucs) / np.sqrt(len(aucs))
    return np.mean(aucs), ci, np.mean(pks), np.mean(coord)


def main():
    os.makedirs("results", exist_ok=True)
    rows = []

    fig, axes = plt.subplots(1, 3, figsize=(15, 4), sharey=True)
    for ax, (cname, fn) in zip(axes, CONDITIONS.items()):
        for mode in MODES:
            res = [evaluate(mode, fn, f) for f in FRACS]
            m = np.array([r[0] for r in res])
            c = np.array([r[1] for r in res])
            ax.plot(FRACS, m, marker="o", label=mode)
            ax.fill_between(FRACS, m - c, m + c, alpha=0.15)
            for f, r in zip(FRACS, res):
                rows.append(["exp1", cname, f, mode, r[0], r[1], r[2]])
            print(f"{cname:32s} {mode:9s} AUROC@0={m[0]:.2f} @0.5={m[2]:.2f} "
                  f"@0.9={m[-1]:.2f}")
        ax.axhline(0.5, color="gray", ls="--", lw=1)
        ax.set_title(cname)
        ax.set_xlabel("Fraction hidden / tampered")
        ax.set_ylim(0.3, 1.05)
    axes[0].set_ylabel("AUROC")
    axes[0].legend()
    plt.tight_layout()
    plt.savefig("results/fig1_tampering.png", dpi=150)
    plt.close()

    fig, ax = plt.subplots(figsize=(7, 4.5))
    coord = None
    for mode in MODES:
        res = [evaluate(mode, stealth=s) for s in STEALTH]
        m = np.array([r[0] for r in res])
        c = np.array([r[1] for r in res])
        coord = [r[3] for r in res]
        ax.plot(STEALTH, m, marker="o", label=mode)
        ax.fill_between(STEALTH, m - c, m + c, alpha=0.15)
        for s, r in zip(STEALTH, res):
            rows.append(["exp2", "stealth", s, mode, r[0], r[1], r[2]])
        print(f"stealth sweep {mode:9s}", np.round(m, 2))
    ax.axhline(0.5, color="gray", ls="--", lw=1)
    ax.set_xlabel("Colluder stealth")
    ax.set_ylabel("AUROC")
    ax.legend(loc="lower left")
    ax2 = ax.twinx()
    ax2.plot(STEALTH, coord, "k:", marker="s")
    ax2.set_ylabel("Colluder-to-colluder messages (adversary's coordination)")
    plt.title("Hiding costs coordination")
    plt.tight_layout()
    plt.savefig("results/fig2_adaptive_adversary.png", dpi=150)
    plt.close()

    grid = np.array([[evaluate("combined", random_hide, f, s)[0]
                      for f in FRACS] for s in STEALTH])
    fig, ax = plt.subplots(figsize=(6, 4.5))
    im = ax.imshow(grid, vmin=0.4, vmax=1.0, cmap="viridis", aspect="auto")
    ax.set_xticks(range(len(FRACS)), FRACS)
    ax.set_yticks(range(len(STEALTH)), STEALTH)
    ax.set_xlabel("Fraction of messages hidden from monitor")
    ax.set_ylabel("Colluder stealth")
    for i in range(len(STEALTH)):
        for j in range(len(FRACS)):
            ax.text(j, i, f"{grid[i, j]:.2f}", ha="center", va="center",
                    color="w", fontsize=8)
    plt.colorbar(im, label="AUROC")
    plt.title("Combined detector: AUROC")
    plt.tight_layout()
    plt.savefig("results/fig3_heatmap.png", dpi=150)
    plt.close()

    with open("results/results.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["exp", "condition", "x", "mode", "auroc", "ci95", "p_at_k"])
        w.writerows(rows)
    print("Saved figures and results/results.csv")


if __name__ == "__main__":
    main()
