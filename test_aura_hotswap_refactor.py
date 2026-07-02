from aura_hotswap_refactor import classify_hotswap_safety_from_sources


def test_simple_function_body_change_is_hotswap_safe():
    before = "def answer():\n    return 1\n"
    after = "def answer():\n    return 2\n"

    report = classify_hotswap_safety_from_sources(before, after)

    assert report.classification == "hotswap_safe"


def test_public_function_signature_change_requires_refactor():
    before = "def answer():\n    return 1\n"
    after = "def answer(value):\n    return value\n"

    report = classify_hotswap_safety_from_sources(before, after)

    assert report.classification == "reload_requires_refactor"
    assert "answer" in report.changed_public_symbols


def test_class_base_change_requires_refactor():
    before = "class Base:\n    pass\n\nclass Demo(Base):\n    pass\n"
    after = "class Base:\n    pass\n\nclass Other:\n    pass\n\nclass Demo(Other):\n    pass\n"

    report = classify_hotswap_safety_from_sources(before, after)

    assert report.classification == "reload_requires_refactor"
    assert "Demo" in report.changed_class_signatures


def test_module_level_thread_start_requires_restart():
    before = "from threading import Thread\n"
    after = "from threading import Thread\nThread(target=lambda: None).start()\n"

    report = classify_hotswap_safety_from_sources(before, after)

    assert report.classification == "restart_required"


def test_syntax_failure_requires_restart():
    report = classify_hotswap_safety_from_sources("def ok():\n    return 1\n", "def nope(:\n")

    assert report.classification == "restart_required"
