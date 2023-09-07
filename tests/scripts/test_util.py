import pytest

from riskmatrix.scripts.util import lock_script


def test_lock_script(tmpdir):
    lock_dir_p = tmpdir.join('locks')
    lock_file_p = lock_dir_p.join('test_script.lock')
    assert not lock_dir_p.check()

    lock_dir = str(lock_dir_p)
    with lock_script(lock_dir, 'test_script') as lock_file:
        assert str(lock_file_p) == lock_file
        assert lock_dir_p.check(dir=True)
        assert lock_file_p.check(file=True)

    assert lock_dir_p.check(dir=True)
    assert not lock_file_p.check()


def test_lock_script_internal_exception(tmpdir):
    lock_dir_p = tmpdir.join('locks')
    lock_file_p = lock_dir_p.join('test_script.lock')
    assert not lock_dir_p.check()

    lock_dir = str(lock_dir_p)
    with pytest.raises(Exception, match=r'test_exc'):
        with lock_script(lock_dir, 'test_script') as lock_file:
            assert str(lock_file_p) == lock_file
            assert lock_dir_p.check(dir=True)
            assert lock_file_p.check(file=True)
            raise Exception('test_exc')

    assert lock_dir_p.check(dir=True)
    assert not lock_file_p.check()


def test_lock_script_locked(tmpdir, caplog):
    lock_dir_p = tmpdir.mkdir('locks')
    lock_file_p = lock_dir_p.join('test_script.lock').ensure(file=True)
    assert lock_dir_p.check(dir=True)
    assert lock_file_p.check(file=True)

    lock_dir = str(lock_dir_p)
    with pytest.raises(SystemExit):
        with lock_script(lock_dir, 'test_script'):
            pass

    assert len(caplog.record_tuples) == 1
    assert caplog.record_tuples[0][0] == 'test_script'
    assert 'Lock file is still present.' in caplog.record_tuples[0][2]
    assert 'active test_script process' in caplog.record_tuples[0][2]
