# increment_version.py
with open("config/version.py", "r+") as file:
    lines = file.readlines()
    version_line = lines[0]
    version_parts = version_line.split('"')
    version_num = version_parts[1]
    major, minor, patch = map(int, version_num.split("."))
    patch += 1  # Increment the patch number
    new_version = f'"{major}.{minor}.{patch}"'
    lines[0] = f"VERSION = {new_version}\n"
    file.seek(0)
    file.writelines(lines)
