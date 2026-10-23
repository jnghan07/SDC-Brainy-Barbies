
"""SDC 2026 CV Extraction - RunPod Serverless Handler.

Accepts CV text and uses the existing RunPod vLLM endpoint
to extract structured candidate information.
"""

import json
import os

import runpod
from openai import OpenAI


MODEL_NAME = "Qwen/Qwen3-VL-4B-Instruct"

FIELDS = [
    "full_name",
    "email",
    "phone",
    "location",
    "target_job_title",
    "industry",
    "professional_summary",
    "education",
    "experience",
    "skills",
    "projects",
    "certifications",
]


def handler(job: dict) -> dict:
    job_input = job.get("input", {})
    cv_text = job_input.get("cv_text", "")

    if not isinstance(cv_text, str) or not cv_text.strip():
        return {
            "error": "Missing CV text. Provide it using input.cv_text."
        }

    api_key = os.getenv("RUNPOD_API_KEY")
    endpoint_id = os.getenv("RUNPOD_ENDPOINT_ID")

    if not api_key or not endpoint_id:
        return {
            "error": "RunPod API credentials are not configured."
        }

    client = OpenAI(
        api_key=api_key,
        base_url=(
            f"https://api.runpod.ai/v2/{endpoint_id}/openai/v1"
        ),
        timeout=240.0,
    )

    prompt = f"""
Extract information from the CV below.

Return one valid JSON object with exactly these fields:
{json.dumps(FIELDS)}

Use strings for scalar fields and arrays for education,
experience, skills, projects, and certifications.
Use empty strings or empty arrays for missing information.
Do not invent facts.

CV:
<cv_text>
{cv_text}
</cv_text>
"""

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a CV information extraction system. "
                        "Return valid JSON only."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=1800,
        )

        content = response.choices[0].message.content or ""
        data = json.loads(content)

        if not isinstance(data, dict):
            return {"error": "Invalid model response format."}

        result = {}

        for field in FIELDS:
            value = data.get(field)

            if field in {
                "education",
                "experience",
                "skills",
                "projects",
                "certifications",
            }:
                result[field] = value if isinstance(value, list) else []
            else:
                result[field] = value if isinstance(value, str) else ""

        return {"result": result}

    except json.JSONDecodeError:
        return {"error": "Model returned invalid JSON."}
    except Exception:
        return {"error": "CV extraction failed. Please try again."}


runpod.serverless.start({"handler": handler})
