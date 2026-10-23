# Project Name

> A one-sentence description of what your project does and who it is for.

---

## Team Information

| Field                  | Details                                     |
| ---------------------- | ------------------------------------------- |
| **Team Name**          | Brainy Barbies                              |
| **Team Domain**        | Domain 1                                    |
| **SDG Track (1–17)**   | SDG 8 — Decent Work and Economic Growth     |
| **Team Leader**        | Law Jing Xuan                               |
| **University**         | Asia Pacific University                     |
| **Number of Members**  | 5                                           |

## Links

| Resource          | Link                                           |
| ----------------- | ---------------------------------------------- |
| GitHub Repository | https://github.com/jnghan07/SDC-Brainy-Barbies |
| Replit Project    | https://replit.com/@your-username/your-project |
| Live Demo         | https://your-project.replit.app                |
| RunPod Endpoint   | https://api.runpod.ai/v2/18vyxb87eihqej        |
| Slide Deck        | https://example.com/slides                     |
| Demo Video        | https://example.com/demo-video                 |

---

## Overview

### Problem

Describe the real-world problem you are solving in 2–4 sentences. Who is affected, and why does it matter?

Due to the rapid development of AI, recent graduates are unable to keep up with on-demand skills as there is a gap in what they learn in universities compared with what they can actually apply in workplace settings, resulting in reviews made by MOHE to keep pace offered courses with AI and industry needs (Ministry of Higher Education Malaysia (MOHE), 2026). Therefore, it is essential to raise awareness among fresh graduates on current and potential future job market trends for better decision-making in terms of their learning priorities and career selection. This way, they can find space and survive in the job market and thrive throughout their careers as our solution tackles this issue. 

### Solution

Explain how your project uses AI to solve the problem and what makes it valuable.

We solved it by tracking the current job market and displaying on-demand jobs. It also predicts future market trends, providing fresh graduates with a heads-up about job displacement.  

Our proposed application first requires a CV upload or a manual entry of skills the candidate owns. After that, the application extracts skills - explicitly listed in the CV and suggests relevant skills the candidate may have but does not find evidence of it being demonstrated - using an AI model that we trained with public database data. It then recommends careers the candidate can pursue and personalize skills the candidate can learn based on the data obtained from CV extraction. The skills are then supported with SDG mappings to show how candidates' upskilling can contribute towards the goals.  

The frontend portion was done using Replit Core and Gemini API key was used to call backend services. 

### Key Features

- **Feature 1** — User can upload their CV to see the details about their skills, whether they are still the trends or not.
- **Feature 2** — Short description.
- **Feature 3** — Short description.

### Tech Stack

| Layer         | Technology                   |
| ------------- | ---------------------------- |
| Frontend      | e.g. HTML, React             |
| Backend       | e.g. Python, Flask / FastAPI |
| Database      | e.g. PostgreSQL, SQLite      |
| AI / Compute  | Replit, Gemini, Claude       |
| Hosting / Dev | Replit                       |

---

## Project Structure

```
.
├── docs/                    # Screenshots, diagrams
├── runpod/
│   └── handler.py           # RunPod serverless handler (GPU workload)
├── src/
│   ├── main.py              # Application entry point
│   └── utils.py             # Helper functions
├── submission/              # Required submission documents
│   ├── SDC2026_TeamName_Preliminary.pdf      # Preliminary submission
│   ├── SDC2026_TeamName_TechDeclaration.pdf  # Technology declaration
│   ├── SDC2026_TeamName_Replit_POU.pdf       # Replit proof of use
│   └── SDC2026_TeamName_Runpod_POU.pdf       # RunPod proof of use
├── tests/
│   └── test_utils.py        # Unit tests
├── .env.example             # Example environment variables
├── .gitignore
├── .replit                  # Replit run configuration
├── LICENSE
├── requirements.txt         # Python dependencies
└── README.md
```

### Architecture

```
User ──► Replit (App / API) ──► RunPod Endpoint (GPU model)
                │
                └──► Response returned to user
```

---

## How to Run

### Option 1 — Run on Replit (Recommended)

1. Open the [Replit Project](https://replit.com/@your-username/your-project), or import this repository via **Create Repl → Import from GitHub**.
2. Open the **Secrets** tab (🔒) and add the variables listed in `.env.example`:
   - `RUNPOD_API_KEY`
   - `RUNPOD_ENDPOINT_ID`
3. Click **Run**. Replit uses the `.replit` file to start `python src/main.py`.

### Option 2 — Run Locally

```bash
# 1. Clone the repository
git clone https://github.com/your-username/your-project.git
cd your-project

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env            # then fill in your values

# 5. Run the app
python src/main.py
```

### Run Tests

```bash
python -m unittest discover tests
```

---

## How We Use Replit *(Required)*

Describe how your team used Replit. For example:

- **Development:** Collaborative coding in a shared Repl using Multiplayer.
- **Hosting:** The app is deployed with Replit Deployments at the Live Demo link above.
- **Secrets:** API keys are stored in Replit Secrets, never in the code.

📄 Proof of use: [`submission/SDC2026_TeamName_Replit_POU.pdf`](submission/SDC2026_TeamName_Replit_POU.pdf)

## How We Use RunPod *(Required)*
- **Workload:**
  Our project uses the Qwen3-VL-4B-Instruct vision-language model for CV information extraction. The model processes CV content and extracts structured candidate information, including contact details, education, work experience, skills, projects, and certifications.
- **Setup:** `runpod/handler.py` is deployed as a **RunPod Serverless Endpoint**.
- **Integration:** The Replit app sends requests to the endpoint using `RUNPOD_API_KEY` and `RUNPOD_ENDPOINT_ID` environment variables. These credentials are stored as environment secrets and are not committed to the repository. The application uses the endpoint's OpenAI-compatible Chat Completions API for CV extraction.

Example request:

```bash
curl -X POST https://api.runpod.ai/v2/18vyxb87eihqej/runsync \
    -H 'Content-Type: application/json' \
    -H 'Authorization: Bearer YOUR_API_KEY' \
    -d '{"input":{"prompt":"Extract CV information into JSON. Return these fields: full_name, email, phone, location, target_job_title, industry, professional_summary, education, experience, skills, projects, certifications."}}'
```

📄 Proof of use: [`submission/SDC2026_TeamName_Runpod_POU.pdf`](submission/SDC2026_TeamName_Runpod_POU.pdf)

---

## Challenges & Learnings

- What challenges did you face, and how did you overcome them?
- What did your team learn?

## Future Improvements

- [ ] Improvement 1
- [ ] Improvement 2

## Team

| Name        | Role                | GitHub                                   |
| ----------- | ------------------- | ---------------------------------------- |
| Member Name | Team Lead / Backend | [@username](https://github.com/username) |
| Law Jing Xuan | Frontend         | [@JingXuannn123](https://github.com/JingXuannn123) |
| Stephy Tsen Yung Yi | AI / RunPod | [@stapi0904](https://github.com/stapi0904) |

---

## Submission Checklist

- [ ] Team name, domain (Domain 1 / Domain 2) and SDG track filled in
- [ ] Slide deck link added
- [ ] Demo video link added
- [ ] Replit used, with proof of use in `submission/`
- [ ] RunPod used, with proof of use in `submission/`
- [ ] Preliminary submission completed (`SDC2026_TeamName_Preliminary.pdf`)
- [ ] Technology declaration completed (`SDC2026_TeamName_TechDeclaration.pdf`)
- [ ] Submission files renamed with your team name (replace `TeamName`)
- [ ] "How to Run" steps verified
- [ ] No API keys or secrets committed to the repository

## License

This project is licensed under the [Apache License 2.0](LICENSE).
