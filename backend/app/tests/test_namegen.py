from app.services.region_engine import geocode, namegen


def test_generate_region_name_is_deterministic() -> None:
    label = "Arlington County, Virginia, United States"
    first = namegen.generate_region_name(label, geocode.THEME_RIVERLANDS)
    second = namegen.generate_region_name(label, geocode.THEME_RIVERLANDS)
    assert first == second


def test_generate_region_name_differs_by_theme() -> None:
    label = "Arlington County, Virginia, United States"
    names = {theme: namegen.generate_region_name(label, theme) for theme in namegen._WORD_BANKS}
    assert len(set(names.values())) == len(names)


def test_generate_region_name_differs_by_place() -> None:
    name_a = namegen.generate_region_name("Place A", geocode.THEME_RIVERLANDS)
    name_b = namegen.generate_region_name("Place B", geocode.THEME_RIVERLANDS)
    assert name_a != name_b


def test_generate_region_name_falls_back_for_unknown_theme() -> None:
    name = namegen.generate_region_name("Somewhere", "not-a-real-theme")
    assert isinstance(name, str) and len(name) > 0


def test_generate_region_name_avoids_awkward_word_repeats() -> None:
    for theme, bank in namegen._WORD_BANKS.items():
        for prefix in bank["prefixes"]:
            for noun in bank["nouns"]:
                noun_root = noun.lower().rstrip("s")
                assert noun_root not in prefix.lower(), f"'{prefix} {noun}' repeats a word root ({theme})"
