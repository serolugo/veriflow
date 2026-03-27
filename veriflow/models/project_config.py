from dataclasses import dataclass


@dataclass
class ProjectConfig:
    id_prefix: str
    project_name: str
    repo: str
    description: str

    @classmethod
    def from_dict(cls, data: dict) -> "ProjectConfig":
        return cls(
            id_prefix=data.get("id_prefix", "") or "",
            project_name=data.get("project_name", "") or "",
            repo=data.get("repo", "") or "",
            description=data.get("description", "") or "",
        )
