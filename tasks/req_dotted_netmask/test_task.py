from src import dotted_netmask, address_in_network, is_ipv4_address


def test_netmask_24():
    assert dotted_netmask(24) == "255.255.255.0"


def test_netmask_other():
    assert dotted_netmask(8) == "255.0.0.0"
    assert dotted_netmask(25) == "255.255.255.128"


def test_in_network():
    assert address_in_network("192.168.1.1", "192.168.1.0/24")
    assert not address_in_network("192.168.1.1", "192.168.100.0/24")


def test_is_ipv4():
    assert is_ipv4_address("8.8.8.8")
    assert not is_ipv4_address("localhost")
