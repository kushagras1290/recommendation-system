from __future__ import annotations

import os

import structlog

from app.core.config import get_settings
from app.ml.collaborative import CollaborativeFilteringModel
from app.ml.content_based import ContentBasedModel
from app.ml.popularity import PopularityModel
from app.ml.ranker import LGBMRanker

logger = structlog.get_logger(__name__)
settings = get_settings()


class ModelRegistry:
    """
    Singleton that owns all trained model instances.
    Loads persisted artifacts on startup if they exist.
    """

    def __init__(self) -> None:
        self.popularity = PopularityModel()
        self.content = ContentBasedModel()
        self.cf = CollaborativeFilteringModel()
        self.ranker = LGBMRanker()
        self._load_all()

    def _artifact_path(self, name: str) -> str:
        return os.path.join(settings.model_dir, f"{name}.pkl")

    def _load_all(self) -> None:
        for name, model in [
            ("popularity", self.popularity),
            ("content", self.content),
            ("cf", self.cf),
            ("ranker", self.ranker),
        ]:
            path = self._artifact_path(name)
            if os.path.exists(path):
                try:
                    model.load(path)
                except Exception as exc:
                    logger.warning("model_load_failed", name=name, error=str(exc))

    def save_all(self) -> None:
        os.makedirs(settings.model_dir, exist_ok=True)
        for name, model in [
            ("popularity", self.popularity),
            ("content", self.content),
            ("cf", self.cf),
            ("ranker", self.ranker),
        ]:
            model.save(self._artifact_path(name))

    def any_trained(self) -> bool:
        return self.popularity.is_trained()

    def status(self) -> dict[str, bool]:
        return {
            "popularity": self.popularity.is_trained(),
            "content_based": self.content.is_trained(),
            "collaborative_filtering": self.cf.is_trained(),
            "ranker": self.ranker.is_trained(),
        }


_registry: ModelRegistry | None = None


def get_registry() -> ModelRegistry:
    global _registry
    if _registry is None:
        _registry = ModelRegistry()
    return _registry
