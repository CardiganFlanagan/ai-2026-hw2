

import json
import os
from pathlib import Path

import tiktoken
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MODEL = os.getenv("MODEL_NAME", "gpt-5.6-luna")
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

SYSTEM_PROMPT = (
    "Ты — ассистент грантового офиса, который ведёт диалог с заявителем "
    "и запоминает важные факты по ходу разговора."
)



def load_script():
    with open(DATA_DIR / "chat_script.json", encoding="utf-8") as f:
        return json.load(f)


def load_memory_schema():
    with open(DATA_DIR / "memory_state.schema.json", encoding="utf-8") as f:
        return json.load(f)


def count_tokens(messages, model=MODEL):
    try:
        enc = tiktoken.encoding_for_model(model)
    except KeyError:
        enc = tiktoken.get_encoding("cl100k_base")
    total = 0
    for m in messages:
        total += len(enc.encode(m["content"]))
    return total


# Валидация JSON-состояния по схеме

def validate_memory_state(state: dict, schema: dict) -> bool:
    try:
        import jsonschema
        jsonschema.validate(instance=state, schema=schema)
        return True
    except Exception as e:
        print(f"  [validate_memory_state] ошибка валидации: {e}")
        return False


#  Сжатие истории в memory_state

def compress_history(history: list[dict], schema: dict) -> dict | None:
    compress_prompt = f"""
Сожми весь предыдущий диалог в один JSON-объект строго по этой JSON-схеме,
без текста до или после:

{json.dumps(schema, ensure_ascii=False, indent=2)}
"""
    messages = history + [{"role": "user", "content": compress_prompt}]

    response = client.chat.completions.create(
        model=MODEL,
        response_format={"type": "json_object"},
        messages=messages,
    )
    raw = response.choices[0].message.content

    try:
        state = json.loads(raw)
    except json.JSONDecodeError:
        print("  [compress_history] модель вернула невалидный JSON, сжатие отменено")
        return None

    if not validate_memory_state(state, schema):
        print("  [compress_history] JSON не прошёл валидацию схемы, сжатие отменено")
        return None

    return state


#  Один прогон сценария в заданном режиме 

COMPRESS_MARKER = "<compress>"


def run_session(turns: list[str], schema: dict, use_compression: bool) -> dict:
    history = [{"role": "system", "content": SYSTEM_PROMPT}]
    token_log = []  # (turn_index, tokens_before_call)
    compressed_state = None

    for i, content in enumerate(turns):
        # Это не слова заявителя, а команда сжатия. Она пропускается
        # (не отправляется модели) в ОБОИХ режимах — чтобы оба прогона
        # видели одинаковое число реальных реплик. В режиме со сжатием
        # на этом же месте дополнительно выполняется compress().
        if content.strip() == COMPRESS_MARKER:
            if use_compression:
                state = compress_history(history, schema)
                if state is not None:
                    compressed_state = state
                    history = [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {
                            "role": "system",
                            "content": "Известные факты о диалоге (сжатое состояние): "
                            + json.dumps(state, ensure_ascii=False),
                        },
                    ]
            continue

        history.append({"role": "user", "content": content})
        token_log.append({"turn": i, "tokens_before_call": count_tokens(history)})

        response = client.chat.completions.create(model=MODEL, messages=history)
        reply = response.choices[0].message.content
        history.append({"role": "assistant", "content": reply})

    return {
        "mode": "compressed" if use_compression else "uncompressed",
        "token_log": token_log,
        "peak_tokens": max((t["tokens_before_call"] for t in token_log), default=0),
        "final_history": history,
        "compressed_state": compressed_state,
    }


#  Проверка "выживания" фактов через probes 
def run_probes(history: list[dict], probes: list[dict]) -> list[dict]:
    results = []
    for probe in probes:
        messages = history + [{"role": "user", "content": probe["question"]}]
        response = client.chat.completions.create(model=MODEL, messages=messages)
        answer = response.choices[0].message.content
        retrieved = any(s.lower() in answer.lower() for s in probe["expect_contains"])
        results.append({
            "id": probe["id"],
            "question": probe["question"],
            "answer": answer,
            "retrieved": retrieved,
        })
    return results


# Главный прогон

def main():
    script_data = load_script()
    schema = load_memory_schema()

    turns = script_data["conversation"]
    probes = script_data["probes"]

    print("=== Режим БЕЗ сжатия ===")
    result_plain = run_session(turns, schema, use_compression=False)
    print(f"Пик токенов: {result_plain['peak_tokens']}")
    probes_plain = run_probes(result_plain["final_history"], probes)

    print("\n=== Режим СО сжатием ===")
    result_compressed = run_session(turns, schema, use_compression=True)
    print(f"Пик токенов: {result_compressed['peak_tokens']}")
    print(f"Итоговое состояние: {json.dumps(result_compressed['compressed_state'], ensure_ascii=False, indent=2)}")
    probes_compressed = run_probes(result_compressed["final_history"], probes)

    print("\n=== Probes: без сжатия vs со сжатием ===")
    for p_plain, p_comp in zip(probes_plain, probes_compressed):
        print(
            f"[{p_plain['id']}] без сжатия={'OK' if p_plain['retrieved'] else 'LOST'}  "
            f"со сжатием={'OK' if p_comp['retrieved'] else 'LOST'}  — {p_plain['question']}"
        )

    out_path = Path(__file__).resolve().parent / "results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "plain": {
                    "peak_tokens": result_plain["peak_tokens"],
                    "token_log": result_plain["token_log"],
                    "probes": probes_plain,
                },
                "compressed": {
                    "peak_tokens": result_compressed["peak_tokens"],
                    "token_log": result_compressed["token_log"],
                    "state": result_compressed["compressed_state"],
                    "probes": probes_compressed,
                },
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(f"\nСохранено в {out_path}")


def interactive():
    """Ручной REPL-режим: python -m sublab_medium.chat_memory --interactive"""
    schema = load_memory_schema()
    history = [{"role": "system", "content": SYSTEM_PROMPT}]

    print("Введи сообщение, 'compress' чтобы сжать историю, 'tokens' чтобы узнать текущий размер, 'exit' чтобы выйти.")
    while True:
        user_input = input("> ").strip()
        if user_input.lower() == "exit":
            break
        if user_input.lower() == "tokens":
            print(f"Текущий размер истории: {count_tokens(history)} токенов")
            continue
        if user_input.lower() == "compress":
            state = compress_history(history, schema)
            if state is not None:
                history = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "system", "content": "Известные факты: " + json.dumps(state, ensure_ascii=False)},
                ]
                print("История сжата.")
            continue

        history.append({"role": "user", "content": user_input})
        response = client.chat.completions.create(model=MODEL, messages=history)
        reply = response.choices[0].message.content
        history.append({"role": "assistant", "content": reply})
        print(reply)


if __name__ == "__main__":
    import sys
    if "--interactive" in sys.argv:
        interactive()
    else:
        main()