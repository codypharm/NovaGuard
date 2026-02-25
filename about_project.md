# About Nova Guard

## What Inspired Me
I built Nova Guard because I am a pharmacist in tech working at the intersection of healthcare and technology, holding dual degrees in Pharmacology and Pharmacy. Every day, I found myself manually reviewing complex prescriptions, running a mental checklist that had to factor in a massive, multi-dimensional web of data: drug-specific issues, patient demographics, active comorbidities, pharmacogenomics (PGx), and fluctuating laboratory values. 

Doing this entirely in your head or by constantly switching between five different clinical databases is cognitively exhausting and highly prone to human error, not just for me, but for every pharmacist and clinician on the floor. I wanted to build a product that acts as a definitive safety layer; an intelligent clinical companion that automatically synthesizes all patient and drug factors to make medication management faster, safer, and infinitely more reliable.

## How I Built It
Nova Guard is designed as a high-performance, AI-driven Clinical Decision Support System (CDSS). 

**The Tech Stack:**
*   **Frontend:** A responsive, hyper-focused UI built with **React**, **TypeScript**, **TailwindCSS**, and **Shadcn UI**. State management is optimized so pharmacists can drag-and-drop lab reports directly into patient profiles instantly.
*   **Backend & Security:** A robust **Python** server utilizing **FastAPI** for asynchronous endpoint delivery, paired with **SQLAlchemy** and **PostgreSQL** for secure patient data persistence. The entire data pipeline is built from the ground up to be **HIPAA compliant**, ensuring all Protected Health Information (PHI) is handled securely, both at rest and in transit.
*   **Clinical Data Infrastructure:** To ensure absolute clinical accuracy, the app integrates deeply with **National Library of Medicine (NLM)** and **FDA APIs**, specifically utilizing **RxNorm**, **RxClass**, **DailyMed**, and the **OpenFDA** datasets to retrieve highly structured, verified drug labels.
*   **AI Orchestration:** The core "brain" of Nova Guard is powered by **AWS Bedrock** , **Open AI Api** and the **Amazon Nova** model family (Micro, Lite, Sonic). I also utilized **LangGraph** to build sophisticated, multi-step clinical reasoning agents that operate on top of the structured FDA data.

**Core Features:**
Nova Guard doesn't just read data; it actively interprets it. 
1.  **Multi-Modal Inputs (Text, Vision & Voice):** Utilizing Amazon Nova, the system can extract structured biomarker data directly from physical laboratory reports via image recognition as well as extract medications in a precritpion with required informations. Furthermore, I integrated **Amazon Nova 2 Sonic** to enable hands-free voice dictation. Pharmacists can verbally review cases, transcribe their speech to text for submission, and the system can even read the clinical response back aloud, ideal for sterile compounding environments or busy sterile workflows.
2.  **Safety Matrix & Counseling Generator:** Analyzes complete medication protocols against patient history to provide a 3-point expert consensus for patient counseling.
3.  **Advanced Clinical Calculators:** The system natively implements strict pharmacokinetic equations, such as the Cockcroft-Gault formula for Creatinine Clearance (CrCl), automatically determining whether to use Actual, Ideal, or Adjusted Body Weight:
    
    $$ CrCl = \frac{(140 - Age) \times Weight_{dosing}}{72 \times SCr} \times (0.85 \text{ if female}) $$

    *Once calculated, the AI pairs the quantitative result with FDA-indexed dosing tables to recommend precise renal modifications.*

## What I Learned
Building Nova Guard forced me to bridge the gap between deterministic clinical logic and probabilistic AI. I learned how to engineer highly structured prompts that force Large Language Models (LLMs) to output strict, predictable JSON schemas, turning raw medical text into actionable application state. 

I also deepened my understanding of modern web architecture, specifically how to decouple heavy, long-running AI inference tasks from the main user thread using asynchronous endpoints and React state updates. I learned that in clinical software, speed and UX are just as critical as the underlying data—if a tool isn't fast, clinicians simply won't use it.

## Challenges I Faced
**1. Latency vs. Accuracy in the Pharmacy Workflow:**
In a pharmacy setting, waiting 15 seconds for a database query is unacceptable. My biggest technical hurdle was optimizing the AI response times. I initially coupled the vision processing for lab reports directly with the database saving process, which caused slow, synchronous blocking. 
*   **The Fix:** I refactored the backend to make the AI endpoints completely stateless and asynchronous. The AI solely acts as an extraction engine, immediately streaming the data back to the frontend's local state, allowing the pharmacist to review multiple documents seamlessly before executing a final database sync.

**2. Taming the AI for Clinical Safety (Hallucination Prevention):**
AI models are notorious for "hallucinating." In pharmacy, a hallucination can be fatal. I could not allow the AI to invent dosage guidelines, guess at contraindications, or assume drug metabolic pathways.
*   **The Fix:** I developed a strict **Retrieval-Augmented Generation (RAG)** architecture grounded exclusively in verified clinical data. Before the LLM makes any decision, the backend first queries **RxNorm** to get the precise computational identifier for a drug. It then pulls the exact Section 12.3 (Pharmacokinetics) or Boxed Warnings directly from **OpenFDA** and **DailyMed** JSON labels. The system feeds the AI these verified, hard-coded textual parameters alongside the patient profile, restricting the LLM to act strictly as a *reasoning engine* (e.g., comparing the patient's CrCl against the FDA label's specific renal cutoffs) rather than an encyclopedic memory. This virtually eliminates hallucinations. 

Nova Guard is the culmination of my clinical background and my passion for engineering—proof that when clinicians design the technology they use, the standard of care elevates for everyone.

## What's Next for Nova Guard
Our immediate goal is to optimize and successfully **launch Nova Guard** into a live, pilot pharmacy environment to observe its impact on actual workflow efficiency and error reduction. Moving forward, we plan to expand the system's capabilities by:
*   **EHR Integration:** Building seamless, bi-directional HL7/FHIR integrations so Nova Guard can pull patient data directly from existing Electronic Health Records (EHRs) automatically.
*   **Predictive Procurement:** Leveraging our AI to not only suggest therapeutic substitutions during shortages, but to predict those shortages based on global API (Active Pharmaceutical Ingredient) supply chain data, prompting the pharmacy to order alternatives proactively.
*   **Continuous Learning Loop:** Implementing a feedback mechanism where clinical pharmacists can flag or refine the AI's counseling points, creating a localized, continuously improving clinical brain for the pharmacy team.
