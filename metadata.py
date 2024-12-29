from bundlewrap.metadata import DoNotRunAgain
import re

global repo, node

defaults = {
    'prometheus': {
        'version': '2.43.0',
        'checksum_sha256': 'cfea92d07dfd9a9536d91dff6366d897f752b1068b9540b3e2669b0281bb8ebf',
        'arch': 'amd64',
        'user': 'prometheus',
        'group': 'prometheus',
        'directory': '/opt/prometheus',
        'http': {
            'addr': '127.0.0.1',
            'port': '9090',
            'external_url': '',
        },
        'whitelisted_ips': [],
        'scrape_configs': [
            # {
            #     'name': 'prometheus',
            #     'static_configs': [
            #         {
            #             'labels': {
            #                 'hostname': 'localhost',
            #             },
            #             'targets': ['127.0.0.1:9090'],
            #         },
            #     ],
            # },
        ],
        'additional_scrape_configs': [
            # {
            #     "job_name": "node",
            #     "static_configs": [
            #         {
            #             "targets": ["127.0.0.1:9100"],
            #         },
            #     ],
            # }
        ],
        'enable_remote-write': False,
    },
}


@metadata_reactor
def add_iptables(metadata):
    if not node.has_bundle("iptables"):
        raise DoNotRunAgain

    iptables_rules = {}
    for whitelistedIP in metadata.get('prometheus').get('whitelisted_ips'):
        iptables_rules += repo.libs.iptables.accept(). \
            input('main_interface'). \
            source(whitelistedIP). \
            tcp(). \
            dest_port(metadata.get('prometheus').get('http').get('port'))

    return iptables_rules

@metadata_reactor
def find_node_exporter_hosts_to_monitor(metadata):
    static_configs = []
    relabel_configs = []
    def get_targets(check_node):
        target_interfaces = []
        m = check_node.metadata
        port = m.get('prometheus_node_exporter').get('http', {}).get('port', 9100)

        interfaces = [m.get('main_interface'), ]
        interfaces += m.get('prometheus_node_exporter').get('additional_interfaces', [])

        for i in interfaces:
            ip = m.get('interfaces', {}).get(i, {}).get('ip_addresses', [])
            if len(ip) > 0:
                target_interfaces += [f'{ip[0]}:{port}', ]

        return target_interfaces

    for checked_node in sorted(repo.nodes, key=lambda x: x.name):
        if not checked_node.has_bundle('prometheus_node_exporter'):
            continue
        if checked_node.partial_metadata == {}:
            continue

        static_configs += [{
            'labels': {
                'hostname': checked_node.hostname,
                'os': checked_node.os,
                'instance': checked_node.name,
                'instance_ip': get_targets(checked_node)[0].split(':',1)[0],
            },
            'targets': get_targets(checked_node)
        }, ]

    return {
        'prometheus': {
            'scrape_configs': [
                {
                    'name': 'node_exporter',
                    'static_configs': static_configs,
                },
            ],
        },
    }
