# coding: utf-8

from eru.config import NETWORK_PROVIDER
from eru.ipam.macvlan import MacVLANIPAM
from eru.ipam.calico import CalicoIPAM

_providers = {
    'macvlan': MacVLANIPAM,
    'calico': CalicoIPAM,
}

ipam = _providers[NETWORK_PROVIDER]()
