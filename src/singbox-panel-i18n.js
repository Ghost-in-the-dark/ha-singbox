/**
 * Tiny RU/EN localization for the sing-box panel card.
 *
 * Language resolution order:
 *   1. explicit config.language ("ru" | "en")
 *   2. "auto" (default) -> Home Assistant UI language (hass.language), any
 *      variant that starts with "ru" maps to Russian, everything else to
 *      English.
 *
 * translate(lang, key, params) picks the string for the language and
 * substitutes {name} placeholders.
 */

const MESSAGES = {
    // -- card ---------------------------------------------------------------
    loading: {
        ru: "Загрузка данных sing-box…",
        en: "Loading sing-box data…",
    },
    testAll: {
        ru: "Проверить все",
        en: "Test all",
    },
    testing: {
        ru: "Тест…",
        en: "Testing…",
    },
    test: {
        ru: "Тест",
        en: "Test",
    },
    speedUp: {
        ru: "Загрузка",
        en: "Upload",
    },
    speedDown: {
        ru: "Скачивание",
        en: "Download",
    },
    selectTitle: {
        ru: "Выбрать {tag}",
        en: "Select {tag}",
    },
    pingTitle: {
        ru: "Проверить пинг {tag}",
        en: "Check ping of {tag}",
    },
    errors: {
        loadFailed: {
            ru: "Не удалось загрузить данные: {msg}",
            en: "Failed to load data: {msg}",
        },
        groupsDevice: {
            ru: "Группы прокси не найдены: по device_id найдено записей реестра: {count}, но сущностей ha-singbox среди них нет (select во всём реестре: {selects}, ping-сенсоров: {pings}). Пример записей по device_id: {sample}. Убедитесь, что установлена интеграция ha-singbox (Ghost-in-the-dark/ha-singbox) и она создала сущности, затем перезапустите HA.",
            en: "Proxy groups not found: device_id matched {count} registry records, but none of them are ha-singbox entities (selects across the registry: {selects}, ping sensors: {pings}). Sample records on the device: {sample}. Make sure the ha-singbox integration (Ghost-in-the-dark/ha-singbox) is installed and created entities, then restart HA.",
        },
        groupsNone: {
            ru: "Группы прокси не найдены: в реестре нет сущностей sing-box (всего select: {selects}, ping-сенсоров: {pings}). Проверьте, что ha-singbox установлена и настроена, затем перезапустите HA.",
            en: "Proxy groups not found: the registry has no sing-box entities (selects in total: {selects}, ping sensors: {pings}). Check that ha-singbox is installed and configured, then restart HA.",
        },
        groupsBadUid: {
            ru: "Группы прокси не найдены: select-сущности есть, но с неожиданным форматом unique_id ({sample}). Обновите ha-singbox и перезапустите HA.",
            en: "Proxy groups not found: select entities exist but with an unexpected unique_id format ({sample}). Update ha-singbox and restart HA.",
        },
    },
    fallback: {
        device: {
            ru: "device_id «{device}» не дал групп (записей реестра: {count}) — показаны все экземпляры sing-box.",
            en: "device_id “{device}” produced no groups ({count} registry records) — showing all sing-box instances.",
        },
        entityNotFound: {
            ru: "entity «{entity}» не найдена в реестре — показаны все экземпляры sing-box.",
            en: "entity “{entity}” was not found in the registry — showing all sing-box instances.",
        },
        entityNoGroups: {
            ru: "entity «{entity}» не дала групп — показаны все экземпляры sing-box.",
            en: "entity “{entity}” produced no groups — showing all sing-box instances.",
        },
    },

    // -- traffic chart -------------------------------------------------------
    chart: {
        down: { ru: "Скачивание", en: "Download" },
        up: { ru: "Загрузка", en: "Upload" },
        peak: {
            ru: "Пик: {value}",
            en: "Peak: {value}",
        },
        now: {
            ru: "Сейчас: ↓ {down} · ↑ {up}",
            en: "Now: ↓ {down} · ↑ {up}",
        },
        empty: {
            ru: "Собираем данные для графика…",
            en: "Collecting chart data…",
        },
    },

    // -- connections ---------------------------------------------------------
    connections: {
        title: { ru: "Подключения", en: "Connections" },
        count: {
            ru: "всего: {total}",
            en: "total: {total}",
        },
        countFiltered: {
            ru: "{shown} из {total}",
            en: "{shown} of {total}",
        },
        search: {
            ru: "Поиск: хост, процесс, правило…",
            en: "Search: host, process, rule…",
        },
        network: { ru: "Сеть", en: "Network" },
        protocol: { ru: "Протокол", en: "Protocol" },
        outbound: { ru: "Outbound", en: "Outbound" },
        allNetworks: { ru: "Все сети", en: "All networks" },
        allProtocols: { ru: "Все протоколы", en: "All protocols" },
        allOutbounds: { ru: "Все outbound", en: "All outbounds" },
        reset: { ru: "Сбросить", en: "Reset" },
        close: { ru: "Закрыть подключение", en: "Close connection" },
        closeAll: { ru: "Закрыть все", en: "Close all" },
        empty: {
            ru: "Активных подключений нет",
            en: "No active connections",
        },
        noMatch: {
            ru: "Ничего не найдено по фильтру",
            en: "Nothing matches the filter",
        },
        unsupported: {
            ru: "Этот бэкенд sing-box не отдаёт список подключений.",
            en: "This sing-box backend does not expose the connection list.",
        },
        unavailable: {
            ru: "Список подключений недоступен: {msg}",
            en: "Connection list unavailable: {msg}",
        },
    },

    // -- visual editor --------------------------------------------------------
    editor: {
        sections: {
            ru: "Что показывать на карточке",
            en: "Sections shown on the card",
        },
        sectionsHint: {
            ru: "Отключите блоки, которые не нужны. Настройки остаются в конфиге и включаются обратно одним переключателем.",
            en: "Turn off the blocks you do not need. The settings stay in the config and come back with one switch.",
        },
        show_test_all: {
            ru: "Кнопка «Проверить все»",
            en: "“Test all” button",
        },
        show_speeds: {
            ru: "Текущая скорость (плитки)",
            en: "Current speed (tiles)",
        },
        show_chart: {
            ru: "График трафика",
            en: "Traffic chart",
        },
        show_totals: {
            ru: "Сводка: всего, память, соединения",
            en: "Totals: traffic, memory, connections",
        },
        show_groups: {
            ru: "Группы и outbound",
            en: "Groups and outbounds",
        },
        show_connections: {
            ru: "Список подключений",
            en: "Connections list",
        },
        title: { ru: "Заголовок", en: "Title" },
        language: { ru: "Язык интерфейса", en: "Interface language" },
        languageAuto: {
            ru: "Авто (как в Home Assistant)",
            en: "Auto (follow Home Assistant)",
        },
        interval: { ru: "Скорость обновления", en: "Update interval" },
        intervalLive: { ru: "В реальном времени", en: "Real time (default)" },
        intervalSec: { ru: "{n} сек", en: "{n} s" },
        intervalHint: {
            ru: "Как часто обновлять показания на карточке. 0 — при каждом изменении состояния в HA (по умолчанию). Выбор outbound и кнопки теста всегда применяются сразу.",
            en: "How often the card refreshes its values. 0 — on every HA state change (default). Outbound selection and the test buttons always apply instantly.",
        },
        showTestAll: {
            ru: "Кнопка «Проверить все»",
            en: "“Test all” button",
        },
        showTestAllHint: {
            ru: "Массовый url-test по всем группам и outbound в один клик.",
            en: "Batch url-test of every group and outbound in one tap.",
        },
        exclude: {
            ru: "Скрыть outbound из карточки",
            en: "Hide outbounds from the card",
        },
        excludeHint: {
            ru: "Отмеченные теги не показываются в группах и блоке Outbound.",
            en: "Checked tags are hidden from the groups and the Outbound block.",
        },
        device: { ru: "device_id (необязательно)", en: "device_id (optional)" },
        deviceHint: {
            ru: "Привязка к конкретному устройству sing-box, если их несколько.",
            en: "Pin to a specific sing-box device when several are configured.",
        },
        entity: { ru: "entity (необязательно)", en: "entity (optional)" },
        entityHint: {
            ru: "Альтернативная привязка через любую сущность ha-singbox.",
            en: "Alternative pin via any ha-singbox entity.",
        },
    },
};

export const LANGUAGES = ["auto", "ru", "en"];

export function resolveLanguage(config, hass) {
    const pick = (config && config.language) || "auto";
    if (pick === "ru" || pick === "en") return pick;
    const sys =
        (hass && (hass.language || (hass.locale && hass.locale.language))) || "";
    return String(sys).toLowerCase().startsWith("ru") ? "ru" : "en";
}

function lookup(key) {
    return key.split(".").reduce((node, part) => node && node[part], MESSAGES);
}

export function translate(lang, key, params = {}) {
    const entry = lookup(key);
    const template = (entry && (entry[lang] || entry.en)) || key;
    return Object.entries(params).reduce(
        (text, [name, value]) =>
            text.split(`{${name}}`).join(String(value)),
        template
    );
}
