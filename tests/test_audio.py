
def test_jackaudio(jackd_server):
    import datetime
    from pyltc.audio import pyjack_audio
    start_dt = datetime.datetime.now()
    aud = pyjack_audio.main(loop_time=10)
    h, m, s, f = aud.generator.frame.get_hmsf()
    t = datetime.time(hour=h.value, minute=m.value, second=s.value)
    dt = datetime.datetime.combine(start_dt.date(), t)
    td = dt - start_dt
    assert td.total_seconds() >= 10
