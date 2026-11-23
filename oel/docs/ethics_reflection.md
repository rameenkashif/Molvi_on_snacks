# Ethics and reflection

Rameen Kashif (456834) | Manal Aslam (465734) | Zainab Ali Bangash (486688)

**Who is affected by a wrong decision.** Customers whose parcels arrive late or never (a
stolen parcel in our model stands for a missed delivery, a theft or a parcel taken by a
competitor); pedestrians and other road users if a real robot is sent across a flooded ford
or a mud track because a planner assumed deterministic motion; the operator, who carries the
liability when a dispatcher accepts an instruction it cannot satisfy; and the courier staff
whose workload is planned around the robot's promised arrival times. An LLM dispatcher adds
a second risk: it can sound confident while ignoring a constraint ("avoid fords") or inventing
a stop that does not exist, and a human may act on that text.

**Safeguards in our design.**
1. *Validation before execution* — every LLM tool call is checked against the instance (names,
   stop ids, terrain, feasibility); invalid calls are refused with an explanation instead of
   being silently "repaired".
2. *The LLM never moves the robot directly* — it can only call our verified planners, which are
   tested for optimality (A\* = UCS) and admissibility/consistency of the heuristic.
3. *Infeasibility is reported, not hidden* — impossible requests (S3 while avoiding fords, cost
   < 100) must be answered as infeasible; we score the model on exactly that.
4. *Uncertainty is modelled* — slip and the rival are simulated; the agent replans after every
   slip and when the dam opens, and the flood is temporary so the agent is never trapped.
5. *Reproducibility and auditability* — every number is seeded from our CMS IDs, every LLM
   response is cached and every Thought/Action/Observation trace is stored.

**Reflection.** The most instructive failures were our own: the first heuristic was
admissible but not consistent, two evaluation features caused the agent to stall, and the
Manhattan baselines from the handout became inadmissible once tunnels existed. Each was found
by testing a property exhaustively rather than trusting the derivation, which is the main
lesson we take from the OEL. The blocker with stealing remains strong on our map (draws are
the most common outcome); a real system would need either faster agents or cooperation
rules, not only better search.
