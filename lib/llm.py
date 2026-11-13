"""Вызов модели через Codex CLI (подписка ChatGPT ученика, отдельный ключ не нужен). Ответ – JSON.

codex exec запускается в пустой папке data/llm (без AGENTS.md системы), с read-only песочницей
и без личных настроек ~/.codex/config.toml (MCP-серверы и плагины ученика не тормозят каждый вызов)."""
import json
import os
import re
import shutil
import subprocess
import uuid
from datetime import datetime
from pathlib import Path

import config
from lib.common import IS_WIN


class LLMError(Exception):
    pass


def find_codex():
    """codex из PATH, иначе из обычных мест установки: ночью и сразу после установки PATH бывает неполным.
    Последний вариант – программа, встроенная в приложение ChatGPT на Mac."""
    exe = shutil.which("codex")
    if exe:
        return exe
    home = Path.home()
    if IS_WIN:
        local = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
        places = [local / "Programs" / "OpenAI" / "Codex" / "bin" / "codex.exe",
                  Path(os.environ.get("APPDATA", home)) / "npm" / "codex.cmd"]
    else:
        places = [home / ".local/bin/codex", Path("/opt/homebrew/bin/codex"), Path("/usr/local/bin/codex"),
                  Path("/Applications/ChatGPT.app/Contents/Resources/codex"),
                  home / "Applications/ChatGPT.app/Contents/Resources/codex",
                  Path("/Applications/Codex.app/Contents/Resources/codex")]
    for p in places:
        if p.is_file():
            return str(p)
    return None


def _codex():
    exe = find_codex()
    if not exe:
        raise LLMError("не найдена программа codex – попроси Codex в приложении установить Codex CLI (шаг 4 урока)")
    return exe


def command(args):
    """Команда запуска codex с аргументами. Если на Windows codex поставлен через npm, это .cmd – его запускает
    только cmd, а путь с пробелом (C:\\Users\\Ира Иванова\\...) cmd понимает только в двойных кавычках с /s."""
    exe = _codex()
    if IS_WIN and exe.lower().endswith((".cmd", ".bat")):
        return f'cmd /d /s /c ""{exe}" {subprocess.list2cmdline(args)}"'
    return [exe, *args]


def ask_json(prompt, model, timeout=900):
    try:
        return _ask(prompt, model, timeout)
    except LLMError as e:
        if not str(e).startswith("не JSON"):
            raise
        return _ask(prompt + "\n\nВажно: ответ – строго валидный JSON, кавычки внутри строк экранированы.", model, timeout)


NO_TOOLS = ("Работай только с текстом ниже: не запускай команды, не открывай файлы и не ищи в интернете. "
            "Ответ – только JSON, без пояснений до и после.\n\n")


def _ask(prompt, model, timeout):
    work = config.DATA / "llm"
    work.mkdir(exist_ok=True)
    out_file = work / f"{uuid.uuid4().hex}.txt"   # у каждого параллельного вызова свой файл ответа
    name, _, effort = (model or "").partition(":")  # "gpt-6.1-sol:low" → модель и глубина; ":low" – модель аккаунта
    args = ["exec", "--skip-git-repo-check", "--ephemeral", "--ignore-user-config", "--sandbox", "read-only",
            "--color", "never", "-C", str(work), "-o", str(out_file)]
    if name:
        args += ["-m", name]
    if effort:
        args += ["-c", f"model_reasoning_effort={effort}"]
    args.append("-")  # текст задания – из stdin: длинный и с кавычками
    try:
        r = subprocess.run(command(args), input=NO_TOOLS + prompt, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout, cwd=work)
    except subprocess.TimeoutExpired:
        raise LLMError(f"Codex не ответил за {timeout} с")
    try:
        text = out_file.read_text(encoding="utf-8").strip() if out_file.exists() else ""
    finally:
        out_file.unlink(missing_ok=True)
    if r.returncode != 0 or not text:
        err = "\n".join(l for l in (r.stderr or "").splitlines() if "ERROR" in l or "error" in l.lower())
        why = (err or r.stderr or r.stdout or "пустой ответ").strip()[-300:]
        low = why.lower()
        if any(w in low for w in ("log out and sign in", "refresh token", "401", "not logged", "login")):
            why = "Codex не вошёл в аккаунт: попроси Codex в приложении запустить codex login и войди через ChatGPT. (" + why + ")"
        elif any(w in low for w in ("usage limit", "rate limit", "429")):
            why = "Кончился лимит Codex в подписке ChatGPT – подожди сброса или поставь глубину low в .env. (" + why + ")"
        raise LLMError(why)
    tries = [text, re.sub(r"^```(?:json)?\s*|\s*```$", "", text)]
    starts = [i for i in (text.find("{"), text.find("[")) if i >= 0]
    if starts:
        tries.append(text[min(starts):max(text.rfind("}"), text.rfind("]")) + 1])
    for t in tries:
        try:
            return json.loads(t)
        except ValueError:
            pass
    with open(config.LOGS / "llm_bad.txt", "a", encoding="utf-8") as f:
        f.write(f"\n===== {datetime.now():%Y-%m-%d %H:%M}\n{text}\n")
    raise LLMError("не JSON: " + text[:300])
