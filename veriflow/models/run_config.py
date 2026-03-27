from dataclasses import dataclass


@dataclass
class RunConfig:
    run_author: str
    objective: str
    tags: str
    main_change: str
    notes: str

    @classmethod
    def from_dict(cls, data: dict) -> "RunConfig":
        return cls(
            run_author=data.get("run_author", "") or "",
            objective=data.get("objective", "") or "",
            tags=data.get("tags", "") or "",
            main_change=data.get("main_change", "") or "",
            notes=data.get("notes", "") or "",
        )
