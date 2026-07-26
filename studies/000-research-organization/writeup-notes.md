Two months ago I set out to replicate Anthropic's [Automated Weak-to-Strong Researcher](https://alignment.anthropic.com/2026/automated-w2s-researcher/). I had and have an interest in developing autoresearchers -- AI systems capable of performing aspects of the research process over long horizons, freeing human researchers for more complex tasks. Like agents and tool use before it, autoresearchers are an emergent use case for LLMs which are likely to have impacts beyond a narrow area. The term "autoresearch" comes from Andrej Karpath's Autoresearch demo where he had an LLM brute force its way towards optimal hyperparameters while training a neural network. The W2S work from Wen et al. (2026) is an extension in some ways of that work, but illustrates the wide-ranging usefulness of autoresearchers clearly.

Wen et al. (2026) showed an Opus-tier frontier model can operate as a long-horizon autoresearcher on the Weak-to-Strong Superversion problem. In this problem a weak model is given access to ground truth labels of some data and is asked to create new labels with which to perform supervised fine tuning (SFT) on a strong model which has not seen the original ground truth, then after training the resulting model is compared to the strong model's performance when trained on the ground truth labels. The resulting metric, the "performance gap recovered", gives an objective measure of how well the weak teacher model is able to train the strong student model. Anthropic used Qwen 1.5-0.5B Chat as the weak teacher and Qwen 3-4B Base as the strong student. The problem is a useful analog in alignment research -- if a weaker intelligence can train a stronger intelligence on a problem where it is not as capable as the ground truth-trained strong model, perhaps the same could be said of humans creating ever smarter model systems.

But how can a weak teacher train a student to be better than itself? The teacher's produced labels are reflective of its understanding which may not generalize to the original ground truth. 
The problem is it isn't immediately obvious how to do this. The strong student needs to recover the idealized student's performance by way of a weaker teacher's labels -- but the teacher generalized labels to generalize back toward the ground truth, which means the teacher needs to be able to produce generalized label which reflect its


Can a weaker intelligence train a stronger intelligence such that the stronger intelligence generalizes beyond the weakner intelligence's capacity? Wen et al. showed that it can and provided an open source code implementation enabling replication relatively simply using an Anthropic API model.

When I began, I focused on a subquestion: if Opus is capable, what is the weakest model capable of filling that researcher role? If a small open source model could do the same, the cost would drop from the $18,000 the group spent on API calls and GPU hours. Part of the reason for this was cost -- I didn't want to spend $18,000 replicating their work, but I did want to learn more about the limitations of autoresearchers. 

Over time the work evolved and now seems a good time to reflect. 

So began a 2 month rabbit hole. There were two main phases: W2S Replication 
1. Setup my 3080 12GB gaming PC with Tailscale for running SFT and local language models generally (Investigation 003.001)
2. Developed a harness enabling an Ollama-based model to stand in for the Anthropic model as a researcher (Investigation 003.002)
3. Showed Qwen 3.5 4B can mechanically run the researcher loop, but training the student proved infeasible on my RTX 3080.

That was the first three 

4. Recognized that time-to-result was the limiter, shifted to StepLaw's Environment A which provides a 12x10 optimization surface. If a researcher can solve this relatively simple problem, it could signal an effetive 
