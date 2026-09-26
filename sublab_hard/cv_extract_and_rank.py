

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MODEL = os.getenv("MODEL_NAME", "gpt-5.6-luna")
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

STORIES_DIR = DATA_DIR / "candidates"

EXTRACT_SYSTEM_PROMPT = """
Ты извлекаешь структурированные данные CV из неформального текста заявки.
Строго следуй правилам:
1. Если факт явно не указан в тексте — ставь null. НЕ угадывай и не додумывай
   (например, никогда не оценивай отсутствующий GPA по названию вуза или впечатлению от текста).
2. Если GPA указан не по 4-балльной шкале — сконвертируй в gpa_4_scale
   и обязательно укажи исходную шкалу в gpa_original_scale. Если GPA в тексте
   вообще не упомянут — gpa_4_scale = null.
3. published_papers_count считай ТОЛЬКО статьи, про которые явно сказано
   "published"/"accepted" (или аналог на другом языке). Статьи со статусом
   "in preparation"/"submitted"/"under review"/"planned"/"in press" НЕ считаются
   опубликованными — перечисли их отдельно в unpublished_papers, не в счётчике.
4. experience_months_total считай в месяцах, а не в количестве мест работы.
   Пересекающиеся по времени периоды считай один раз (не суммируй дважды).
   Период без указанных дат не может быть посчитан в месяцах — перечисли его
   отдельно в unpublished_experience_periods и не включай в сумму месяцев.
5. Если в тексте есть противоречивые данные по одному и тому же полю —
   ставь это поле в null и опиши противоречие в ambiguities. Не выбирай
   одно из значений сам и не усредняй.
Текст заявки может быть не на английском языке (например, на казахском) —
это не повод пропускать факты.

Отвечай СТРОГО JSON без текста до/после:
{
  "candidate_id": string,
  "full_name": string | null,
  "degree": string | null,
  "graduation_year": number | null,
  "gpa_4_scale": number | null,
  "gpa_original_scale": string | null,
  "languages": [string, ...],
  "published_papers_count": number,
  "unpublished_papers": [string, ...],
  "experience_months_total": number | null,
  "unpublished_experience_periods": [string, ...],
  "ambiguities": [string, ...]
}
"""

def build_rank_system_prompt(rubric: dict) -> str:
    criteria_desc = "\n".join(
        f"- {c['id']} ({c['label']}): 5 = {c['what_5_means']}; 0 = {c['what_0_means']}"
        for c in rubric["criteria"]
    )
    ids = [c["id"] for c in rubric["criteria"]]
    return f"""
Оцени кандидата по каждому критерию рубрики от 0 до 5 (числа, дробные допустимы).
Критерии:
{criteria_desc}

Не считай итоговую сумму и не применяй веса — только сами баллы.
Отвечай СТРОГО JSON без текста до/после, с ключами ровно {ids}:
{{"scores": {{"{ids[0]}": number, "{ids[1]}": number, "{ids[2]}": number}}}}
"""



def load_stories():
    stories = {}
    for path in sorted(STORIES_DIR.glob("*.md")):
        stories[path.stem] = path.read_text(encoding="utf-8")

    if not stories:
        for path in sorted(STORIES_DIR.glob("*.txt")):
            stories[path.stem] = path.read_text(encoding="utf-8")
    return stories


def load_rubric():
    with open(DATA_DIR / "candidate_rubric.json", encoding="utf-8") as f:
        return json.load(f)


# Извлечение CV-полей из одной истории 

def extract_cv(candidate_id: str, story_text: str) -> dict:
    response = client.chat.completions.create(
        model=MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": EXTRACT_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"candidate_id: {candidate_id}\n\nТекст заявки:\n{story_text}",
            },
        ],
    )
    raw = response.choices[0].message.content
    try:
        parsed = json.loads(raw)
        parsed["_parse_ok"] = True
    except json.JSONDecodeError:
        parsed = {"_parse_ok": False, "_raw": raw, "candidate_id": candidate_id}
    return parsed



def score_candidate(cv: dict, rubric: dict) -> dict:
    response = client.chat.completions.create(
        model=MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": build_rank_system_prompt(rubric)},
            {
                "role": "user",
                "content": f"CV кандидата:\n{json.dumps(cv, ensure_ascii=False, indent=2)}",
            },
        ],
    )
    raw = response.choices[0].message.content
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"scores": {}}


#  Взвешенная сумма 

def compute_weighted_total(scores: dict, rubric: dict) -> float:
    total = 0.0
    for criterion in rubric["criteria"]:
        total += scores.get(criterion["id"], 0) * criterion["weight"]
    return round(total, 2)


#  Прозаический вердикт модели

def ask_prose_winner(all_cvs: list[dict]) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": "Вот список кандидатов на грант:\n"
                f"{json.dumps(all_cvs, ensure_ascii=False, indent=2)}\n\n"
                "Кто из них должен победить и почему? Ответь свободным текстом.",
            }
        ],
    )
    return response.choices[0].message.content


# Главный прогон

def main():
    stories = load_stories()
    rubric = load_rubric()

    all_cvs = []
    for candidate_id, text in stories.items():
        cv = extract_cv(candidate_id, text)
        all_cvs.append(cv)
        print(f"[{candidate_id}] parse_ok={cv.get('_parse_ok')} "
              f"published={cv.get('published_papers_count')} "
              f"gpa_4={cv.get('gpa_4_scale')}")

    ranking = []
    for cv in all_cvs:
        result = score_candidate(cv, rubric)
        total = compute_weighted_total(result.get("scores", {}), rubric)
        ranking.append({
            "candidate_id": cv.get("candidate_id"),
            "scores": result.get("scores", {}),
            "weighted_total": total,
        })

    ranking.sort(key=lambda r: r["weighted_total"], reverse=True)

    print("\n=== Ранжирование (посчитано кодом) ===")
    for r in ranking:
        print(f"{r['candidate_id']}: {r['weighted_total']:.2f} — {r['scores']}")

    winner_by_code = ranking[0]["candidate_id"] if ranking else None
    print(f"\nПобедитель по коду: {winner_by_code}")

    prose_verdict = ask_prose_winner(all_cvs)
    print(f"\n=== Прозаический вердикт модели ===\n{prose_verdict}")

    out_path = Path(__file__).resolve().parent / "results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "cvs": all_cvs,
                "ranking": ranking,
                "winner_by_code": winner_by_code,
                "prose_verdict": prose_verdict,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(f"\nСохранено в {out_path}")


if __name__ == "__main__":
    main()