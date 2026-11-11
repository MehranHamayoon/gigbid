# A perfect evidence match still earned zero replies

Mehran Hamayoon · GigBid field notes

The first result I wanted to show in GigBid was a retrieval curve. A freelancer brings an uneven portfolio, a marketplace posting asks for a messy mix of skills, and the assistant has to find the work that actually proves the match. Better retrieval seemed like the straightforward route to a better proposal. The first simulator run exposed a gap in that story. The proposals had relevant, verifiable evidence. The clients replied to none of them.

GigBid is a freelance copilot built around an approval boundary. It scouts listings, checks fit and risk, and drafts a cover letter with evidence the user can inspect. A user approves the exact draft and its spending preview before the simulator can deduct any Connects. The same idea applies when a client asks for an interview. A separate graph suggests times, then waits for a human to approve the reply. I built the simulator and the portfolios as synthetic fixtures, so the results below describe that environment.

## The missing word was already in the portfolio

One development job asks for a churn prediction baseline. The relevant portfolio case study describes comparing logistic regression with a random forest and reporting precision and recall. That is strong evidence for the work. The portfolio record also has a skill tag called classification. The prose omits that exact word. The simulated client prefers seeing its must-have skill written explicitly, and the proposal writer originally quoted the case excerpt while omitting the skill tags.

I saw the problem because the project records enough intermediate state to trace a failed proposal. The fit matrix showed the skill supported by a real item in the synthetic portfolio. The generated text showed the excerpt and its citation. The verifier accepted it. The action succeeded, Connects were deducted, and the proposal stayed at submitted. Looking only at the retrieval ranking or at the completion status would have hidden the difference between finding a fact and communicating it.

I changed the writer to add an explicit portfolio-skills line when it quotes a case study. Both lines cite the same record. The verifier checks the excerpt against the stored text and checks the ordered skill list against that record's metadata. A citation ID alone cannot authorize a statement. A fabricated award with a valid ID still fails the check. The human can inspect the underlying record and edit the proposal. Approval re-fetches the cited evidence and rejects an edited statement whose source has disappeared or changed.

## Why the measured reply rate moved

I ran an excerpt-only arm and a skills-plus-excerpt arm on the same set of eligible local jobs. Both used the hybrid retriever, the same fair-price rule, the same approval path, and the same fixed client preferences. The excerpt-only arm received zero replies from 24 proposals. Adding the attested skill tags produced replies for all 24 in this fixture. No generated proposal in either arm had an unsupported factual claim after verification. The per-job rows and exact run settings are committed with the code.

The size of the difference reflects the simulator's scoring function. It checks an exact preferred skill token and a price ceiling. The experiment changes the text that reaches that function, so a big jump is plausible by construction. Real clients can infer a skill from methodology, react to a long generic list, or have a completely different priority from the one in the posting. There is also selection bias in the eligible jobs. Their labels were made to exercise the system, and the pilot variants share requirements with their source jobs. I would treat the paired comparison as a test that a missing part of a handoff can matter. I would need independent jobs and blinded reviewers to estimate how much it matters outside this simulator.

The test also changed what I think a useful evidence ID represents. The original implementation treated the ID as a reference to a block of text. The corrected one uses the ID as a reference to a structured record containing a source excerpt, skill tags, date, type, and outcome. That gives the writer more usable facts without asking it to infer an applicant's experience. It also gives the verifier a stronger contract. A generic similarity threshold could mistake a plausible claim about a technology for an assertion that the applicant used it on a specific project.

## Why hybrid retrieval still shipped

The local benchmark uses fixed job IDs and expected evidence. Its cosine baseline reached 67.5% evidence Recall@5. Hybrid BM25 plus cosine and reciprocal rank fusion reached 96.7%. The corrective variant reached 97.5% with a re-query path for missing requirements. V2 ships because that marginal recall gain on this small corpus did not justify the extra latency and complexity. The actual runtime queries with the structured deliverables and skill names. The offline retrieval study also includes the fuller posting text, so the ranking benchmark and the interactive path answer related questions under different input conditions.

The helpful comparison is between a good first retrieval and the rest of the pipeline. Even a case study at rank one can fail to communicate the client's preferred term. Conversely, a high reply rate from this simulator can coexist with mediocre retrieval if the proposal happens to contain the token it rewards. I would want a stronger benchmark to annotate which evidence supports each requirement, whether the proposal expresses that connection, and whether a human finds the evidence convincing. Those labels would help separate ranking quality from the mechanical response preference.

## Keeping people in the decision

A multi-agent graph made the evidence gap easier to inspect. The Scout loads a listing through the marketplace port. The Job Analyst normalizes the brief, the Risk Assessor checks client and posting signals, and the Fit Matcher builds the requirements matrix. Those branches run together and join at the bid decision. The Pricing Strategist consults the client history, the posted range, the user's floor, and a small historical market prior. The writer, verifier, critic, and compliance guard then operate on typed fields with separate responsibilities.

The orchestration also has overhead. A direct rule can make a decision much faster than a graph that checkpoints, performs MCP calls, emits node events, and produces an approval payload. A staged rule matched the graph's bid-or-skip accuracy on the local labelled subset. What the graph added was operational behavior that accuracy alone could not measure. It stops for approval and survives reopening a checkpoint. The simulator uses a tenant-scoped idempotency key, which lets a retry return the first write's result without spending twice. Keeping an audit record also makes a skipped scam or a rejected draft explainable after the run.

Risk detection came with a similar tradeoff. My fixtures include both unpaid-work posts and requests inside job text that try to dictate what the assistant should do. The detector flags known patterns and the graph ends the unsafe branch before drafting. Pattern checks remain sensitive to wording. The marketplace boundary is the second protection. A job post has no authority to sign an approval, even if a pattern is missed. Keeping marketplace write tools out of scouting and retrieval also reduces the number of places a bug can trigger an external effect.

## What I would measure next

I would collect independent proposals with judgments on four separate questions. Did the retrieval surface the best evidence? Did the proposal make its connection to the deliverable explicit? Did each factual claim survive a source check? Did the wording sound useful and specific to a real reviewer? I would label a set before calibrating an automated judge, and I would ask reviewers to compare anonymized drafts without knowing which retrieval variant produced them. I would also replace near-neighbour synthetic variants with more varied jobs and requirements that legitimately span multiple team members.

A simulated reply is a quick feedback signal. The more important result was learning where that signal entered the system. Ranking returned an appropriate item, the original writer dropped useful metadata, the verifier passed the excerpt, and the client simulator saw no explicit skill match. Improving the evidence handoff fixed that particular failure with one small, auditable change. That is the kind of outcome I want a freelancer to be able to inspect and challenge before a proposal leaves their workspace.

[Reproducible local results](https://github.com/MehranHamayoon/gigbid/tree/main/evals/results) · [Data and simulator limitations](https://github.com/MehranHamayoon/gigbid/blob/main/docs/DATA_CARD.md)
