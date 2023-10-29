import yaml
global node

# See https://web.archive.org/web/20170903201521/https://pyyaml.org/ticket/64#comment:5
class MyDumper(yaml.Dumper):
    def increase_indent(self, flow=False, indentless=False):
        return super(MyDumper, self).increase_indent(flow, False)


version = node.metadata.get('prometheus').get('version')
checksum = node.metadata.get('prometheus').get('checksum_sha256')
arch = node.metadata.get('prometheus').get('arch')
prom_dir = node.metadata.get('prometheus').get('directory')
prom_user = node.metadata.get('prometheus').get('user')
prom_group = node.metadata.get('prometheus').get('group')
prom_dir_version = f'/opt/prometheus-{version}.linux-{arch}'

groups = {
    prom_group: {},
}

users = {
    prom_user: {
        'gid': prom_group,
        'password_hash': '*',
        'needs': [
            f'group:{prom_group}',
        ],
        'shell': '/bin/bash',
    }
}

directories = {
    '/var/lib/prometheus': {
        'owner': f'{prom_user}',
        'group': f'{prom_group}',
        'needs': [
            f'user:{prom_user}',
        ],
    },
    '/etc/prometheus': {
        'owner': f'{prom_user}',
        'group': f'{prom_group}',
        'needs': [
            f'user:{prom_user}',
        ],
    }
}

downloads = {
    f'/tmp/prometheus-{version}.linux-{arch}.tar.gz': {
        'url': 'https://github.com/prometheus/prometheus/releases/download/'
               f'v{version}/prometheus-{version}.linux-{arch}.tar.gz',
        'sha256': checksum,
        'unless': f'test -f {prom_dir_version}/prometheus',
    },
}

actions = {
    'unpack_prometheus': {
        'command': f'tar xfvz /tmp/prometheus-{version}.linux-{arch}.tar.gz -C /opt',
        'needs': [
            f'download:/tmp/prometheus-{version}.linux-{arch}.tar.gz',
        ],
        'unless': f'test -d {prom_dir}',
    },
    'chown_prom_dir': {
        'command': f'chown -R {prom_user}:{prom_group} {prom_dir_version}',
        'needs': [
            'action:unpack_prometheus',
            f'symlink:{prom_dir}',
        ],
        'unless': f'test $(stat -c "%U:%G" {prom_dir_version}) = "{prom_user}:{prom_group}"'
    },
    'daemon_reload_prometheus': {
        'command': 'systemctl daemon-reload',
        'triggered': True,
    }
}

files = {
    '/etc/prometheus/prometheus.yml': {
        'source': 'etc/prometheus/prometheus.yml.jinja2',
        'content_type': 'jinja2',
        'context': {
            'http': node.metadata.get('prometheus').get('http'),
            'scrape_configs': node.metadata.get('prometheus').get('scrape_configs'),
            'additional_scrape_config': yaml.dump(
                    node.metadata.get('prometheus').get('additional_scrape_configs'),
                Dumper=MyDumper,
                default_flow_style=False
            ) if node.metadata.get('prometheus').get('additional_scrape_configs') else "",
        },
        'owner': prom_user,
        'group': prom_group,
        'needs': [
            'directory:/etc/prometheus',
        ],
        'triggers': [
            'svc_systemd:prometheus:reload',
        ],
    },
    '/etc/systemd/system/prometheus.service': {
        'source': 'etc/systemd/system/prometheus.service.jinja2',
        'content_type': 'jinja2',
        'context': {
            'prom_dir': prom_dir,
            'http': node.metadata.get('prometheus').get('http'),
        },
        'triggers': [
            'action:daemon_reload_prometheus',
        ]
    },
}

symlinks = {
    f'{prom_dir}': {
        'target': prom_dir_version,
        'needs': [
            'action:unpack_prometheus',
        ],
    },
}

svc_systemd = {
    "prometheus": {
        'running': True,
        'enabled': True,
        'needs': [
            f'symlink:{prom_dir}',
            f'file:/etc/systemd/system/prometheus.service',
            f'file:/etc/prometheus/prometheus.yml',
            f'action:unpack_prometheus',
        ],
    },
}
