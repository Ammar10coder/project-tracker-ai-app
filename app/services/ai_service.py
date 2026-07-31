import json
import logging
from typing import List, Dict, Any
from pydantic import BaseModel, Field

from app import config
from app.ai.prompt import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class TaskItem(BaseModel):
    task_title: str = Field(description="Short, concise name of the task")
    status: str = Field(description="Status of the task: 'Completed' or 'In Progress'")
    progress_percentage: int = Field(description="100 for Completed tasks, 50 for In Progress tasks")


class MessageAnalysis(BaseModel):
    greetings: List[str] = Field(default_factory=list)
    completed: List[str] = Field(default_factory=list)
    in_progress: List[str] = Field(default_factory=list)
    tasks: List[TaskItem] = Field(default_factory=list)


def analyze_message(text: str, project_name: str = "", deadline: str = "", yesterday_report: str = "") -> Dict[str, Any]:
    """
    Analyzes chat update text and extracts structured tasks.
    Fallback pipeline: Gemini -> Groq -> OpenRouter -> Keyword Rule Engine.
    """
    if not text or not text.strip():
        return {"greetings": [], "completed": [], "in_progress": [], "tasks": []}

    cfg = config.load()
    gemini_key = cfg.get("GEMINI_API_KEY")
    groq_key = cfg.get("GROQ_API_KEY")
    openrouter_key = cfg.get("OPENROUTER_API_KEY")

    prompt = f"""
You are an AI Project Manager. Analyze the following team chat update message.

Instructions:
1. Separate general greetings (e.g., "Good morning team!") from technical updates.
2. Extract distinct work items into short, professional task titles (DO NOT keep full chat sentences).
3. Assign status: 'Completed' (100% progress) or 'In Progress' (50% progress).

Message to analyze:
"{text}"
"""

    # TIER 1: GOOGLE GEMINI API
    if gemini_key:
        try:
            from google import genai
            from google.genai import types

            gemini_client = genai.Client(api_key=gemini_key)
            response = gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=MessageAnalysis,
                    temperature=0.1,
                ),
            )

            cleaned_text = response.text.strip()
            if cleaned_text.startswith("```"):
                cleaned_text = cleaned_text.strip("`")
                if cleaned_text.startswith("json"):
                    cleaned_text = cleaned_text[4:].strip()

            parsed = json.loads(cleaned_text)

            completed_list = parsed.get("completed", [])
            in_progress_list = parsed.get("in_progress", [])
            tasks_list = parsed.get("tasks", [])

            if not tasks_list:
                for item in completed_list:
                    tasks_list.append({"task_title": item, "status": "Completed", "progress_percentage": 100})
                for item in in_progress_list:
                    tasks_list.append({"task_title": item, "status": "In Progress", "progress_percentage": 50})

            return {
                "greetings": parsed.get("greetings", []),
                "completed": [t["task_title"] if isinstance(t, dict) else t for t in completed_list],
                "in_progress": [t["task_title"] if isinstance(t, dict) else t for t in in_progress_list],
                "tasks": tasks_list
            }
        except Exception as gemini_e:
            logger.warning(f"Gemini API failed: {gemini_e}. Trying Groq...")
    else:
        logger.info("Gemini API key not set, skipping to Groq.")

    # TIER 2: GROQ API FALLBACK
    if groq_key:
        try:
            from groq import Groq
            groq_client = Groq(api_key=groq_key)

            groq_prompt = f"""
            You are an AI Project Manager. Extract tasks from this chat update.
            Return ONLY a valid JSON object with key "tasks" containing a list of objects with:
            - "task_title": concise task name
            - "status": "Completed" or "In Progress"
            - "progress_percentage": 100 for completed, 50 for in progress

            Chat text: "{text}"
            """

            chat_completion = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": groq_prompt}],
                model="llama-3.1-8b-instant",
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            groq_response = chat_completion.choices[0].message.content
            parsed = json.loads(groq_response)
            extracted_tasks = parsed.get("tasks", [])

            completed = [t["task_title"] for t in extracted_tasks if t.get("status") == "Completed"]
            in_progress = [t["task_title"] for t in extracted_tasks if t.get("status") == "In Progress"]

            return {
                "greetings": [],
                "completed": completed,
                "in_progress": in_progress,
                "tasks": extracted_tasks
            }
        except Exception as groq_e:
            logger.warning(f"Groq API failed: {groq_e}. Trying OpenRouter...")
    else:
        logger.info("Groq API key not set, skipping to OpenRouter.")

    # TIER 3: OPENROUTER API FALLBACK
    if openrouter_key:
        try:
            from openai import OpenAI
            openrouter_client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=openrouter_key)

            openrouter_prompt = f"""
            Analyze the following employee update and extract the tasks.
            Return ONLY a valid JSON object with the following structure, with no markdown formatting or extra text:
            {{
                "tasks": [
                    {{
                        "task_title": "Brief, concise description of the task",
                        "status": "In Progress" or "Completed",
                        "progress_percentage": <integer between 0 and 100>
                    }}
                ]
            }}

            Employee Update: "{text}"
            """

            response = openrouter_client.chat.completions.create(
                model="meta-llama/llama-3.1-8b-instruct:free",
                messages=[
                    {"role": "system", "content": "You are a precise data extraction API. Only output raw JSON."},
                    {"role": "user", "content": openrouter_prompt}
                ],
                temperature=0.1
            )

            raw_output = response.choices[0].message.content.strip()
            if raw_output.startswith("```json"):
                raw_output = raw_output[7:-3]
            elif raw_output.startswith("```"):
                raw_output = raw_output[3:-3]

            parsed = json.loads(raw_output)
            extracted_tasks = parsed.get("tasks", [])

            completed = [t["task_title"] for t in extracted_tasks if t.get("status") == "Completed" or t.get("progress_percentage") == 100]
            in_progress = [t["task_title"] for t in extracted_tasks if t.get("status") != "Completed" and t.get("progress_percentage", 0) < 100]

            return {
                "greetings": [],
                "completed": completed,
                "in_progress": in_progress,
                "tasks": extracted_tasks
            }
        except Exception as openrouter_e:
            logger.error(f"OpenRouter API failed: {openrouter_e}. Falling back to rule-based parser.")
    else:
        logger.info("OpenRouter API key not set, skipping to rule-based parser.")

    # TIER 4: RULE-BASED KEYWORD FALLBACK
    greetings, completed, in_progress, tasks = [], [], [], []
    greeting_keywords = ["good morning", "good evening", "good afternoon", "sir", "hello", "hi", "hey"]
    completed_keywords = ["completed", "done", "finished", "integrated", "implemented", "fixed", "pushed"]
    progress_keywords = ["working on", "in progress", "doing", "optimizing", "developing", "building", "uploading"]

    for line in text.splitlines():
        line_str = line.strip()
        if not line_str:
            continue
        line_lower = line_str.lower()

        if any(kw in line_lower for kw in greeting_keywords) and len(line_str.split()) <= 5:
            greetings.append(line_str)
        elif any(kw in line_lower for kw in completed_keywords):
            title = line_str.replace('"', '').strip()
            completed.append(title)
            tasks.append({"task_title": title, "status": "Completed", "progress_percentage": 100})
        elif any(kw in line_lower for kw in progress_keywords):
            title = line_str.replace('"', '').strip()
            in_progress.append(title)
            tasks.append({"task_title": title, "status": "In Progress", "progress_percentage": 50})

    if not tasks and len(text.split()) > 3:
        tasks.append({"task_title": text[:50] + "...", "status": "In Progress", "progress_percentage": 50})
        in_progress.append(text[:50] + "...")

    return {"greetings": greetings, "completed": completed, "in_progress": in_progress, "tasks": tasks}


def analyze_project(project_name: str, deadline: str, yesterday_report: str, today_message: str) -> Dict[str, Any]:
    return analyze_message(text=today_message, project_name=project_name, deadline=deadline, yesterday_report=yesterday_report)
