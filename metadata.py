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
        },
        'whitelisted_ips': [],
        'scrape_configs': [
            # {
            #    "name": "node",
            #    "targets": ["127.0.0.1:9100"],
            # }
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
