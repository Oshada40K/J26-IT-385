# CareerNova -- Development Fixes and Enhancements

**Component 01:** AI-Based Semantic Skill Assessment and Skill Gap
Identification Model\
**Purpose:** Implementation checklist based on supervisor feedback.

## 1. Multi-Domain CV Support

-   Extend CV analysis beyond Software Engineering.
-   Support: Software Engineering, Data Science, Data Analytics, UI/UX
    Design, Networking, Cybersecurity, Cloud Computing, Database
    Administration, IT Support, and AI/ML.
-   Detect the candidate's domain automatically from CV content.
-   Display skills relevant to the detected domain.

## 2. Dynamic Skill Extraction

-   Extract skills from CV text, projects, education, internships, and
    work experience.
-   Categorize skills dynamically:
    -   Technical skills
    -   Programming languages
    -   Frameworks and libraries
    -   Tools and platforms
    -   Databases
    -   Domain-specific skills
    -   Soft skills
-   Recognize related skill names and avoid duplicates.
-   Do not restrict extraction to a fixed skill list.

## 3. Percentage-Based Proficiency Assessment

-   Add a percentage score for each identified skill.
-   Retain the existing five-level proficiency classification.
-   Display scores using progress bars or equivalent indicators.
-   Define a consistent scoring method based on available evidence.
-   Label scores as estimated proficiency, not verified ability.

## 4. Explainable AI (XAI)

-   Explain why each skill was identified.
-   Show the CV text or other evidence supporting the skill.
-   Explain the factors contributing to each proficiency score.
-   Distinguish self-reported skills from practical evidence.
-   Show evidence limitations and confidence separately from
    proficiency.

## 5. Multi-Source Data Input

-   Allow users to submit:
    -   CV / Resume
    -   GitHub profile URL
    -   LinkedIn profile URL
-   Obtain information only through permitted access methods and user
    authorization.
-   Handle unavailable or inaccessible sources gracefully.

## 6. Independent Source Analysis

-   Analyse each source separately before combining results.
-   Generate an independent skill profile for:
    -   CV
    -   GitHub
    -   LinkedIn
-   Show source-specific skills, evidence, estimated proficiency, and
    explanations.
-   Do not treat missing evidence in a source as proof that the
    candidate lacks a skill.

## 7. Cross-Source Skill Comparison

-   Compare skills identified across CV, GitHub, and LinkedIn.
-   Identify skills found in multiple sources.
-   Identify skills found in only one source.
-   Highlight differences between claimed skills and practical evidence.
-   Show the evidence source for every compared skill.

## 8. Skill Gap Identification

-   Allow comparison against a selected job role or career profile.
-   Identify required skills that are missing or weakly evidenced.
-   Display matched skills and skill gaps.
-   Recommend relevant skills for improvement.

## 9. Assessment Dashboard

-   Create separate summary sections for CV, GitHub, and LinkedIn.
-   Display skill categories and proficiency percentages.
-   Include five-level proficiency labels.
-   Show evidence and XAI explanations for each skill.
-   Add a combined cross-source comparison view.

## 10. Assessment Report

-   Generate a downloadable assessment report.
-   Include detected domain, source summaries, skill scores, evidence,
    XAI explanations, and skill gaps.
-   Clearly state which sources were available and analysed.

## 11. Suggested Technical Approach

-   Use NLP and semantic similarity for skill identification.
-   Consider Sentence-BERT embeddings for matching skill descriptions.
-   Use a skill taxonomy as a reference, not as a hard limit on
    extraction.
-   Define and validate the proficiency scoring methodology.
-   Use suitable XAI methods for model-level explanations and evidence
    highlighting for extracted information.

## 12. Recommended Implementation Order

1.  Multi-domain CV support and domain detection.
2.  Dynamic skill extraction and categorization.
3.  Percentage-based proficiency scoring.
4.  XAI explanations for CV-based results.
5.  GitHub and LinkedIn input and independent analysis.
6.  Cross-source skill comparison.
7.  Skill gap identification.
8.  Dashboard updates and downloadable report.
9.  Testing, validation, and documentation.

## 13. Key Validation Tasks

-   Test CVs from different IT domains.
-   Check that irrelevant and duplicate skills are not displayed.
-   Verify that each score has traceable supporting evidence.
-   Test cases where GitHub or LinkedIn data is unavailable.
-   Evaluate skill extraction and proficiency estimates using labelled
    test examples.
-   Check that explanations accurately reflect the model's decisions.