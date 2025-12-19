import zipfile, json
path='scripts/minecraft/jars/client-1.21.1-20240808.144430-extra.jar'
with zipfile.ZipFile(path) as z:
    candidate='assets/minecraft/models/block/heavy_core.json'
    if candidate in z.namelist():
        with z.open(candidate) as f:
            data=json.load(f)
        print('Found model:',candidate)
        print(json.dumps(data, indent=2))
    else:
        print('Model not found')
