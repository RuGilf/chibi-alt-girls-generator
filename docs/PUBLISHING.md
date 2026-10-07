# Публикация на GitHub

[На главную](../README.md)

Папка уже содержит исходники, README, галереи, тесты, CI и установочный ZIP в `releases/`. Личные сцены и избранное не включены. GitHub-репозиторий и релиз ещё не созданы.

## Перед первым push

Выбери лицензию и при необходимости добавь её текст в `LICENSE`, обнови разделы лицензии в README/CONTRIBUTING, затем пересобери ZIP. Если решение ещё не принято, текущая документация прямо указывает, что лицензия не выбрана.

Создай пустой репозиторий на GitHub, например `altushka-character-generator`, без автоматически добавленных README, `.gitignore` и лицензии — нужные файлы уже подготовлены.

В терминале в корне подготовленной папки:

```sh
# Если папка получена из ZIP и ещё не является Git-репозиторием:
git init -b main

# Создай начальный коммит:
git add .
git commit -m "Prepare ALTUSHKA Character Generator 0.8.0"

# Замени YOUR_USERNAME и имя репозитория на свои:
git remote add origin https://github.com/YOUR_USERNAME/altushka-character-generator.git
git push -u origin main
```

Команды публикуют файлы только после твоего запуска и авторизации. Автор и email коммита берутся из твоих настроек Git.

## Release 0.8.0

1. Проверь результат GitHub Actions.
2. Открой Releases → Draft a new release.
3. Создай тег `v0.8.0` для опубликованного коммита.
4. Название: **ALTUSHKA 0.8.0 — hands and poses**.
5. Кратко перечисли: цельные кисти, 10 стоячих поз, независимые жесты, сохранение в JSON и избранное. Укажи тестированную версию Blender и известные ограничения из README.
6. Прикрепи `releases/chibi_generator_v0.8.0.zip` и его `.sha256`.
7. Опубликуй релиз.

Описание репозитория: **Modular Blender chibi character generator with alternative fashion, hairstyles, skin tones, poses and hand gestures.**

Темы: `blender`, `blender-addon`, `character-generator`, `chibi`, `procedural-generation`, `python`, `character-creation`.
