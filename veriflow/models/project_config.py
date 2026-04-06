from dataclasses import dataclass, field


@dataclass
class ProjectConfig:
    id_prefix: str
    project_name: str
    repo: str
    description: str
    semicolab: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "ProjectConfig":
        semicolab = data.get("semicolab", True)
        if isinstance(semicolab, str):
            semicolab = semicolab.strip().lower() not in ("false", "0", "no")
        return cls(
            id_prefix=data.get("id_prefix", "") or "",
            project_name=data.get("project_name", "") or "",
            repo=data.get("repo", "") or "",
            description=data.get("description", "") or "",
            semicolab=bool(semicolab),
        )
