import json
import os
import shutil
from pathlib import Path

import pytest

from bot.config import Business, BusinessProvider

CONFIGS = sorted(Path(__file__).resolve().parent.parent.joinpath("configs").glob("*.json"))
PLACEHOLDERS = dict(
    name="Иван",
    business="B",
    service="S",
    price="P",
    description="D",
    slot="Завтра 15:00",
    address="A",
    phone="+7",
    hours="H",
    text="T",
)


@pytest.mark.parametrize("path", CONFIGS, ids=lambda p: p.name)
def test_bundled_configs_are_valid(path):
    business = Business.from_dict(json.loads(path.read_text(encoding="utf-8")))
    for key in business.texts:
        business.text(key, **PLACEHOLDERS)  # no unknown placeholders


def test_provider_hot_reloads_and_survives_broken_edit(tmp_path):
    path = tmp_path / "biz.json"
    shutil.copy(CONFIGS[0], path)
    provider = BusinessProvider(path)

    data = json.loads(path.read_text(encoding="utf-8"))
    data["business_name"] = "Новое имя"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    os.utime(path, (1, 1))  # force a different mtime regardless of fs resolution
    assert provider.get().name == "Новое имя"

    path.write_text("{ broken json", encoding="utf-8")
    os.utime(path, (2, 2))
    assert provider.get().name == "Новое имя"
