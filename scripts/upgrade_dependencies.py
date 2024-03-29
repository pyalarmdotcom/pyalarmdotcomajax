"""Update dependency versions."""

# ruff: noqa: T201

import re
from pathlib import Path

import requests
import tomli
import tomli_w
import yaml


def get_latest_version(package_name: str) -> str | None:
    """Fetch the latest version of a package from PyPI, stripping extras from the package name."""
    # Strip extras from the package name if present
    package_name = package_name.split("[")[0]
    response = requests.get(f"https://pypi.org/pypi/{package_name}/json", timeout=5)
    if response.status_code == 200:
        data = response.json()
        return data["info"]["version"]  # type: ignore

    print(f"Failed to fetch latest version for {package_name}")
    return None


def parse_dependency_string(dep: str) -> tuple[str, str, str]:
    """Extract package name and version from a dependency string, ignoring comments and handling extras."""
    dep = dep.strip()
    if dep.startswith("#"):
        return "", "", "comment"

    package_match = re.match(r"([a-zA-Z0-9\-_]+(\[.+\])?)(\s*[>=<~!^]+\s*)(.*)", dep)
    if package_match:
        package_name, _, _, version = package_match.groups()
        return package_name, version.strip(), "dependency"

    return "", "", "unknown"


def update_dependencies(
    dependencies: list[str],
) -> tuple[list[str], list[tuple[str, str, str]]]:
    """Update a list of dependency strings to their latest versions, respecting the format and ignoring comments."""
    updated_dependencies = []
    updates = []
    for dep in dependencies:
        package_name, current_version, line_type = parse_dependency_string(dep)
        if line_type == "comment":
            updated_dependencies.append(dep)
            continue
        if line_type == "dependency":
            latest_version = get_latest_version(package_name)
            if latest_version and latest_version != current_version:
                updated_dependencies.append(f"{package_name} >= {latest_version}")
                updates.append((package_name, current_version, latest_version))
            else:
                updated_dependencies.append(dep)
        else:
            updated_dependencies.append(dep)

    return updated_dependencies, updates


def update_pyproject_toml(directory: Path, updates_log: dict[str, list[tuple[str, str, str]]]) -> None:
    """Update dependencies in 'pyproject.toml' to their latest versions."""
    pyproject_path = directory / "pyproject.toml"

    # Open the TOML file in binary read mode for tomli
    with pyproject_path.open("rb") as file:
        data = tomli.load(file)

    dependencies = data.get("project", {}).get("dependencies", [])
    updated_dependencies, updates = update_dependencies(dependencies)
    data["project"]["dependencies"] = updated_dependencies

    # Log updates
    if updates:
        updates_log["pyproject.toml"] = updates

    # Open the TOML file in text write mode for tomli_w
    with pyproject_path.open("wb") as file:
        tomli_w.dump(data, file)


def update_pre_commit_config(directory: Path, updates_log: dict[str, list[tuple[str, str, str]]]) -> None:
    """Update dependencies in '.pre-commit-config.yaml' to their latest versions."""
    pre_commit_path = directory / ".pre-commit-config.yaml"
    with pre_commit_path.open("r+", encoding="utf-8") as file:
        data = yaml.safe_load(file)
        for repo in data.get("repos", []):
            for hook in repo.get("hooks", []):
                if "additional_dependencies" in hook:
                    updated_deps, updates = update_dependencies(hook["additional_dependencies"])
                    hook["additional_dependencies"] = updated_deps
                    if updates:
                        updates_log[".pre-commit-config.yaml"] = updates

        file.seek(0)
        yaml.dump(data, file, default_flow_style=False)
        file.truncate()


def update_requirements_dev(directory: Path, updates_log: dict[str, list[tuple[str, str, str]]]) -> None:
    """Update dependencies in 'requirements-dev.txt' to their latest versions."""
    requirements_path = directory / "requirements-dev.txt"
    with requirements_path.open("r+", encoding="utf-8") as file:
        lines = file.readlines()
        updated_lines, updates = update_dependencies(lines)

        file.seek(0)
        file.writelines(updated_lines)
        file.truncate()

        if updates:
            updates_log["requirements-dev.txt"] = updates


def main(directory_path: str = "/workspaces/pyalarmdotcomajax/") -> None:
    """Update all package dependencies to their latest versions across multiple configuration files."""
    directory = Path(directory_path)
    updates_log: dict[str, list[tuple[str, str, str]]] = {}
    update_pyproject_toml(directory, updates_log)
    update_pre_commit_config(directory, updates_log)
    update_requirements_dev(directory, updates_log)

    for file, updates in updates_log.items():
        print(f"Updates in {file}:")
        for package, old_version, new_version in updates:
            print(f" - {package}: {old_version} -> {new_version}")


if __name__ == "__main__":
    main()
