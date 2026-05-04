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
