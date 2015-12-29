# coding: utf-8

from eru.config import NETWORK_PROVIDER

ipam = None

if NETWORK_PROVIDER == 'macvlan':
    from eru.ipam.macvlan import MacVLANIPAM
    ipam = MacVLANIPAM()
elif NETWORK_PROVIDER == 'calico':
    from eru.ipam.calico import CalicoIPAM
    ipam = CalicoIPAM()
else:
    raise ValueError('Network Provider must be either macvlan or calico')
