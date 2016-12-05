from datetime import datetime, timedelta

import pytest
import eventlet
import detox
from detox.proc import Resources

class TestResources:
    def test_getresources(self):
        l= []
        class Provider:
            def provide_abc(self):
                l.append(1)
                return 42
        resources = Resources(Provider())
        res, = resources.getresources("abc")
        assert res == 42
        assert len(l) == 1
        res, = resources.getresources("abc")
        assert len(l) == 1
        assert res == 42

    def test_getresources_param(self):
        class Provider:
            def provide_abc(self, param):
                return param
        resources = Resources(Provider())
        res, = resources.getresources("abc:123")
        return res == "123"

    def test_getresources_parallel(self):
        l= []
        queue = eventlet.Queue()
        class Provider:
            def provide_abc(self):
                l.append(1)
                return 42
        resources = Resources(Provider())
        pool = eventlet.GreenPool(2)
        pool.spawn(lambda: resources.getresources("abc"))
        pool.spawn(lambda: resources.getresources("abc"))
        pool.waitall()
        assert len(l) == 1

    def test_getresources_multi(self):
        l= []
        queue = eventlet.Queue()
        class Provider:
            def provide_abc(self):
                l.append(1)
                return 42
            def provide_def(self):
                l.append(1)
                return 23
        resources = Resources(Provider())
        a, d = resources.getresources("abc", "def")
        assert a == 42
        assert d == 23

class TestDetoxExample1:
    pytestmark = [pytest.mark.example1, pytest.mark.timeout(20)]

    def test_createsdist(self, detox):
        sdist, = detox.getresources("sdist")
        assert sdist.check()

    def test_getvenv(self, detox):
        venv, = detox.getresources("venv:py")
        assert venv.envconfig.envdir.check()
        venv2, = detox.getresources("venv:py")
        assert venv == venv2

    def test_test(self, detox):
        detox.runtests("py")

class TestDetoxExample2:
    pytestmark = [pytest.mark.example2, pytest.mark.timeout(20)]

    def test_test(self, detox):
        detox.runtests("py")

class TestCmdline:
    pytestmark = [pytest.mark.example1]
    @pytest.mark.timeout(20)
    def test_runtests(self, cmd):
        result = cmd.rundetox("-e", "py", "-v", "-v")
        result.stdout.fnmatch_lines([
            "py*getenv*",
            "py*create:*",
        ])


class TestProcLimitOption:
    pytestmark = [pytest.mark.example3]

    def test_runtestmulti(self):
        class MyConfig:
            class MyOption:
                proclimit = 4
            option = MyOption()

        l = []

        def MyGreenPool(**kw):
            l.append(kw)
            # Building a Detox object will already call GreenPool(),
            # so we have to let MyGreenPool being called twice before raise
            if len(l) == 2:
                raise ValueError

        from detox import proc
        setattr(proc, 'GreenPool', MyGreenPool)
        with pytest.raises(ValueError):
            d = proc.Detox(MyConfig())
            d.runtestsmulti(['env1', 'env2', 'env3'])  # Fake env list

        assert l[0] == {}  # When building Detox object
        assert l[1] == {'size': 4}  # When calling runtestsmulti

    @pytest.mark.timeout(30)
    def test_runtests(self, cmd):
        now1 = datetime.now()
        cmd.rundetox("-n", "1", "-epy1,py2,py3,py4,py5,py6,py7,py8")
        then1 = datetime.now()
        delta1 = then1 - now1
        assert delta1 >= timedelta(seconds=8)

        now4 = datetime.now()
        cmd.rundetox("-n", "4", "-epy1,py2,py3,py4,py5,py6,py7,py8")
        then4 = datetime.now()
        delta4 = then4 - now4
        assert delta4 >= timedelta(seconds=2)

        assert delta1 >= delta4, 'pool size=4 took much time than pool size=1'
