from hotflow.taobao import TaobaoClient


def test_sign_generates_expected_hash():
    params = {
        "app_key": "123456",
        "method": "taobao.test",
        "timestamp": "2024-01-01 00:00:00",
        "format": "json",
    }
    secret = "abcdefg"
    expected_base = (
        secret
        + "app_key123456"
        + "formatjson"
        + "methodtaobao.test"
        + "timestamp2024-01-01 00:00:00"
        + secret
    )
    expected = __import__("hashlib").md5(expected_base.encode("utf-8")).hexdigest().upper()
    assert TaobaoClient.sign(params, secret) == expected
