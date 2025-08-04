#!/bin/bash

# Запускаем ssh-agent и экспортируем переменные окружения
eval "$(ssh-agent -s)"

# Добавляем приватный ключ GitLab
ssh-add ~/.ssh/github

# Проверка
echo "✅ SSH-ключ для Git добавлен:"
ssh-add -l
