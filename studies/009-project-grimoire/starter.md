# 

## Driving Questions

1. What text in a prompt will align a model's outputs to the ground truth data for a particular corpus?
2. Can we use ablation studies to empirically derive principles for a prompt to improve a model's performance against an arbitrary ground truth given a corpus of documents and a ground truth resulting from those documents?
3. Can we compare the derived principles to a known human supplied source of principles
4. Can we take principles and use fine tuning methods to align models to those principles instead of embedding those principles in the prompt?


## Components

### Ground Truth Data
The Pydantic model is groudn truth specific. In the case of the CUAD, it includes:

```
class CUADDecisionUnit(BaseModel):
    category: str = Field(
        description=''
    ),
    spans: list[str] = Field(
        description='The '
    )
```

There are 41 Categories in CUAD. This would likely be an enum for this work, but other datasets may differ.

### Scoring
Scoring depends on the format of the ground truth data and the problem at hand. For CUAD there's both category scoring and span scoring. Special attention has to be paid here to how the original dataset and models applied were scored -- in CUAD's case, there was a ranked scoring criteria applied that doesn't make sense for an LLM. We shifted to ContractEval which used LLMs on CUAD, but it didn't account for false negatives very well.

In general, sticking to FN/FP/TP/TN counting and then deriving precision, recall, F1, and F2 (when recall is more important) is a good rule of thumb starting place.

However, it's likely in the future we'll need more sophisticated scoring as scoring will become a reward function which will differ depending on the problem.

### Principle

```
class Principle(BaseModel):
    statement: str = Field(
        description: 'A discrete instruction or guidance for how to handle a circumstance.'
    ),
    trigger: str = Field(
        description: 'When this principle should be applied'
    ),
    origin: str = Field(
        description: "How the principle was identified. Typical values include 'expert-derived', 'empirically-derived', 'non-expert-suggested'"
    )

```

### Dataset Splits
At a minimum we need the following:
- Principle Training Set
    - What we derive principles from
- Principle Validation Set
    - What we evaluate on for principles

The above enables us to derive principles from the training set, escalate across the training set (n=1 --> n=5 --> n=20 --> n=full training set), and then externally validate on a clean dataset that the principles are generalized onto new documents.

However we also want to try (1) fine tuning directly on the resulting data and (2) fine tuning with emmission of principles (similar to rewarding chain of though) after we've proven the principle extraction engine can work. So we also have two additional splits:
3. Fine Tuning Training
4. Fine Tuning Validation

For cleanliness, we also set a small n<5 set of documents which we use to get setup with the dataset -- defining data contracts in the form of Pydantic models, harness requirements, tools, etc. We won't derive principles or fine tune against these documents, but we leverage their shape to determine how to build the rest around it. 

### Standard Runner

Inputs:
- Document: str
- Task Description: str
- Principles: str (assembled from JSON)
- Model config: dict

Outputs:

```
class Decision(CUADDecisionUnit):
    cited_principles: list[Principle] = Field(
        description: 'A list of the principles used to make this decision.'
    ),
    citation_explanation: str = Field(
        description: 'A description of why the cited principles were cited for this Decision.'
    )

```

In the case of no principles supplied, Decisions would simply be null for cited_principles and citation_explanation.

### Visualization
We need a way to compare visually the outputs from different models or different versions of principles or to the ground truth or the baseline output, etc. The point of this is that many issues are innately obvious from either exploratory data analysis or from simply looking at a single ground truth vs. model output overlaid on top of the document.

Say we're curious if there's an Agreement Date in a contract. The ground truth says there is and it says "Agreement Date: January 1, 2010". The model says something else and it doesn't reach the Jaccard ratio threshold for overlap. But when we look at the actual model output it says "January 1, 2010". It got the important bit, but wasn't perfect. So what's wrong here? We had the right category, the span was off, but it's really a scoring issue. We could solve it by changing the scoring, by proposing a new principle to solve the issue, or adjusting existing principles to cover this case. Which one we should do is much easier to see visually than empirically -- all we see empirically is it didn't pass the threshold. This is a hypothetical, so the actual answer doesn't matter, but this seems like an issue of convention so it should be governed by a newly proposed principle and probably checked against other documents to see if it's consistent.

## Process

### Setup
1. Establish Baseline of Performance (from past work)
    - What is the existing performance against the dataset? Is there an originating paper or a followup paper? Can we rerun it and replicate the results?
    - This step is necessary for academic comparison, but not strictly speakign necessary to the system. However, it frequently raises issues which previous authors solved for us, so it's useful to do as an exercise before entering the rest of the process.
2. Perform Exploratory Data Analysis of Ground Truth Dataset
3. Form Pydantic Models for Ground Truth Dataset Decisions
4. Establish Scoring Criteria
5. Perform Dataset Split
6. Establish Task Definition
7. Assemble Prompt from 1 Document, Task Definition, No Principles, Decision Pydantic Model as Structured Output

Validation: We compare the outputs from #1 to #7 using #4 on a single document from #5's requirements split. If we can do this successfully, we can move onto the Principle Derivation Loop.

### Principle Testing Loop (PTL)
* Run Current Model
* Run Current Model + Proposed Principle
* Compare Performance on Document Set

### Principle Escalation
* Intended Impact Assessment
    - Execute Principle Testing Loop on n=1
    - Given the problem the principle is supposed to solve and the document it's meant to solve it in, does it solve the problem in that document?
* Generalizable Impact Assessment
    - Execute PTL on n=3-5 where principle should be applied
    - Requires having set of candidate documents where we expect principle to be applied
* Regression Assessment
    - Execute PTL on n=10-20 where principle may or may not be applied
    - Should verify there are documents where the principle shouldn't be applied and where it should.
* Training Set Assessment
    - Execute PTL on full training dataset and establish performance effect
    - If it improves it, becomes a part of "current best model".

In general, failures at any of these steps should be logged. Some mean the principle isn't viable; some mean the language needs to be adjusted; some the principle may have interaction effects with other principles and they should be consolidated in some way.

Why do this? Each trial is cheap at n=1, but more expensive the higher you get up the ladder. Further, issues are often observable with a principle at small n, but at larger n it's harder to see why it's failing. Starting small places the observability and validation at the forefront and escalation serves to establish generalizability.

### Principle Proposal

Principles can come from a few sources:
* Trusted Written Source
    - Often a handbook or set of Statements of Protocols (SOPs)
* Expert Source
    - An expert provides a principle. Practically similar to Trusted Written Source
* Gap Observation
    - LLM proposed principle based upon a gap between a model's outputs and the ground truth. These we have to be careful not to just write the answer, otherwise it won't generalize.
    - These are the most common.
* Ground Truth Trend
    - LLM's exploratory data analysis identifies a trend and proposes a principle based upon it. I.e. This Category is in 60% of contracts and usually starts with this text (not always though -- additional room for refinement)
    - Common at the outset, prior to having employed principles.

In general, the Gap Observation and Ground Truth Trend are the most common ways to get principles. Principles regardless of source are only accepted after undergoing Principle Escalation and showing their merit in the full dataset.

## Next Steps and Validation

We propose to build the system above using the CUAD dataset which is contained within /morel-research/studies/009-project-grimoire/data/ with subdirectories processed/ containing splits and basic stats about the dataset which serves as non-exhaustive starting point for exploratory data analysis and raw/ which features the category_descriptions.csv for use in Pydantic models and potential task descriptions and the data.zip and CUADv1.json which are the core dataset, unprocessed in its original form. The success of such a system will be defined by the following:
1. Does the system show evidence of having completed the Setup?
2. Does the system have clear, obvious answers about the model inputs, outputs, the prompt supplied to the model in the base case, how the performance of the model compared to the relevant paper's model (ContratEval in this case) and the base case model vs. the ground truth in an up to 5 document sample from the requirements set? If the system doesn't offer these answers clearly and understandably to a human, it will be considered to have failed.
3. Can the system propose a principle? Is it clear and obvious what that principle is? Is that principle stored in a manner that enables scalability (i.e. a JSON format with versioning)?
4. Can the system successfully execute the PLT on n=1 document (Intended Impact Assessment), regardless of whether the principle proposed in #3 worked?

Note that escalation beyond n=1 is considered out of scope for the initial validation.

## Open Questions
Assuming the above works, we begin to ask several research questions:
1. Does a full iteration of Principle Escalation yield at least one principle which improves the performance of the model on the full training dataset?
2. What is the action set available to the model? I.e. Propose a Principle, Remove a Principle, and Modify a Principle are all valid options. But what other actions are valid? Types of document routing? Tool availability (i.e. Define a Tool)? Lots of options. At least initially we'll limit it to Propose, Remove, Modify.
3. At what steps can the action set be applied? At the outset of a principle n=1 certainly, but what about upper level in the escalation? Can just one principle be modified or can multiple be removed, added, or modified?
4. How are principles combined and at what steps? Is it just at the full training dataset level? What if principles have an interaction effect?
5. How many parallel streams of principle escalation can be employed? How should they pass information between each other such that duplication is minimized? How are they combined?
6. What LLMs should be applied in different roles? Candidate models are Qwen3.5-9B, InklingSmall, and GLM-5.3-Flash, more to come after initial attempts. My sense is we can build with Qwen3.5-9B to keep costs in check through n=1 validation, then consider again what to do. HuggingFace inference enables us to shift between them. /morel-research/.env has the HF_TOKEN. 
7. What should our reward function look like? Should we have a loss (i.e. cross-entropy loss or otherwise)? How do we balance various things to be rewarded, such as Recall, Precision, overall Accuracy, Category Accuracy vs. Span Accuracy, etc.?
8. What fine tuning methods available through Tinker (Thinking Machines) should we consider for this problem? How does our data need to be organized to do so? 