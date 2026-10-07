# Публикация на GitHub

[На главную](../README.md)

Папка уже содержит исходники, README, галереи, тесты, CI и установочный ZIP в `releases/`. Личные сцены и избранное не включены. Удалённый репозиторий создан. Изменения дополнения подготавливаются локально; команды публикации выполняются отдельно.

## Перед первым push

Для уже существующего клона с локальными коммитами в рабочей ветке:

```sh
git status
git log -3 --oneline
git push -u origin HEAD
```

Это отправит текущую ветку; после проверки её можно объединить с основной через pull request на GitHub. Следующие шаги нужны только при публикации новой копии из ZIP.

Если используешь существующий клон, проверь адрес командой `git remote -v`. Для новой копии сначала создай пустой репозиторий GitHub без автоматически добавленных файлов.

В терминале в корне подготовленной папки:

```sh
# Если папка получена из ZIP и ещё не является Git-репозиторием:
git init -b main

# Создай начальный коммит:
git add .
git commit -m "Prepare ALTUSHKA Character Generator 0.9.0"

# Замени YOUR_USERNAME и имя репозитория на свои:
git remote add origin https://github.com/YOUR_USERNAME/altushka-character-generator.git
git push -u origin main
```

Команды публикуют файлы только после твоего запуска и авторизации. Автор и email коммита берутся из твоих настроек Git.

## Release 0.9.0

1. Проверь результат GitHub Actions.
2. Открой Releases → Draft a new release.
3. Создай тег `v0.9.0` для опубликованного коммита.
4. Название: **ALTUSHKA 0.9.0 — faces, hair and hands**.
5. Кратко перечисли: новые поверхности ткани и кожи, стабильный рельеф, исправления создания персонажа, поз и загрузки JSON. Укажи тестированную версию Blender и известные ограничения из README.
6. Прикрепи `releases/chibi_generator_v0.9.0.zip` и его `.sha256`.
7. Опубликуй релиз.

Описание репозитория: **Modular Blender chibi character generator with alternative fashion, hairstyles, skin tones, poses and hand gestures.**

Темы: `blender`, `blender-addon`, `character-generator`, `chibi`, `procedural-generation`, `python`, `character-creation`.
