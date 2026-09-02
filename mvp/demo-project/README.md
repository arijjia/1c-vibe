# Демо-репозиторий 1c-vibe (контент для GitLab)

Синтетическое дерево «выгрузки конфигурации 1С» — для демонстрации цикла
«задача в Jira → правка агентом → MR → проверка CI». XML упрощён по сравнению
с реальной выгрузкой платформы, но структура каталогов — как в настоящей:
`Configuration.xml`, `Catalogs/<Имя>/Object.xml`, `Catalogs/<Имя>/Ext/*.bsl`.

Содержимое этого каталога кладётся в отдельный git-проект (см. `../README.md`).

## Локальная проверка линтером (без GitLab CI)

```
BSL_LS_VERSION=1.0.7
curl --fail --location --output /tmp/bsl-language-server.jar \
  "https://github.com/1c-syntax/bsl-language-server/releases/download/v${BSL_LS_VERSION}/bsl-language-server-${BSL_LS_VERSION}-exec.jar"
echo "9f62765edd344d66456da24c906eaf623a03c56e90e5aafee466200100909f64  /tmp/bsl-language-server.jar" | shasum -a 256 --check
java -Xmx1g -jar /tmp/bsl-language-server.jar analyze \
  --srcDir . --workspaceDir . --outputDir bsl-reports \
  --reporter json --reporter code-quality
python3 ci/check_lint.py bsl-reports/bsl-json.json
```

Проверенная связка: BSL Language Server 1.0.7 и Java 25. Версия и checksum
совпадают с `.gitlab-ci.yml`.

## CI

`.gitlab-ci.yml` запускает BSL Language Server в headless-режиме и работает
fail-closed: анализатор, checksum, формат отчёта и диагностики Error должны быть
успешны. Отчёт публикуется и как артефакт, и как GitLab Code Quality report.
Требования к раннеру: Docker executor и исходящий HTTPS к Docker Hub/GitHub.
