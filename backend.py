import os
import json
import io
import contextlib
import pandas as pd
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

# =========================
# GROQ SETUP
# =========================

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise RuntimeError(
        "GROQ_API_KEY not found. Put it inside your .env file."
    )

client = Groq(api_key=api_key)

MODEL = "openai/gpt-oss-20b"


# =========================
# ANALYZE DATA
# =========================

def analyze(tables, question):

    data_description = ""

    for name, df in tables.items():

        data_description += f"\n\nTABLE: {name}\n"
        data_description += f"Columns: {list(df.columns)}\n"
        data_description += f"Rows: {len(df)}\n"

        # Detect missing values
        missing = df.isnull().sum().to_dict()
        data_description += f"Missing values: {missing}\n"

        # Show sample data
        data_description += df.head(20).to_string(index=False)

    # =========================
    # AI PROMPT
    # =========================

    prompt = f"""
You are a proof-carrying AI data analyst.

UPLOADED DATA:

{data_description}

USER QUESTION:
{question}

YOUR JOB:

1. Understand the user's natural-language question.
2. Use ONLY the uploaded data.
3. Do NOT invent or assume values.
4. Detect missing information.
5. If required information is missing, return can_determine=false.
6. If the question is ambiguous, return can_determine=false.
7. Generate Python pandas code ONLY if the answer can be determined.
8. The Python code MUST store the final result in a variable called `answer`.
9. Every numerical answer must be reproducible by running the generated code.
10. DO NOT use import statements.
11. pandas is already available as `pd`.
12. If only one table exists, use `df`.
13. If multiple tables exist, use tables["filename"].

CALCULATION RULES:

- "total" → sum()
- "average" / "mean" → mean()
- "highest" / "maximum" → max()
- "lowest" / "minimum" → min()
- "count" → count rows

IMPORTANT:

Do NOT use max() when the user asks for a total.

Do NOT use sum() when the user asks for the highest value.

Do NOT guess missing values.

Return ONLY valid JSON.

ANSWERABLE:

{{
    "can_determine": true,
    "code": "answer = ...",
    "reason": "",
    "explanation": "Short explanation."
}}

NOT ANSWERABLE:

{{
    "can_determine": false,
    "code": "",
    "reason": "Explain why the answer cannot be determined.",
    "explanation": ""
}}
"""

    try:

        # =========================
        # CALL GROQ
        # =========================

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0
        )

        text = response.choices[0].message.content.strip()

        # Remove markdown fences
        if text.startswith("```"):
            text = text.replace("```json", "")
            text = text.replace("```", "")
            text = text.strip()

        # =========================
        # READ AI RESPONSE
        # =========================

        result = json.loads(text)

        # =========================
        # CANNOT DETERMINE
        # =========================

        if not result.get("can_determine", False):

            reason = result.get(
                "reason",
                "Cannot determine from the available data."
            )

            return {
                "can_determine": False,
                "answer": "",
                "code": "",
                "evidence": reason,
                "reason": reason
            }

        # =========================
        # GET PYTHON CODE
        # =========================

        generated_code = result.get("code", "").strip()

        generated_code = generated_code.replace(
            "```python", ""
        )

        generated_code = generated_code.replace(
            "```", ""
        ).strip()

        if not generated_code:

            return {
                "can_determine": False,
                "answer": "",
                "code": "",
                "evidence": "",
                "reason": "AI did not generate Python code."
            }

        # =========================
        # BLOCK UNSAFE CODE
        # =========================

        forbidden = [
            "import ",
            "open(",
            "eval(",
            "exec(",
            "subprocess",
            "os.",
            "sys."
        ]

        for item in forbidden:

            if item in generated_code:

                return {
                    "can_determine": False,
                    "answer": "",
                    "code": generated_code,
                    "evidence": "",
                    "reason": "Generated code contains a prohibited operation."
                }

        # =========================
        # PREPARE PYTHON
        # =========================

        local_vars = {
            "pd": pd,
            "tables": tables
        }

        # If only one file was uploaded
        if len(tables) == 1:

            local_vars["df"] = next(
                iter(tables.values())
            )

        output = io.StringIO()

        # =========================
        # RUN GENERATED CODE
        # =========================

        with contextlib.redirect_stdout(output):

            exec(
                generated_code,
                {
                    "__builtins__": {
                        "len": len,
                        "str": str,
                        "float": float,
                        "int": int,
                        "sum": sum,
                        "min": min,
                        "max": max,
                        "round": round
                    }
                },
                local_vars
            )

        # =========================
        # GET ANSWER
        # =========================

        answer = local_vars.get("answer")

        if answer is None:
            answer = output.getvalue().strip()

        if isinstance(answer, pd.DataFrame):

            answer = answer.to_string(index=False)

        elif isinstance(answer, pd.Series):

            answer = answer.to_string()

        else:

            answer = str(answer)

        # =========================
        # EVIDENCE
        # =========================

        evidence = (
            "The answer was calculated by executing "
            "the generated Python code on the uploaded data.\n\n"
            "Explanation: "
            + result.get("explanation", "")
        )

        # =========================
        # FINAL RESULT
        # =========================

        return {
            "can_determine": True,
            "answer": answer,
            "code": generated_code,
            "evidence": evidence,
            "reason": ""
        }

    except Exception as e:

        return {
            "can_determine": False,
            "answer": "",
            "code": "",
            "evidence": "",
            "reason": "Backend error: " + str(e)
        }