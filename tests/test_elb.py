from citadel.models.loadbalance import ELBInstance


def test_loadbalancer(test_db):
    lb = ELBInstance.create('addr', 0, 'container_id', 'elb')
    assert lb is not None

    lb1 = ELBInstance.get_by_name('elb')
    assert len(lb1) == 1
    assert lb1[0].id == lb.id
