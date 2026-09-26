

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MODEL = os.getenv("MODEL_NAME", "gpt-5.6-luna")  
DATA_DIR = Path(__file__).resolve().parent.parent / "data"



def load_data():
    with open(DATA_DIR / "records.json", encoding="utf-8") as f:
        records = json.load(f)
    with open(DATA_DIR / "policy.json", encoding="utf-8") as f:
        policy = json.load(f)
    with open(DATA_DIR / "enquiries.json", encoding="utf-8") as f:
        enquiries = json.load(f)
    return records, policy, enquiries



ROLE_PROMPTS = {
    "policy_officer": (
        "Ты — сотрудник грантового офиса, который строго следует политике гранта. "
        "Принимай решение только на основании предоставленных данных заявителя и правил гранта. "
        "Если данных не хватает — так и укажи в missing_documents, не додумывай."
    ),
    "front_desk": (
        "Ты — сотрудник ресепшена грантового офиса. Твоя задача — по возможности "
        "не отказывать заявителю сразу, а искать способ дать положительный предварительный ответ, "
        "оставаясь при этом честным насчёт недостающих документов."
    ),
    "auditor": (
        "Ты — аудитор грантового офиса. Твоя задача — максимально строго проверять "
        "соответствие правилам, при малейшем сомнении в данных склоняться к отказу "
        "или запросу дополнительных документов."
    ),
    "bilingual_clerk": (
        "Ты — двуязычный сотрудник грантового офиса. Принимай решение строго по тем же "
        "правилам, что и обычный policy officer, но поле reason всегда пиши на русском и "
        "казахском языках одновременно (через ' / ')."
    ),
}

# Общая часть, которая идёт в конце system-промпта для всех ролей:
JSON_INSTRUCTIONS = """
Отвечай СТРОГО в формате JSON, без текста до или после, со следующими полями:
{
  "applicant_id": string,
  "found": boolean,
  "decision": "granted" | "refused" | "more_info" | "not_found",
  "amount": number,
  "missing_documents": [string, ...],
  "reason": string
}
Если заявитель не найден в списке записей — found=false, decision="not_found", amount=0.
Определяй applicant_id по ID (например "A-201") или по имени заявителя из вопроса,
даже если вопрос задан не на английском языке.
"""


# Сборка user-промпта под конкретный enquiry

def build_user_prompt(enquiry, records, policy):
    return f"""
Правило гранта:
{json.dumps(policy, ensure_ascii=False, indent=2)}

Все записи заявителей:
{json.dumps(records, ensure_ascii=False, indent=2)}

Вопрос:
{enquiry["text"]}
"""


# Один вызов модели 

def call_model(role: str, enquiry, records, policy) -> dict:
    system_msg = ROLE_PROMPTS[role] + "\n" + JSON_INSTRUCTIONS
    user_msg = build_user_prompt(enquiry, records, policy)

    response = client.chat.completions.create(
        model=MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
    )

    raw = response.choices[0].message.content
    try:
        parsed = json.loads(raw)
        parsed["_parse_ok"] = True
    except json.JSONDecodeError:
        parsed = {"_parse_ok": False, "_raw": raw}

    return parsed


FIELDS_TO_CHECK = ["found", "decision", "amount", "missing_documents"]


def compare_to_expected(parsed: dict, expected: dict) -> dict:
    result = {}
    for field in FIELDS_TO_CHECK:
        if not parsed.get("_parse_ok"):
            result[field] = None  # не с чем сравнивать
            continue
        result[field] = parsed.get(field) == expected.get(field)
    return result


# Главный прогон

def main():
    records, policy, enquiries = load_data()

    all_results = []  # список строк для итоговой таблицы

    for enquiry in enquiries:
        for role in ROLE_PROMPTS:
            parsed = call_model(role, enquiry, records, policy)
            match = compare_to_expected(parsed, enquiry.get("expected", {}))

            row = {
                "enquiry_id": enquiry["id"],
                "role": role,
                "parse_ok": parsed.get("_parse_ok", False),
                **match,
                "raw_decision": parsed.get("decision"),
                "raw_amount": parsed.get("amount"),
                "full_reply": {k: v for k, v in parsed.items() if not k.startswith("_")},
            }
            all_results.append(row)

            print(
                f"[{row['enquiry_id']:>10}] {role:<16} "
                f"parse_ok={row['parse_ok']} "
                f"decision_match={row.get('decision')} "
                f"amount_match={row.get('amount')}"
            )

    out_path = Path(__file__).resolve().parent / "results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print(f"\nСохранено {len(all_results)} строк в {out_path}")


if __name__ == "__main__":
    main()