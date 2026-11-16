#!/usr/bin/env python3
"""Apply Microsoft's compatible .NET 8 servicing assemblies to Runner 2.338.2.

The Dockerfile verifies the official NuGet archives before this script runs.
Keep the actual DLLs, dependency graph, package hashes and file versions aligned.
Fail on unexpected upstream versions instead of silently editing a new Runner.
"""
import base64
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile


PACKAGES = {
    'Microsoft.AspNetCore.WebUtilities': 'webutilities.nupkg',
    'Microsoft.Net.Http.Headers': 'headers.nupkg',
}
OLD_VERSION = '8.0.25'
VERSION = '8.0.34'


def patch(bin_dir, archives):
    packages = {}
    for name, archive in PACKAGES.items():
        raw = (archives / archive).read_bytes()
        with zipfile.ZipFile(archives / archive) as package:
            dll = package.read(f'lib/net8.0/{name}.dll')
            # AssemblyVersion stays 8.0.0.0 across compatible servicing releases.
            versions = re.findall(r'8\.0\.\d{4}\.\d+', dll.decode('utf-16-le', errors='ignore'))
            if len(set(versions)) != 1:
                raise ValueError(f'{name}: missing or ambiguous DLL file version')
            packages[name] = (dll, versions[0], base64.b64encode(hashlib.sha512(raw).digest()).decode())

    changed = set()
    for path in bin_dir.glob('*.deps.json'):
        data = json.loads(path.read_text())
        for name, (_, file_version, digest) in packages.items():
            old_key, new_key = f'{name}/{OLD_VERSION}', f'{name}/{VERSION}'
            keys = [key for key in data['libraries'] if key.startswith(name + '/')]
            if not keys:
                continue
            if keys != [old_key]:
                raise ValueError(f'{path.name}: unexpected upstream {name} version: {keys}')
            library = data['libraries'].pop(old_key)
            library.update(sha512='sha512-' + digest, path=f'{name.lower()}/{VERSION}',
                           hashPath=f'{name.lower()}.{VERSION}.nupkg.sha512')
            data['libraries'][new_key] = library
            for target in data['targets'].values():
                if old_key in target:
                    entry = target.pop(old_key)
                    for asset in entry.get('runtime', {}).values():
                        asset['fileVersion'] = file_version
                    target[new_key] = entry
                for entry in target.values():
                    dependencies = entry.get('dependencies', {})
                    if name in dependencies:
                        if dependencies[name] != OLD_VERSION:
                            raise ValueError(f'{path.name}: unexpected reference to {name}')
                        dependencies[name] = VERSION
            changed.add(name)
        path.write_text(json.dumps(data, indent=2) + '\n')
    if changed != set(PACKAGES):
        raise ValueError('Expected Runner servicing dependencies were not found')
    for name, (dll, _, _) in packages.items():
        target = bin_dir / f'{name}.dll'
        if not target.is_file():
            raise ValueError(f'Missing upstream assembly: {name}')
        target.write_bytes(dll)


if __name__ == '__main__':
    patch(Path(sys.argv[1]), Path(sys.argv[2]))
