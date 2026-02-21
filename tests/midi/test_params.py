from midi.params import ParamMap, ParamDef


def test_param_map_lookup():
    pm = ParamMap()
    p = pm.get("voice_mode")
    assert p is not None
    assert p.name == "voice_mode"
    assert p.min_val == 0
    assert p.max_val == 127


def test_param_map_list_all():
    pm = ParamMap()
    params = pm.list_all()
    assert len(params) > 0
    assert all(isinstance(p, ParamDef) for p in params)


def test_param_map_build_message():
    pm = ParamMap()
    p = pm.get("voice_mode")
    msg = p.build_message(channel=1, value=63)
    assert isinstance(msg, list)
    assert len(msg) > 0


def test_param_map_clamps_value():
    pm = ParamMap()
    p = pm.get("voice_mode")
    msg_low = p.build_message(channel=1, value=-10)
    msg_high = p.build_message(channel=1, value=999)
    assert msg_low is not None
    assert msg_high is not None
