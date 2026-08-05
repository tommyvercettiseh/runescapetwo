from tools.vision_tester.template_capture import normalize_capture_name


def test_normalize_capture_name_adds_png_and_strips_directories() -> None:
    assert normalize_capture_name(" bank_button ") == "bank_button.png"
    assert normalize_capture_name("folder/bank.png") == "bank.png"
