# coding: utf-8

def get_ips_by_container(container):
    if not hasattr(container, 'info'):
        return []

    networks = container.info.get('NetworkSettings', {}).get('Networks', {})
    ips = [network.get('IPAddress', '') for network in networks.values()]
    return [ip for ip in ips if ip]
