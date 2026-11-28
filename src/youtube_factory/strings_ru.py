"""All user-facing Russian strings in one place."""

APP_TITLE = "YouTube Factory — Фабрика Shorts"
APP_NAME_RU = "Фабрика Shorts"

# Navigation
NAV_HOME = "Главная"
NAV_HISTORY = "История"
NAV_SETTINGS = "Настройки"

# Home
HOME_TAGLINE = "Превращайте длинные видео в идеи для Shorts за минуту"
HOME_SUBTITLE = (
    "Вставьте ссылку на видео. Транскрипт программа получит сама, а можно добавить свой."
)
URL_PLACEHOLDER = "Вставьте ссылку на YouTube-видео"
BTN_CREATE = "Создать Shorts"
BTN_EXAMPLE = "Попробовать пример"
BTN_PASTE_TRANSCRIPT = "Вставить транскрипт…"
RECENT_TITLE = "Недавние анализы"
BTN_ALL_HISTORY = "Вся история"
TILE_DEMO_TITLE = "Попробовать пример"
TILE_DEMO_TEXT = "Готовое видео, интернет не нужен"
TILE_PASTE_TITLE = "Свой транскрипт"
TILE_PASTE_TEXT = "Вставьте текст или откройте файл"
RECENT_EMPTY = "Пока пусто. Создайте первый анализ — он появится здесь."

# Transcript dialog
TRANSCRIPT_DIALOG_TITLE = "Транскрипт видео"
TRANSCRIPT_HINT = "Вставьте текст или откройте файл .txt, .srt или .vtt"
TRANSCRIPT_PLACEHOLDER = "Вставьте сюда транскрипт…"
BTN_OPEN_FILE = "Открыть файл…"
BTN_ANALYZE = "Анализировать"
BTN_CANCEL = "Отмена"
FILE_FILTER = "Транскрипты (*.txt *.srt *.vtt);;Все файлы (*)"
OPEN_FILE_TITLE = "Выберите файл транскрипта"
TITLE_OPTIONAL_PLACEHOLDER = "Название видео (необязательно)"
UNTIMED_NOTE = "В тексте нет меток времени — тайминг оценён по скорости речи."

# Analysis
ANALYSIS_TITLE = "Анализируем видео"
STEPS = [
    "Получаем данные видео",
    "Извлекаем транскрипт",
    "Ищем сильные моменты",
    "Генерируем идеи Shorts",
    "Готовим результаты",
]
BTN_CANCEL_ANALYSIS = "Отменить"
BTN_BACK = "Назад"
BTN_RETRY = "Повторить"
ANALYSIS_CANCELLED = "Анализ отменён."

# Results
BTN_NEW_ANALYSIS = "Новый анализ"
BTN_FAVORITES_ONLY = "Только избранное"
FILTER_ALL = "Все"
FILTER_FAVORITES = "Избранное"
BTN_EXPORT_JSON = "Экспорт в JSON"
BTN_EXPORT_CSV = "Экспорт в CSV"
BTN_OPEN_VIDEO = "Открыть на YouTube"
EXPORT_SELECTED_HINT = "Экспортируются отмеченные карточки; если ничего не отмечено — все."
RESULTS_EMPTY = "Здесь пока нет Shorts. Измените фильтр или начните новый анализ."
MODE_DEMO = "Демо"
MODE_MANUAL = "Свой транскрипт"
DURATION_LABEL = "Длительность"
SCORE_LABEL = "Потенциал"
LABEL_HOOK = "Хук"
LABEL_TITLE = "Название"
LABEL_DESCRIPTION = "Описание"
LABEL_REASON = "Почему сработает"
SELECT_FOR_EXPORT = "Выбрать для экспорта"
TIP_COPY = "Скопировать весь текст"
TIP_EDIT = "Редактировать"
TIP_FAVORITE = "В избранное"
TIP_UNFAVORITE = "Убрать из избранного"
TIP_DELETE = "Удалить"
BTN_SAVE = "Сохранить"
BTN_COPY = "Копировать"
BTN_EDIT = "Править"
BTN_DELETE = "Удалить"
FAV_ON = "В избранном"
FAV_OFF = "В избранное"

# History
HISTORY_TITLE = "История анализов"
HISTORY_EMPTY = "История пуста."
BTN_OPEN = "Открыть"
CONFIRM_DELETE_TITLE = "Удалить запись?"
CONFIRM_DELETE_ANALYSIS = (
    "Анализ «{title}» и все его Shorts будут удалены без возможности восстановления."
)
CONFIRM_DELETE_SHORT = "Удалить этот Short?"
SHORTS_COUNT = "Shorts: {n}"

# Settings
SETTINGS_TITLE = "Настройки"
SETTINGS_APPEARANCE = "Оформление"
SETTINGS_THEME = "Тема"
SETTINGS_ANIMATIONS = "Плавные анимации"
SETTINGS_ANIMATIONS_HINT = "Выключите, чтобы максимально разгрузить компьютер."
SETTINGS_FILES = "Файлы"
THEME_DARK = "Тёмная"
THEME_LIGHT = "Светлая"
THEME_SYSTEM = "Системная"
SETTINGS_EXPORT_DIR = "Папка экспорта"
EXPORT_DIR_PLACEHOLDER = "Не выбрана — каждый раз спрашивать"
BTN_CHOOSE_FOLDER = "Выбрать…"
CHOOSE_FOLDER_TITLE = "Выберите папку для экспорта"
SETTINGS_API_TITLE = "Интеграции (скоро)"
SETTINGS_API_NOTE = (
    "Ключи читаются только из переменных окружения Windows или файла .env. "
    "В программе они не хранятся."
)
API_YOUTUBE = "YouTube Data API"
API_TRANSCRIPTS = "Сервис транскриптов"
API_LLM = "Языковая модель (локальная или облачная)"
API_SOON = "Появится в следующих версиях"
SETTINGS_ABOUT = "О программе"
ABOUT_TEXT = "{name}\nВерсия {version}\nВсе данные хранятся только на вашем компьютере."
BTN_OPEN_DATA_DIR = "Открыть папку с данными"
SETTINGS_SAVED = "Настройки сохранены"

# Toasts
TOAST_COPIED = "Текст скопирован"
TOAST_SAVED = "Изменения сохранены"
TOAST_DELETED = "Удалено"
TOAST_EXPORTED = "Файл сохранён: {path}"
TOAST_FAV_ADDED = "Добавлено в избранное"
TOAST_FAV_REMOVED = "Убрано из избранного"
TOAST_CLEAR_HISTORY = "Запись удалена из истории"

# Errors
ERR_TITLE = "Ошибка"
ERR_EMPTY_URL = "Вставьте ссылку на видео или нажмите «Попробовать пример»."
ERR_NOT_YOUTUBE = "Это не похоже на ссылку YouTube. Проверьте адрес и попробуйте снова."
ERR_NO_VIDEO_ID = "Не удалось найти идентификатор видео в ссылке."
ERR_NO_TRANSCRIPT = (
    "У этого видео нет субтитров, поэтому транскрипт не получить автоматически. "
    "Нажмите «Вставить транскрипт…» и добавьте текст или файл."
)
ERR_NET_OFFLINE = "Нет связи с YouTube. Проверьте интернет и попробуйте ещё раз."
ERR_NET_ERROR = "Не удалось загрузить данные видео. Попробуйте позже или вставьте транскрипт."
ERR_VIDEO_UNAVAILABLE = "Видео недоступно: оно удалено или закрыто в вашем регионе."
ERR_VIDEO_PRIVATE = "Видео приватное или только для участников канала."
ERR_AGE_RESTRICTED = "Видео с ограничением по возрасту: YouTube не отдаёт его без входа в аккаунт."
ERR_VIDEO_LIVE = "Это прямая трансляция или премьера. Дождитесь окончания и повторите."
ERR_BOT_CHECK = (
    "YouTube просит подтвердить, что вы не робот. Подождите немного и повторите "
    "или вставьте транскрипт вручную."
)
ERR_TRANSCRIPT_EMPTY = "Транскрипт пустой. Вставьте текст или выберите файл."
ERR_TRANSCRIPT_TYPE = "Поддерживаются только файлы .txt, .srt и .vtt."
ERR_TRANSCRIPT_UNREADABLE = (
    "Не удалось прочитать файл. Проверьте, что он существует и в кодировке UTF-8."
)
ERR_TRANSCRIPT_LARGE = "Файл слишком большой. Максимальный размер — 5 МБ."
ERR_TOO_SHORT = "Транскрипт слишком короткий для анализа. Нужно хотя бы несколько абзацев."
ERR_NO_CANDIDATES = "Не нашлось подходящих фрагментов. Попробуйте транскрипт подлиннее."
ERR_UNKNOWN = "Что-то пошло не так. Подробности записаны в журнал."
ERR_EXPORT = "Не удалось сохранить файл: {reason}"
ERR_OPEN_URL = "Не удалось открыть ссылку в браузере."
ERR_DB = "Не удалось открыть историю. Работа продолжится без сохранения."
ERR_ALREADY_RUNNING = "Другая копия «Фабрики Shorts» уже запущена."
EXPORT_JSON_TITLE = "Сохранить JSON"
EXPORT_CSV_TITLE = "Сохранить CSV"
EXPORT_JSON_FILTER = "JSON (*.json)"
EXPORT_CSV_FILTER = "CSV (*.csv)"
DEFAULT_VIDEO_TITLE = "Видео без названия"
