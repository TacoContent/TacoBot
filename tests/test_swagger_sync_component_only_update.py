import pathlib
import shutil
import tempfile
import subprocess
import sys

SCRIPT = pathlib.Path('scripts/swagger_sync.py')
SWAGGER = pathlib.Path('.swagger.v1.yaml')
MODELS_DIR = pathlib.Path('bot/lib/models')


def test_component_only_update_triggers_write(monkeypatch):
    # Copy swagger & model file to temp dir to isolate
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)
        # Replicate minimal project structure required: scripts, swagger file, models dir
        (tmp / 'scripts').mkdir(parents=True)
        (tmp / 'bot/lib/models/openapi').mkdir(parents=True)

        shutil.copyfile(SCRIPT, tmp / 'scripts/swagger_sync.py')
        shutil.copyfile(SWAGGER, tmp / '.swagger.v1.yaml')
        # Copy the openapi decorator helper so the import path resolves
        shutil.copyfile(MODELS_DIR / 'openapi/openapi.py', tmp / 'bot/lib/models/openapi/openapi.py')

    # Pick a model file that exists (DiscordChannel) and add a new attribute to force component drift
        source_model = MODELS_DIR / 'DiscordChannel.py'
        content = source_model.read_text(encoding='utf-8')
        # Append a harmless comment to ensure timestamp change if description already modified
        if '# test drift' not in content:
            content = content + '\n# test drift'

        lines = content.splitlines()
        modified = []
        injected = False
        for line in lines:
            modified.append(line)
            if not injected and line.strip().startswith('def __init__'):
                # Insert after function signature; add a new attribute with annotation
                modified.append('        self.test_component_flag: bool = True  # added by test to trigger schema update')
                injected = True
        (tmp / 'bot/lib/models/DiscordChannel.py').write_text('\n'.join(modified), encoding='utf-8')

        # Run --check then --fix
        cmd_base = [sys.executable, 'scripts/swagger_sync.py', '--handlers-root', 'bot/lib/http/handlers', '--models-root', 'bot/lib/models', '--swagger-file', '.swagger.v1.yaml', '--coverage-report', 'coverage.json', '--coverage-format', 'json']
        # Handlers root may not exist in temp; create empty so script can proceed (will have zero handlers)
        (tmp / 'bot/lib/http/handlers').mkdir(parents=True, exist_ok=True)

        check = subprocess.run(cmd_base + ['--check'], cwd=tmp, capture_output=True, text=True)
        # return code may be 0 (no handler drift) even though components will be updated on fix.
        assert check.returncode in (0,1)

        before = (tmp / '.swagger.v1.yaml').read_text(encoding='utf-8')
        fix = subprocess.run(cmd_base + ['--fix'], cwd=tmp, capture_output=True, text=True)
        after = (tmp / '.swagger.v1.yaml').read_text(encoding='utf-8')

        # Should indicate swagger updated due to components change (component-only wording allowed)
        assert 'Swagger updated' in fix.stdout, fix.stdout + '\n' + fix.stderr
        assert before != after, 'Swagger file should change when only components drift.'

        # Ensure new attribute present in swagger output (component schema)
        assert 'test_component_flag' in after
