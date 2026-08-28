# Executive Presentation Timing Log & Rehearsal Audit

**System Name:** Reflex On-Demand Dispatch & Chain of Custody System  
**Document Classification:** Rehearsal Timing Audits & Speaker Handoff Logs  
**Target Duration:** 10:00 Minutes (Green Zone: 09:30 to 10:00 Minutes)  
**Pod:** Commit Crew (Group 92)  

---

## 1. Executive Timing Summary & Progression

To guarantee precision during the live defense panel, the Commit Crew executed three structured rehearsal cycles. Each dry-run was timed per speaker, auditing handoff transitions, slide pacing and live system demonstration triggers.

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        REHEARSAL PACING PROGRESSION SUMMARY                            │
├──────────────┬──────────────────┬──────────────┬─────────────────┬─────────────────────┤
│ REHEARSAL    │ DATE             │ TOTAL TIME   │ VARIANCE        │ STATUS              │
├──────────────┼──────────────────┼──────────────┼─────────────────┼─────────────────────┤
│ Dry-Run 1    │ August 26, 2026  │ 12:45 Min    │ +2:45 (Over)    │ Pacing Bottlenecks  │
│ Dry-Run 2    │ August 27, 2026  │ 10:38 Min    │ +0:38 (Over)    │ Refined Transitions │
│ Dry-Run 3    │ August 28, 2026  │ 09:48 Min    │ -0:12 (Optimal) │ Frozen & Ready      │
└──────────────┴──────────────────┴──────────────┴─────────────────┴─────────────────────┘
```

---

## 2. Dry-Run 1: Initial Baseline Rehearsal (Day 2)

* **Date:** Wednesday, August 26, 2026
* **Session Type:** Internal Pod Timing & Storyboard Check (No Scoring)
* **Goal:** Establish raw timing baselines, identify slide redundancies and test unscripted speaker handoffs.

### Timing Breakdown:

| Segment | Assigned Speaker | Planned Budget | Actual Time | Segment Variance |
| :--- | :--- | :--- | :--- | :--- |
| **1. The Kenyan Problem** | Jesse Vincent | 01:45 Min | 02:40 Min | +0:55 (Over) |
| **2. The Reflex Solution** | Silvya Atieno | 01:15 Min | 01:50 Min | +0:35 (Over) |
| **3. Architecture & Data** | Aphane Ginah | 01:45 Min | 02:20 Min | +0:35 (Over) |
| **4. Live Interactive Demo**| Peter Kuria | 02:45 Min | 03:25 Min | +0:40 (Over) |
| **5. Trade-Offs & Roadmap**| Ahmed Abdi Ibrahim | 01:45 Min | 01:50 Min | +0:05 (Over) |
| **6. Conclusion & Q&A Open**| Jesse Vincent | 00:45 Min | 00:40 Min | -0:05 (On Time)|
| **TOTALS** | **Full Pod** | **10:00 Min** | **12:45 Min** | **+2:45 (Over Time)**|

### Identified Bottlenecks & Critique:
1. **Problem Framing Over-Explanation:** Jesse spent 2 minutes and 40 seconds giving historical retail context rather than getting directly to the three operational failures.
2. **Demo Latency & Window Juggling:** Peter experienced a 20-second delay switching browser tabs between the retailer view and customer tracker.
3. **Redundant Architecture Explanations:** Aphane and Ahmed had overlapping explanations regarding the async queue and database concurrency.

### Remediation Action Plan:
* Tightened Problem Framing into three crisp bullet points (Accountability Void, Status Blindness, POD Breakdown).
* Pre-arranged browser windows side-by-side on Peter's screen to eliminate tab juggling during the live demo.
* Clear ownership boundary established: Aphane owns persistence/WAL mode while Ahmed owns async event dispatching.

---

## 3. Dry-Run 2: Mock Panel Session (Day 3)

* **Date:** Thursday, August 27, 2026
* **Session Type:** Formal Mock Panel Rehearsal with Peer Reviewers
* **Goal:** Test revised transitions, enforce strict speaker verbal cues and rehearse cross-examination defense under the State ➔ Context ➔ Evidence framework.

### Timing Breakdown:

| Segment | Assigned Speaker | Planned Budget | Actual Time | Segment Variance |
| :--- | :--- | :--- | :--- | :--- |
| **1. The Kenyan Problem** | Jesse Vincent | 01:45 Min | 01:50 Min | +0:05 (Near Target) |
| **2. The Reflex Solution** | Silvya Atieno | 01:15 Min | 01:18 Min | +0:03 (Near Target) |
| **3. Architecture & Data** | Aphane Ginah | 01:45 Min | 01:42 Min | -0:03 (On Time) |
| **4. Live Interactive Demo**| Peter Kuria | 02:45 Min | 03:08 Min | +0:23 (Slight Over)|
| **5. Trade-Offs & Roadmap**| Ahmed Abdi Ibrahim | 01:45 Min | 01:55 Min | +0:10 (Slight Over)|
| **6. Conclusion & Q&A Open**| Jesse Vincent | 00:45 Min | 00:45 Min | 00:00 (Exact) |
| **TOTALS** | **Full Pod** | **10:00 Min** | **10:38 Min** | **+0:38 (Slight Over)**|

### Peer & Instructor Critique Received:
1. **Demo Commentary Coordination:** During the live demo, Peter waited for the backend response before explaining what he clicked. He was advised to speak over the action simultaneously.
2. **Trade-Off 2 Evidence Depth:** When asked about SQLite WAL mode during mock Q&A, the initial answer was too theoretical. Ahmed was advised to cite the explicit PRAGMA configuration and test numbers.
3. **Transition Crispness:** Verbal handoffs were slightly hesitant between Silvya and Aphane.

### Remediation Action Plan:
* Scripted exact dual-action narration for the live demo so typing and speaking occur in parallel.
* Embedded the State ➔ Context ➔ Evidence cheat sheet directly into `docs/TRADEOFFS.md`.
* Standardized explicit verbal handoff cues: *"Over to you, Silvya"*, *"Aphane, walk us through the architecture"*, *"Peter, show us Reflex in action"*, *"Ahmed, walk us through the trade-offs"*, *"Jesse, take us home"*.

---

## 4. Dry-Run 3: Final Pre-Freeze Rehearsal (Day 4)

* **Date:** Friday, August 28, 2026
* **Session Type:** Locked Dress Rehearsal & Live Screen Synchronization
* **Goal:** Final pacing freeze, flawless verbal handoffs and complete alignment within the 10:00-minute presentation window.

### Timing Breakdown:

| Segment | Assigned Speaker | Planned Budget | Actual Time | Segment Variance |
| :--- | :--- | :--- | :--- | :--- |
| **1. The Kenyan Problem** | Jesse Vincent | 01:45 Min | 01:38 Min | -0:07 (Optimal) |
| **2. The Reflex Solution** | Silvya Atieno | 01:15 Min | 01:10 Min | -0:05 (Optimal) |
| **3. Architecture & Data** | Aphane Ginah | 01:45 Min | 01:40 Min | -0:05 (Optimal) |
| **4. Live Interactive Demo**| Peter Kuria | 02:45 Min | 02:42 Min | -0:03 (Optimal) |
| **5. Trade-Offs & Roadmap**| Ahmed Abdi Ibrahim | 01:45 Min | 01:50 Min | +0:05 (Optimal) |
| **6. Conclusion & Q&A Open**| Jesse Vincent | 00:45 Min | 00:48 Min | +0:03 (Optimal) |
| **TOTALS** | **Full Pod** | **10:00 Min** | **09:48 Min** | **-0:12 (Optimal Green Zone)**|

---

## 5. Comparative Timing Variance Matrix

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        SEGMENT TIMING COMPARISON ACROSS RUNS                           │
├──────────────────────────┬──────────────┬──────────────┬──────────────┬────────────────┤
│ SEGMENT                  │ DRY-RUN 1    │ DRY-RUN 2    │ DRY-RUN 3    │ NET DELTA      │
├──────────────────────────┼──────────────┼──────────────┼──────────────┼────────────────┤
│ 1. The Kenyan Problem    │ 02:40 Min    │ 01:50 Min    │ 01:38 Min    │ -1:02 (-39%)   │
│ 2. The Reflex Solution   │ 01:50 Min    │ 01:18 Min    │ 01:10 Min    │ -0:40 (-36%)   │
│ 3. Architecture & Data   │ 02:20 Min    │ 01:42 Min    │ 01:40 Min    │ -0:40 (-29%)   │
│ 4. Live Interactive Demo │ 03:25 Min    │ 03:08 Min    │ 02:42 Min    │ -0:43 (-21%)   │
│ 5. Trade-Offs & Roadmap  │ 01:50 Min    │ 01:55 Min    │ 01:50 Min    │  0:00 (Stable) │
│ 6. Conclusion & Q&A Open │ 00:40 Min    │ 00:45 Min    │ 00:48 Min    │ +0:08 (+20%)   │
├──────────────────────────┼──────────────┼──────────────┼──────────────┼────────────────┤
│ TOTAL TIME               │ 12:45 Min    │ 10:38 Min    │ 09:48 Min    │ -2:57 (-23%)   │
└──────────────────────────┴──────────────┴──────────────┴──────────────┴────────────────┘
```

---

## 6. Live Timekeeping Protocol & Emergency Compression

To maintain precision during the live defense panel, the following operational safeguards are enacted:

* **Designated Timekeeper:** Silvya Atieno will monitor a shared digital stopwatch and drop discrete visual alerts in the team backchannel:
  * **At 05:00 Elapsed:** "Midpoint Reached (Demo Starting)"
  * **At 08:00 Elapsed:** "2 Minutes Remaining (Trade-Offs)"
  * **At 09:00 Elapsed:** "1 Minute Remaining (Wrap-Up)"
* **Emergency Compression Protocol:** If the live demo runs 30 seconds over budget, Ahmed will compress Slide 7 (Roadmap) into a single spoken sentence (*"Our immediate roadmap focuses on USSD integration and Daraja STK escrow release"*) to guarantee Jesse takes the floor for final handover at exactly 09:15.