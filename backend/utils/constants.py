CATEGORY_RULES = {
    "logs": {
        ".log",
        ".txt",
        ".out",
        ".trace",
        ".err",
    },
    "images": {
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
        ".bmp",
        ".gif",
        ".tif",
        ".tiff",
    },
    "documents": {
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".csv",
        ".json",
        ".xml",
        ".md",
    },
    "archives": {
        ".zip",
        ".rar",
        ".7z",
        ".tar",
        ".gz",
    },
    "code": {
        ".py",
        ".js",
        ".ts",
        ".vue",
        ".html",
        ".css",
        ".java",
        ".go",
        ".rs",
        ".sql",
    },
}

# 文件名模式分类规则（优先级高于扩展名分类）
# 格式: { category: [正则表达式列表] }
FILENAME_PATTERNS = {
    "images": [
        r"(?i)screenshot|screen.?shot|截图|屏幕截图",
        r"(?i)^IMG[_-]\d{8}",
        r"(?i)^DCIM|^DSC[_N]|^P\d{7,}",
        r"(?i)photo|照片|图片",
    ],
    "logs": [
        r"(?i)^error|crash|dump|trace|debug",
        r"(?i)log[_-]?\d|日志",
        r"(?i)stderr|stdout|core\.\d+",
    ],
    "documents": [
        r"(?i)invoice|发票|票据|收据|receipt",
        r"(?i)contract|合同|协议",
        r"(?i)report|报告|报表",
        r"(?i)resume|简历|CV",
        r"(?i)meeting|会议|纪要",
    ],
    "archives": [
        r"(?i)backup|备份",
        r"(?i)release|发布|部署",
    ],
    "code": [
        r"(?i)config|配置|settings",
        r"(?i)Makefile|Dockerfile|\.env\b",
    ],
}

# 临时/缓存文件名模式（用于 delete 建议）
TEMP_FILE_PATTERNS = [
    r"(?i)^(tmp|temp|cache|~)",
    r"(?i)\.(tmp|temp|cache|bak|swp|swo)$",
    r"(?i)^\.DS_Store$|^Thumbs\.db$|^desktop\.ini$",
    r"(?i)^__MACOSX|^\._",
]

CATEGORY_LABELS = {
    "logs": "日志",
    "images": "图片",
    "documents": "文档/数据表",
    "archives": "压缩包",
    "code": "代码",
    "unknown": "未知类型",
}

ALLOWED_ACTIONS = {"rename_and_move", "move", "delete", "keep"}

TEXT_EXTENSIONS = {
    ".txt",
    ".log",
    ".csv",
    ".md",
    ".json",
    ".xml",
    ".yaml",
    ".yml",
    ".ini",
    ".conf",
    ".py",
    ".js",
    ".ts",
    ".vue",
    ".html",
    ".css",
    ".sql",
}

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"}

WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
}

WINDOWS_INVALID_CHARS = set(r'\/:*?"<>|')

MAX_FILENAME_LENGTH = 255
