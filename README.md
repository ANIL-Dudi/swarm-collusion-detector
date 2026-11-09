# Swarm Collusion Detector

**Track 4 (Multi-Agent Oversight and Control), Swarm Alignment Hackathon 2026**

Can a monitor detect colluding agents in a multi-agent system when it sees only
part of the logs, when colluders delete or spoof their own messages, or when
colluders actively try to look honest?

## Threat model
- 16 agents, 5 of them hidden colluders, 60 rounds of messaging.
- Colluders message each other more, share code words, and act in synchronized
  bursts.
- The monitor sees message logs only. It does not know who the colluders are.
- Adversary capabilities tested: (1) the monitor sees only a fraction of
  messages, (2) colluders delete their own coordination messages, (3) colluders
  overwrite message text, (4) colluders trade coordination for stealth.

## Method
- `src/generate_logs.py`: synthetic multi-agent logs with a `stealth` parameter
  for an adaptive adversary.
- `src/detector.py`: per-agent coordination score from four signals:
  `volume` (naive baseline), `edges` (communication graph), `content` (TF-IDF
  similarity), `sync` (correlated activity timing), plus `combined`.
- `src/stress_test.py`: AUROC and 95% CIs over 30 seeds for all conditions.
- `src/gap_defence.py`: tamper-evident logging defence using per-agent
  sequence numbers to detect deleted messages.

## Run
    pip install -r requirements.txt
    python src/stress_test.py
    python src/gap_defence.py

Outputs go to `results/`.

## Key findings
1. **Fusing signals beats the baseline under partial observation.** With 50% of
   messages hidden, combined AUROC is 1.00 versus 0.80 for message volume.
2. **Log deletion by the adversary is the main threat.** If colluders delete
   their own coordination messages, combined AUROC falls to 0.12 at 90%
   deletion, below chance, because the colluders end up looking quieter than
   honest agents. The monitor can be inverted, not just blinded.
3. **Hiding has a cost.** As stealth rises to 1.0, every detector falls to
   chance (AUROC about 0.47-0.51), but colluders also stop coordinating.
4. **Content spoofing barely hurts** (AUROC 1.00 at 90% spoofed), because
   graph signals are untouched and a few surviving code words suffice. This
   mostly shows our spoofing adversary is weak.
5. **Tamper-evident defence:** (fill in after running `gap_defence.py`)

![Tampering](results/fig1_tampering.png)
![Adaptive adversary](results/fig2_adaptive_adversary.png)
![Heatmap](results/fig3_heatmap.png)
![Gap defence](results/fig4_gap_defence.png)

## Limitations
- Synthetic data only. Next step: replay on AI Village transcripts and
  Swarm Traces payloads.
- Colluders follow a fixed strategy and do not learn against the detector.
- Small population (16 agents); behavior at swarm scale is untested.
- The gap defence assumes sequence numbers are written by a trusted logger.
