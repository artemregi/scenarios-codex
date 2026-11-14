# Codex вместо Claude Code: что работает, что нет

Codex – агент OpenAI, который работает так же, как Claude Code: ты пишешь задание, он сам запускает команды и правит
файлы. С осени 2026 Codex встроен в приложение ChatGPT для компьютера (режимы Chat / Work / Codex). Вход – аккаунтом
ChatGPT.

Ученик работает только в приложении. Ночью система работает без приложения: скрипты вызывают программу `codex`
(Codex CLI), её Codex ставит сам на шаге 4. Вход у приложения и программы общий – папка `~/.codex`.

Сверено с документацией learn.chatgpt.com, ноябрь 2026.

## Тарифы

| тариф | приложение Codex | программа `codex` (ночной запуск) |
|---|---|---|
| Free, Go | ✅ модель GPT-6 Luna, доступ открывают постепенно | ❌ |
| Plus ($20) | ✅ | ✅ модели GPT-6.1 Sol и GPT-6 Luna, лимит считается окнами по 5 часов |
| Pro и выше | ✅ | ✅ |

Поэтому в уроке нужен Plus. Остаток лимита – chatgpt.com/codex/settings/usage.

## Как система вызывает модель

| | Claude Code | Codex |
|---|---|---|
| Где работает ученик | Терминал, `claude` | приложение ChatGPT → Codex → открыть папку |
| Без вопросов о разрешениях | `claude --dangerously-skip-permissions` | переключатель под строкой ввода → **Full access** |
| Вызов из скриптов (ночью) | `claude -p` | `codex exec` |
| Файл с инструкцией для агента | `CLAUDE.md` | `AGENTS.md` |
| Вход | `claude` → логин Claude | в приложении «Continue to sign in», для программы при необходимости `codex login` |
| Модели | haiku / sonnet / opus | модель аккаунта + глубина low / medium / high |

Скрипты системы (`passport.py`, `discover.py`, `write.py`) вызывают модель через `lib/llm.py`:
`codex exec` в пустой папке `data/llm`, песочница только для чтения, без личных настроек `~/.codex/config.toml`
(чтобы плагины и MCP-серверы ученика не тормозили каждый вызов). Ответ забирается из файла `-o`.

Модель в `.env` по умолчанию пустая (`SCORE_MODEL=:low`, `WRITE_MODEL=:medium`) – берётся модель, которая стоит у
аккаунта по умолчанию. Названия моделей у OpenAI меняются часто: GPT-5.5 убрали из Codex 14.10.2026, если вписать
устаревшее название, `doctor.py` покажет ошибку.

`codex` ищется в PATH, потом в обычных местах установки (`~/.local/bin`, Homebrew, `%LOCALAPPDATA%\Programs\OpenAI\Codex\bin`),
в последнюю очередь – внутри приложения ChatGPT на Mac (`/Applications/ChatGPT.app/Contents/Resources/codex`).

## Что проверено

| что | статус |
|---|---|
| Установка программы на Mac: `curl -fsSL https://chatgpt.com/codex/install.sh \| sh` или `brew install --cask codex` | ✅ |
| `npm i -g @openai/codex` без прав администратора | ❌ ошибка EACCES, поэтому в уроке установщик OpenAI |
| Внутри приложения ChatGPT на Mac лежит своя программа `codex` с `codex exec` | ✅ запасной путь в `lib/llm.py` |
| `codex login status` показывает реальное состояние входа | ❌ пишет «Logged in», даже когда токен отозван. Проверять только настоящим запросом – так делает `doctor.py` |
| Режим Full access = без песочницы и без вопросов (`danger-full-access` + `never`) | ✅ по документации |
| Обычный режим приложения не пускает команды в интернет | ✅ по документации, поэтому в уроке Full access |
| «Запланированные задачи» приложения работают, только пока приложение открыто | ✅ по документации, поэтому ночью launchd / Планировщик Windows |
| `codex exec` на Plus: скорость, 3 вызова параллельно (`PARALLEL=3` в `write.py`) | ⏳ нужна подписка Plus |
| Программа `codex` подхватывает вход из приложения без `codex login` | ⏳ нужна подписка Plus |
| Ночной запуск из расписания с входом ChatGPT | ⏳ нужна подписка Plus |
| Chrome (`login.py`, `collect.py`) из Full access | ⏳ нужна подписка Plus |
| `bank.py` в фоне живёт после ответа Codex в приложении | ⏳ нужна подписка Plus |
| Загрузка `AGENTS.md` из открытой папки | ⏳ нужна подписка Plus |
| Windows: агент в PowerShell, Python через uv без администратора, ночной запуск из Планировщика (в том числе от батареи) | ⏳ нужен компьютер на Windows |

## Чем отличается от Claude Code

- **Лимиты.** Codex тратит лимит подписки ChatGPT, общий с режимом Work. Если он кончился, `write.py` упадёт с
  ошибкой «Кончился лимит Codex». Остаток – chatgpt.com/codex/settings/usage.
- **Песочница.** Без Full access Codex не пускает команды в интернет и спрашивает разрешение. Системе нужны Instagram,
  Telegram и Chrome, поэтому в каждом новом чате проверяй Full access.
- **Вход может слететь.** Тогда `doctor.py` и ночной запуск пишут «Codex не вошёл в аккаунт». Лечится так: попроси
  Codex в приложении запустить `codex login` и войди в браузере.
- **Windows.** Если команды падают с ошибкой про execution policy – попроси Codex выполнить
  `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`.
