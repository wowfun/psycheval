from psycheval.i18n import MESSAGES, SUPPORTED_LOCALES


def test_supported_locales_define_the_same_message_keys():
    assert set(MESSAGES) == set(SUPPORTED_LOCALES)
    for locale in SUPPORTED_LOCALES:
        assert MESSAGES[locale].keys() == MESSAGES["en"].keys(), locale
