import glob

def expand_globs(patterns: list[str]) -> list[str]:
    files: list[str] = []

    for pattern in patterns:
        matches = sorted(glob.glob(pattern))
        if not matches:
            raise SystemExit(f'No files match: {pattern}')
        files.extend(matches)

    return list(dict.fromkeys(files))