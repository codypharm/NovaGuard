# 🎬 Nova Guard 3-Minute Demo Guide

This guide is designed to help you record the perfect 3-minute screen capture and read the accompanying voice-over script later. Total target time is ~160-180 seconds.

## ⏱️ Timeline Overview

| Section | Visual Actions (Screen Recording) | Timestamp |
| :--- | :--- | :--- |
| **1. Intro & Landing Page** | Scroll down to show animations, click "Launch Workbench". | `0:00 - 0:20` |
| **2. Patient Intake** | Search/Select a patient. Quickly highlight history. | `0:20 - 0:40` |
| **3. Nova Vision Labs** | Upload a CMP lab image. Show AI extracting eGFR. | `0:40 - 1:10` |
| **4. Safety Matrix** | Type a risky prescription. Wait for streaming flags. | `1:10 - 2:00` |
| **5. Drug Ops Calculator** | Switch to Drug Ops tab. Enter a Cockcroft-Gault math calculation. | `2:00 - 2:40` |
| **6. Report Generation** | Click to download the final Clinical PDF Report. | `2:40 - 3:00` |

---

## 📽️ Step-by-Step Recording & Voice-Over Script

### Part 1: The First Impression (20 seconds)

**What to do on screen:**
1. Start recording on the Landing Page (`/`). 
2. Slowly scroll down. Pause briefly when the `framer-motion` "Workflow Animation" loops so the viewer grasps the step-by-step nature.
3. Scroll back up and click the bold "**Launch Workbench**" button.

> **Voice-over Script:**
> *"Welcome to Nova Guard, a state-of-the-art Clinical Intelligence Engine powered natively by Amazon Nova. Designed to eliminate pharmacy dosing errors and cognitive overload, Nova Guard orchestrates an autonomous safety workflow from chaotic intakes to actionable clinician verdicts."*

### Part 2: Multimodal Patient Intake (20 seconds)

**What to do on screen:**
1. Now in the Workbench, click "Load Profile" on a sample patient (e.g., John Doe).
2. Briefly hover your mouse over the patient's "Allergies" or "Current Medications" to establish they have a rich clinical history.
3. Click into the **Lab Results** tab of the patient form.

> **Voice-over Script:**
> *"Behind the scenes, Nova Guard compiles a unified patient profile, capturing everything from current medications to genetic markers. Plus, all Private Health Information is entirely stripped out and de-identified before hitting any cloud LLM, ensuring strict HIPAA compliance."*

### Part 3: Amazon Nova Vision Parsing (30 seconds)

**What to do on screen:**
1. Stay in the Labs section. Drop in a fake printed CMP lab report image (the image file).
2. Click "Process Lab Report".
3. Wait and show the extracted JSON data populating automatically (highlighting eGFR or Creatinine).
4. Save the patient profile.

> **Voice-over Script:**
> *"Nova Guard actively utilizes Amazon Nova Vision. Here, a pharmacist uploads a photograph of a chaotic metabolic lab panel. Within seconds, the AI extracts structured biomarkers like eGFR and liver enzymes, instantly calculating renal function thresholds for future interventions."*

### Part 4: The Ultimate Triages & Generative Verdict (50 seconds)

**What to do on screen:**
1. Open up the Clinical Chat terminal in the center.
2. Type or dictate a highly risky scenario. For example: *"Patient needs pain relief. Prescribe Codeine 30mg Q6H PRN."* (Make sure the patient has a CYP2D6 Poor Metabolizer genetic profile set up in the DB).
3. Hit Enter. Let the screen record as LangGraph evaluates. 
4. IMPORTANT: Make sure to clearly capture the unfolding `<clinical_analysis>` Chain-of-Thought streaming in the UI, and the final animated **red Pharmacogenomics Flag**.

> **Voice-over Script:**
> *"The true intelligence executes in the chat terminal. We ask the system to prescribe Codeine. In real-time, the LangGraph orchestrator intercepts this intent. It cross-references OpenFDA, parses NIH RxNorms, and checks the patient's CYP2D6 genetic marker. The deterministic safety matrix triggers a severe Pharmacogenomics Alert, warning of poor metabolism. The Amazon Nova reasoning model streams a transparent sequence of thought, ending with a clinical blocked verdict—protecting both patient and clinician."*

### Part 5: Polypharmacy & Drug Operations (40 seconds)

**What to do on screen:**
1. Start another query: *"They also stopped taking Lisinopril due to a cough last year, but a doctor just prescribed Ramipril."* Let the system generate the **Longitudinal Flag** showing cross-class reactivity.
2. Click the top nav bar to switch over to the **Drug operations module**.
3. Quickly fill out the Dose Adjustment fields (weight, age, eGFR) and hit "Calculate Results" to show the automated Renal Math engine.

> **Voice-over Script:**
> *"The logic runs deeper than immediate queries. A 'time travel' longitudinal check detects cross-reactivity based on historically discontinued drugs. Beyond chat, the standalone Drug Operations Module automates treacherous Cockcroft-Gault dosing mathematics—eliminating manual error entirely."*

### Part 6: Reporting & Outro (20 seconds)

**What to do on screen:**
1. Switch back to the chat timeline.
2. Tell the system to *"Generate my clinical report"* or click the button. 
3. The PDF downloads. Open it briefly on screen to show the structured summary.
4. End recording.

> **Voice-over Script:**
> *"When the consultation is finished, a complete, legally robust PDF clinical report is instantly generated. From multimodal intakes to high-stakes generative triages, Nova Guard isn't just a chatbot; it is precision clinical intelligence without compromise."*

---

## 🎬 Top Recording Tips for a Flawless Demo

- **Pacing is everything:** Move your cursor deliberately. Don't rush clicks. If the LLM takes 5 seconds to stream the text, don't move the mouse; let the viewer's eyes follow the text.
- **Screen Resolution:** Record in 1080p (or 16:9 ratio) standard so text isn't blurry. A `Command + Shift + 5` (on Mac) recording a specific window is best.
- **Hide Clutter:** Close extra browser extensions, make the browser full screen so OS docks/notifications don't appear.
- **Use Mock Data Pre-loads:** Pre-load the Postgres database with the exact PGx marker and allergies needed so you don't have to awkwardly type them in during the demo.
