import eru.views.deploy
import base
import json
import hashlib

from eru.models.group import Group
from eru.models.pod import Pod
from eru.models.host import Host, Cpu
from eru.models.container import Container
from eru.models.app import App, Version
import eru.queries.group as q_group
import eru.queries.pod as q_pod
import eru.queries.host as q_host


class TestDeployPrivate(base.TestCase):
    def test_create_one(self):
        group = q_group.create_group('g0')
        self.assertIsNotNone(group)
        pod = q_pod.create_pod('p0')
        self.assertIsNotNone(pod)
        host = q_host.create_host('p0', '0.0.1.1', 'h0', 'also-h0', 16, 1)
        self.assertIsNotNone(host)

        app = App('a0', '', 'deadbeef')
        self.db.session.add(app)
        self.db.session.flush()
        version = Version(app.id, hashlib.sha1('deadbeef').hexdigest())
        self.db.session.add(version)
        self.db.session.commit()

        x = q_group.assign_pod('g0', 'p0')
        self.assertTrue(x)
        x = q_host.assign_group('g0', '0.0.1.1')
        self.assertTrue(x)

        with self.app.test_client() as client:
            r = client.put('/deploy/create/g0/p0/a0', data=json.dumps({
                'ncpu': 1,
                'ncontainer': 1,
                'version': version.sha,
            }))
            self.assertEqual(201, r.status_code)

        used_cpus = Cpu.query.filter_by(used=1)
        self.assertEqual(1, used_cpus.count())

        cpu = used_cpus.first()
        self.assertEqual(host.id, cpu.hid)

        container = Container.query.filter(Container.id == cpu.cid).first()
        self.assertIsNotNone(container)

        self.assertEqual(host.id, container.hid)
        self.assertEqual(app.id, container.aid)
        self.assertEqual(version.id, container.vid)
