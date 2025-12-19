import shutil
import base64
import io
import json
from pathlib import Path
from zipfile import ZipFile
from typing import Optional, Tuple, Dict

from PIL import Image
from .constants import ASSETS_DIR
from .logger import logger


class AssetExtractor:
    @staticmethod
    def get_asset_filename(item_id: str) -> str:
        """Converts item ID (e.g., minecraft:acacia_boat) to filename (minecraft_acacia_boat.png)."""
        return item_id.replace(":", "_") + ".png"

    @staticmethod
    def create_placeholder_asset(item_id: str) -> str:
        """Create a visible placeholder PNG for items without an extracted asset and return the filename."""
        filename = AssetExtractor.get_asset_filename(item_id)
        dest = ASSETS_DIR / filename
        if dest.exists():
            return filename
        try:
            img = Image.new("RGBA", (32, 32), (255, 0, 255, 255))
            img.save(dest)
            return filename
        except Exception as e:
            logger.error(f"Failed to create placeholder asset for {item_id}: {e}")
            return filename

    @staticmethod
    def extract_asset(zip_file: ZipFile, zip_path: str, item_id: str, source_jar: str, include_asset: bool = False, tint: Optional[Tuple[int, int, int]] = None, overwrite: bool = False) -> Tuple[Optional[str], Optional[str], Optional[int], Optional[int]]:
        """
        Extracts the asset from the zip file to the assets directory.
        If include_asset is True, also returns a base64-encoded string of the image data.
        Returns (filename, asset_b64, width, height) where values can be None on failure.
        """
        filename = AssetExtractor.get_asset_filename(item_id)
        destination_path = ASSETS_DIR / filename

        if destination_path.exists() and not overwrite:
            # If we need the base64 but it's not being returned because we're skipping,
            # we should still return the filename and base64 if requested.
            asset_b64 = None
            width, height = None, None
            if include_asset:
                try:
                    with open(destination_path, "rb") as f:
                        data = f.read()
                        asset_b64 = base64.b64encode(data).decode("ascii")
                        with Image.open(io.BytesIO(data)) as img:
                            width, height = img.size
                except Exception:
                    pass
            return filename, asset_b64, width, height

        try:
            with zip_file.open(zip_path) as source:
                data = source.read()

            # Load image to check size and apply tint if needed
            try:
                img = Image.open(io.BytesIO(data)).convert("RGBA")

                if tint:
                    r, g, b, a = img.split()
                    r = r.point(lambda p: int(p * tint[0] / 255))
                    g = g.point(lambda p: int(p * tint[1] / 255))
                    b = b.point(lambda p: int(p * tint[2] / 255))
                    img = Image.merge('RGBA', (r, g, b, a))

                    # Save tinted image back to bytes for writing
                    buffered = io.BytesIO()
                    img.save(buffered, format="PNG")
                    data = buffered.getvalue()

                width, height = img.size
            except Exception:
                width = None
                height = None

            # Save file to disk
            with open(destination_path, "wb") as target:
                target.write(data)

            asset_b64 = None
            if include_asset:
                asset_b64 = base64.b64encode(data).decode("ascii")

            return filename, asset_b64, width, height
        except Exception as e:
            logger.error(f"Failed to extract asset {zip_path} from {source_jar}: {e}")
            return None, None, None, None

    @staticmethod
    def render_model(zip_file: ZipFile, model_data: Dict, namespace: str, item_id: str, include_asset: bool = False, overwrite: bool = False, tint: Optional[Tuple[int, int, int]] = None) -> Tuple[Optional[str], Optional[str], Optional[int], Optional[int]]:
        """
        Experimental: Render a model from its JSON definition.
        """
        import math

        filename = AssetExtractor.get_asset_filename(item_id)
        destination_path = ASSETS_DIR / filename

        if destination_path.exists() and not overwrite:
            asset_b64 = None
            width, height = None, None
            if include_asset:
                try:
                    with open(destination_path, "rb") as f:
                        data = f.read()
                        asset_b64 = base64.b64encode(data).decode("ascii")
                        with Image.open(io.BytesIO(data)) as img:
                            width, height = img.size
                except Exception:
                    pass
            return filename, asset_b64, width, height

        if not model_data:
            return None, None, None, None

        # Helper to load model JSON
        def load_model_json(path, default_ns):
            if ":" in path:
                ns, p = path.split(":", 1)
            else:
                ns = default_ns
                p = path

            candidates = [
                f"assets/{ns}/models/{p}.json",
                f"assets/{ns}/models/item/{p}.json",
                f"assets/{ns}/models/block/{p}.json"
            ]

            for c in candidates:
                if c in zip_file.namelist():
                    with zip_file.open(c) as f:
                        return json.load(f), ns
            return None, None

        # Helper to resolve model inheritance
        def resolve_model(data, current_ns):
            if "parent" in data:
                parent_path = data["parent"]
                if ":" in parent_path:
                    p_ns, p_path = parent_path.split(":", 1)
                else:
                    p_ns = "minecraft"
                    p_path = parent_path

                parent_file_path = f"assets/{p_ns}/models/{p_path}.json"
                try:
                    if parent_file_path in zip_file.namelist():
                        with zip_file.open(parent_file_path) as f:
                            parent_data = json.load(f)
                            resolved_parent = resolve_model(parent_data, p_ns)

                            merged_textures = resolved_parent.get("textures", {}).copy()
                            merged_textures.update(data.get("textures", {}))

                            merged_elements = data.get("elements", resolved_parent.get("elements", []))

                            return {
                                "textures": merged_textures,
                                "elements": merged_elements
                            }
                except Exception as e:
                    logger.warning(f"Failed to resolve parent {parent_path}: {e}")

            return {
                "textures": data.get("textures", {}),
                "elements": data.get("elements", [])
            }

        # Helper to render a resolved model
        def render_resolved_model(full_model):
            if not full_model:
                return [], []

            elements = full_model.get("elements", [])
            is_flat_item = False

            # Handle item/generated (no elements, just textures)
            if not elements and "textures" in full_model:
                # Check for layer0
                layer0 = full_model["textures"].get("layer0")
                if layer0:
                    is_flat_item = True

            if not elements and not is_flat_item:
                return [], []

            # Canvas setup
            w, h = 64, 64

            # Texture cache
            texture_cache = {}
            texture_defs = full_model.get("textures", {})
            animated_textures = {}

            def get_texture(tex_ref):
                if not tex_ref: return None
                while tex_ref.startswith("#"):
                    tex_ref = texture_defs.get(tex_ref[1:])
                    if not tex_ref: return None

                if tex_ref in texture_cache:
                    return texture_cache[tex_ref]

                if ":" in tex_ref:
                    ns, path = tex_ref.split(":", 1)
                else:
                    ns = namespace
                    path = tex_ref

                possible_paths = [
                    f"assets/{ns}/textures/{path}.png",
                    f"assets/{ns}/textures/{path}",
                ]

                for p in possible_paths:
                    try:
                        if p in zip_file.namelist():
                            with zip_file.open(p) as f:
                                raw_data = f.read()
                                tex = Image.open(io.BytesIO(raw_data)).convert("RGBA")
                                texture_cache[tex_ref] = tex

                                mcmeta_path = p + ".mcmeta"
                                if mcmeta_path in zip_file.namelist():
                                    try:
                                        with zip_file.open(mcmeta_path) as mf:
                                            mcmeta = json.load(mf)
                                            if "animation" in mcmeta:
                                                animated_textures[tex_ref] = (mcmeta, raw_data)
                                    except Exception:
                                        pass

                                return tex
                    except Exception:
                        continue
                return None

            used_textures = set()
            if is_flat_item:
                used_textures.add(full_model["textures"]["layer0"])
            else:
                for el in full_model.get("elements", []):
                    for face_data in el.get("faces", {}).values():
                        if "texture" in face_data:
                            used_textures.add(face_data["texture"])

            for tex_ref in used_textures:
                get_texture(tex_ref)

            is_animated = len(animated_textures) > 0

            frames = []
            durations = []

            if is_animated:
                primary_anim_ref = next(iter(animated_textures))
                mcmeta, raw_data = animated_textures[primary_anim_ref]

                animation_data = mcmeta.get("animation", {})
                frametime = animation_data.get("frametime", 1)

                raw_img = Image.open(io.BytesIO(raw_data))
                w_tex, h_tex = raw_img.size

                num_frames_total = h_tex // w_tex
                frames_order = animation_data.get("frames", list(range(num_frames_total)))

                for i in frames_order:
                    frame_index = i
                    frame_duration = frametime

                    if isinstance(i, dict):
                        frame_index = i.get("index", 0)
                        frame_duration = i.get("time", frametime)

                    if frame_index >= num_frames_total:
                        continue

                    durations.append(frame_duration * 50)

                    frame_texture_cache = {}
                    for tex_ref, (meta, data) in animated_textures.items():
                        img = Image.open(io.BytesIO(data)).convert("RGBA")
                        fw, fh = img.size
                        fsize = fw
                        local_frames = fh // fw
                        local_index = frame_index % local_frames
                        box = (0, local_index * fsize, fsize, (local_index + 1) * fsize)
                        frame_tex = img.crop(box)
                        frame_texture_cache[tex_ref] = frame_tex

                    frames.append(frame_texture_cache)
            else:
                frames.append({})
                durations.append(0)

            iso_scale = 2.0

            def project(x, y, z):
                cx, cy, cz = x - 8, y - 8, z - 8
                sx = (cx - cz) * 0.866 * iso_scale + w/2
                sy = (cx + cz) * 0.5 * iso_scale - cy * iso_scale + h/2
                return sx, sy

            def rotate_point(point, origin, axis, angle):
                px, py, pz = point
                ox, oy, oz = origin
                px -= ox
                py -= oy
                pz -= oz
                rad = math.radians(angle)
                c = math.cos(rad)
                s = math.sin(rad)
                if axis == "x":
                    new_y = py * c - pz * s
                    new_z = py * s + pz * c
                    py = new_y
                    pz = new_z
                elif axis == "y":
                    new_x = px * c - pz * s
                    new_z = px * s + pz * c
                    px = new_x
                    pz = new_z
                elif axis == "z":
                    new_x = px * c - py * s
                    new_y = px * s + py * c
                    px = new_x
                    py = new_y
                px += ox
                py += oy
                pz += oz
                return (px, py, pz)

            global_rotation_y = 0

            # Rotation Fixes
            # Rotate stairs and lectern by -90 degrees
            ROTATION_NEGATIVE_90_FIX_ITEMS = [
                "stairs", "stair", "minecraft:lectern", "heavy_core"
            ]
            if any(x in item_id for x in ROTATION_NEGATIVE_90_FIX_ITEMS):
                global_rotation_y = -90

            ROTATION_POSITIVE_90_FIX_ITEMS = [
                "minecraft:blast_furnace", "minecraft:dropper", "minecraft:dispenser",
                "minecraft:furnace", "minecraft:observer", "minecraft:smoker", "minecraft:vault"
            ]
            if item_id in ROTATION_POSITIVE_90_FIX_ITEMS:
                global_rotation_y = 90

            rendered_frames = []

            for frame_idx, frame_tex_cache in enumerate(frames):
                img = Image.new("RGBA", (w, h), (0, 0, 0, 0))

                def get_frame_texture(tex_ref):
                    resolved_ref = tex_ref
                    while resolved_ref.startswith("#"):
                        resolved_ref = texture_defs.get(resolved_ref[1:])
                        if not resolved_ref: return None
                    if resolved_ref in frame_tex_cache:
                        return frame_tex_cache[resolved_ref]
                    return get_texture(tex_ref)

                if is_flat_item:
                    tex_ref = full_model["textures"]["layer0"]
                    tex = get_frame_texture(tex_ref)
                    if tex:
                        # Apply Tint for Flat Items (Layer 0)
                        if tint:
                            r, g, b, a = tex.split()
                            r = r.point(lambda p: int(p * tint[0] / 255))
                            g = g.point(lambda p: int(p * tint[1] / 255))
                            b = b.point(lambda p: int(p * tint[2] / 255))
                            tex = Image.merge("RGBA", (r, g, b, a))

                        tex = tex.resize((w, h), Image.NEAREST)
                        img.paste(tex, (0, 0))
                    rendered_frames.append(img)
                    continue

                elements = full_model.get("elements", [])
                faces_to_draw = []

                for el in elements:
                    efrom = el["from"]
                    eto = el["to"]
                    efaces = el.get("faces", {})
                    x1, y1, z1 = efrom
                    x2, y2, z2 = eto
                    element_faces = []

                    if "up" in efaces:
                        element_faces.append({
                            "face": "up",
                            "corners": [(x1, y2, z1), (x2, y2, z1), (x2, y2, z2), (x1, y2, z2)],
                            "center": ((x1+x2)/2, y2, (z1+z2)/2),
                            "data": efaces["up"]
                        })
                    if "down" in efaces:
                        element_faces.append({
                            "face": "down",
                            "corners": [(x1, y1, z2), (x2, y1, z2), (x2, y1, z1), (x1, y1, z1)],
                            "center": ((x1+x2)/2, y1, (z1+z2)/2),
                            "data": efaces["down"]
                        })
                    if "north" in efaces:
                        element_faces.append({
                            "face": "north",
                            "corners": [(x2, y2, z1), (x1, y2, z1), (x1, y1, z1), (x2, y1, z1)],
                            "center": ((x1+x2)/2, (y1+y2)/2, z1),
                            "data": efaces["north"]
                        })
                    if "south" in efaces:
                        element_faces.append({
                            "face": "south",
                            "corners": [(x1, y2, z2), (x2, y2, z2), (x2, y1, z2), (x1, y1, z2)],
                            "center": ((x1+x2)/2, (y1+y2)/2, z2),
                            "data": efaces["south"]
                        })
                    if "west" in efaces:
                        element_faces.append({
                            "face": "west",
                            "corners": [(x1, y2, z1), (x1, y2, z2), (x1, y1, z2), (x1, y1, z1)],
                            "center": (x1, (y1+y2)/2, (z1+z2)/2),
                            "data": efaces["west"]
                        })
                    if "east" in efaces:
                        element_faces.append({
                            "face": "east",
                            "corners": [(x2, y2, z2), (x2, y2, z1), (x2, y1, z1), (x2, y1, z2)],
                            "center": (x2, (y1+y2)/2, (z1+z2)/2),
                            "data": efaces["east"]
                        })

                    rot = el.get("rotation")
                    if rot:
                        origin = rot.get("origin", [8, 8, 8])
                        axis = rot.get("axis", "y")
                        angle = rot.get("angle", 0)
                        for face in element_faces:
                            face["corners"] = [rotate_point(c, origin, axis, angle) for c in face["corners"]]
                            face["center"] = rotate_point(face["center"], origin, axis, angle)

                    current_global_rotation = global_rotation_y
                    if item_id == "minecraft:lectern" and efrom[1] > 0:
                        current_global_rotation += 180

                    if current_global_rotation != 0:
                        origin = [8, 8, 8]
                        axis = "y"
                        angle = current_global_rotation
                        for face in element_faces:
                            face["corners"] = [rotate_point(c, origin, axis, angle) for c in face["corners"]]
                            face["center"] = rotate_point(face["center"], origin, axis, angle)

                    faces_to_draw.extend(element_faces)

                faces_to_draw.sort(key=lambda f: f["center"][0] + f["center"][1] + f["center"][2])

                for face in faces_to_draw:
                    tex_ref = face["data"].get("texture")
                    tex = get_frame_texture(tex_ref)
                    if not tex: continue

                    # Apply Tint if tintindex is present
                    if "tintindex" in face["data"] and tint:
                        r, g, b, a = tex.split()
                        r = r.point(lambda p: int(p * tint[0] / 255))
                        g = g.point(lambda p: int(p * tint[1] / 255))
                        b = b.point(lambda p: int(p * tint[2] / 255))
                        tex = Image.merge("RGBA", (r, g, b, a))

                    uv = face["data"].get("uv", [0, 0, 16, 16])
                    tw, th = tex.size
                    u1, v1, u2, v2 = uv
                    u1 = u1 * tw / 16
                    v1 = v1 * th / 16
                    u2 = u2 * tw / 16
                    v2 = v2 * th / 16

                    crop_box = (min(u1, u2), min(v1, v2), max(u1, u2), max(v1, v2))
                    face_tex = tex.crop(crop_box)

                    quad = [project(*c) for c in face["corners"]]
                    p0 = quad[0]
                    p1 = quad[1]
                    p3 = quad[3]

                    fw, fh = face_tex.size
                    if fw == 0 or fh == 0: continue

                    x0, y0 = p0
                    x1, y1 = p1
                    x3, y3 = p3

                    a = (x1 - x0) / fw
                    b = (x3 - x0) / fh
                    c = x0
                    d = (y1 - y0) / fw
                    e = (y3 - y0) / fh
                    f = y0

                    det = a*e - b*d
                    if det == 0: continue

                    ia = e / det
                    ib = -b / det
                    ic = (b*f - c*e) / det
                    id = -d / det
                    ie = a / det
                    if_val = (c*d - a*f) / det

                    xs = [p[0] for p in quad]
                    ys = [p[1] for p in quad]
                    minx, maxx = min(xs), max(xs)
                    miny, maxy = min(ys), max(ys)

                    bw = int(maxx - minx) + 1
                    bh = int(maxy - miny) + 1

                    nic = ia*minx + ib*miny + ic
                    nif = id*minx + ie*miny + if_val

                    transformed_face = face_tex.transform(
                        (bw, bh),
                        Image.AFFINE,
                        (ia, ib, nic, id, ie, nif),
                        resample=Image.NEAREST
                    )

                    img.paste(transformed_face, (int(minx), int(miny)), transformed_face)

                rendered_frames.append(img)

            return rendered_frames, durations

        # Main Logic
        all_frames = []
        all_durations = []

        overrides = model_data.get("overrides", [])
        # Check for animation predicates (angle, time)
        anim_overrides = [o for o in overrides if any(k in o["predicate"] for k in ["angle", "time"])]

        if anim_overrides:
            # Sort by predicate value
            def get_predicate_value(o):
                p = o["predicate"]
                return p.get("angle", p.get("time", 0))

            anim_overrides.sort(key=get_predicate_value)

            # Render each frame
            for o in anim_overrides:
                model_path = o["model"]
                sub_model_data, sub_ns = load_model_json(model_path, namespace)
                if sub_model_data:
                    sub_full_model = resolve_model(sub_model_data, sub_ns)
                    frames, sub_durations = render_resolved_model(sub_full_model)
                    if frames:
                        all_frames.append(frames[0])  # Take first frame of sub-model
                        # Use sub-model duration if provided, otherwise default to 50 ms (20 FPS)
                        if sub_durations and sub_durations[0] and sub_durations[0] > 0:
                            all_durations.append(sub_durations[0])
                        else:
                            all_durations.append(50)  # 50 ms per frame -> 20 FPS
        else:
            # Standard rendering
            full_model = resolve_model(model_data, namespace)
            all_frames, all_durations = render_resolved_model(full_model)

        # Save output
        if not all_frames:
            return None, None, None, None

        is_animated = len(all_frames) > 1
        w, h = all_frames[0].size

        if is_animated:
            filename = filename.replace(".png", ".webp")
            destination_path = ASSETS_DIR / filename

            output = io.BytesIO()
            all_frames[0].save(
                output,
                format="WEBP",
                save_all=True,
                append_images=all_frames[1:],
                duration=all_durations,
                loop=0,
                background=(0,0,0,0)
            )
            data = output.getvalue()
            with open(destination_path, "wb") as f:
                f.write(data)

            asset_b64 = None
            if include_asset:
                asset_b64 = base64.b64encode(data).decode("ascii")

            return filename, asset_b64, w, h
        else:
            img = all_frames[0]
            img.save(destination_path)

            asset_b64 = None
            if include_asset:
                with open(destination_path, "rb") as f:
                    asset_b64 = base64.b64encode(f.read()).decode("ascii")

            return filename, asset_b64, w, h



    @staticmethod
    def render_animated_sprite(item_id: str, texture_data: bytes, mcmeta: Dict, source_jar: str, include_asset: bool = False, overwrite: bool = False) -> Tuple[Optional[str], Optional[str], Optional[int], Optional[int]]:
        """
        Renders an animated GIF from a sprite sheet and mcmeta.
        """
        filename = AssetExtractor.get_asset_filename(item_id).replace(".png", ".gif")
        destination_path = ASSETS_DIR / filename

        if destination_path.exists() and not overwrite:
            asset_b64 = None
            width, height = None, None
            if include_asset:
                try:
                    with open(destination_path, "rb") as f:
                        data = f.read()
                        asset_b64 = base64.b64encode(data).decode("ascii")
                        with Image.open(io.BytesIO(data)) as img:
                            width, height = img.size
                except Exception:
                    pass
            return filename, asset_b64, width, height

        try:
            img = Image.open(io.BytesIO(texture_data)).convert("RGBA")
            w, h = img.size

            # Determine frame size
            # Assume vertical strip if h > w and h % w == 0
            # Assume horizontal strip if w > h and w % h == 0
            # Default to square frames based on min dimension

            if h > w and h % w == 0:
                frame_size = w
                num_frames_total = h // w
                is_vertical = True
            elif w > h and w % h == 0:
                frame_size = h
                num_frames_total = w // h
                is_vertical = False
            else:
                # Fallback or single frame
                frame_size = min(w, h)
                num_frames_total = 1
                is_vertical = True

            animation_data = mcmeta.get("animation", {})
            frametime = animation_data.get("frametime", 1)
            frames_order = animation_data.get("frames", list(range(num_frames_total)))

            # Extract frames
            frames = []
            durations = []

            for i in frames_order:
                frame_index = i
                frame_duration = frametime

                if isinstance(i, dict):
                    frame_index = i.get("index", 0)
                    frame_duration = i.get("time", frametime)

                if frame_index >= num_frames_total:
                    continue

                if is_vertical:
                    box = (0, frame_index * frame_size, frame_size, (frame_index + 1) * frame_size)
                else:
                    box = (frame_index * frame_size, 0, (frame_index + 1) * frame_size, frame_size)

                frame = img.crop(box)

                # Scale to 32x32 for consistency with other assets
                if frame.size != (32, 32):
                     frame = frame.resize((32, 32), Image.NEAREST)

                frames.append(frame)
                durations.append(frame_duration * 50) # Convert ticks to ms

            if not frames:
                return None, None, None, None

            output = io.BytesIO()
            # Use the first frame duration as default, or list if supported/needed
            # Pillow supports list of durations
            frames[0].save(
                output,
                format="GIF",
                save_all=True,
                append_images=frames[1:],
                duration=durations,
                loop=0,
                disposal=2
            )

            data = output.getvalue()

            with open(destination_path, "wb") as f:
                f.write(data)

            asset_b64 = None
            width, height = frames[0].size

            if include_asset:
                asset_b64 = base64.b64encode(data).decode("ascii")

            return filename, asset_b64, width, height

        except Exception as e:
            logger.error(f"Failed to render animated sprite for {item_id}: {e}")
            return None, None, None, None

    @staticmethod
    def render_3d_block(item_id: str, textures: Dict[str, bytes], source_jar: str, include_asset: bool = False, block_type: str = "block", tint: Optional[Tuple[int, int, int]] = None, overwrite: bool = False) -> Tuple[Optional[str], Optional[str], Optional[int], Optional[int]]:
        """
        Renders a 3D isometric block from provided face textures.
        textures: Dict mapping face name ('up', 'left', 'right') to raw bytes.
        block_type: 'block', 'slab', 'stairs', 'wall', 'fence', 'fence_gate', 'cross'
        tint: Optional (r, g, b) tuple to tint the 'up' and 'overlay' textures (for grass).
        """
        filename = AssetExtractor.get_asset_filename(item_id)
        destination_path = ASSETS_DIR / filename

        if destination_path.exists() and not overwrite:
            # If we need the base64 but it's not being returned because we're skipping,
            # we should still return the filename and base64 if requested.
            asset_b64 = None
            width, height = None, None
            if include_asset:
                try:
                    with open(destination_path, "rb") as f:
                        data = f.read()
                        asset_b64 = base64.b64encode(data).decode("ascii")
                        with Image.open(io.BytesIO(data)) as img:
                            width, height = img.size
                except Exception:
                    pass
            return filename, asset_b64, width, height

        try:
            # Load textures (don't immediately force a fixed size)
            # For 'cross' type, we expect a single texture, usually passed as 'all' or 'cross' or just use the first one found
            if block_type in ["cross"]:
                # Use the first available texture
                tex_data = next(iter(textures.values()))
                raw_tex = Image.open(io.BytesIO(tex_data)).convert("RGBA")
                raw_up = raw_tex # Not used but keeps variables defined
                raw_left = raw_tex
                raw_right = raw_tex
            elif block_type in ["sprite_flat"]:
                # Sprite sheets: use only the FIRST frame from the sprite, resize that frame to
                # scale based on the smaller side (min width/height -> 32), bottom-center align,
                # and save the 32x32 canvas directly as the final asset (skip isometric renderer).
                tex_data = next(iter(textures.values()))
                raw_tex = Image.open(io.BytesIO(tex_data)).convert("RGBA")

                w, h = raw_tex.size
                # Detect frame orientation and crop the first frame (assume square frames stacked horizontally or vertically)
                if w > h and w % h == 0:
                    # Horizontal strip of square frames
                    frame_size = h
                elif h > w and h % w == 0:
                    # Vertical strip of square frames
                    frame_size = w
                else:
                    # Fallback: use the smallest dimension as frame size
                    frame_size = min(w, h)

                # Crop the first frame (top-left corner) for strip sprites, otherwise use full image
                # Detect strip sprites carefully. If it *looks* like a strip but
                # frames are not identical, treat it as a single tall/wide image.
                if w > h and w % h == 0:
                    frames = w // h
                    if frames > 1:
                        f1 = raw_tex.crop((0, 0, h, h))
                        # If first frame is mostly transparent, it's probably a single tall image; use full image
                        non_transparent = sum(1 for p in f1.getdata() if p[3] > 10)
                        if non_transparent / float(h * h) < 0.1:
                            frame = raw_tex
                        else:
                            frame = f1
                    else:
                        frame = raw_tex.crop((0, 0, h, h))
                elif h > w and h % w == 0:
                    frames = h // w
                    if frames > 1:
                        f1 = raw_tex.crop((0, 0, w, w))
                        non_transparent = sum(1 for p in f1.getdata() if p[3] > 10)
                        if non_transparent / float(w * w) < 0.1:
                            frame = raw_tex
                        else:
                            frame = f1
                    else:
                        frame = raw_tex.crop((0, 0, w, w))
                else:
                    # Single image - use the full texture as the frame
                    frame = raw_tex

                # Scale frame appropriately:
                # - If this was a cropped frame (square from a strip), scale so the small side becomes 32 (square -> 32x32)
                # - If this is the full image (single-frame), scale to *fit* within 32x32 (scale = 32 / max(width,height))
                if frame.size != raw_tex.size:
                    # cropped square frame (or strip crop) -> scale so small side becomes 32 (square -> 32)
                    min_side = min(frame.width, frame.height)
                    if min_side == 0:
                        scale = 1.0
                    else:
                        scale = 32.0 / float(min_side)
                else:
                    # single image: scale to fit within 32x32
                    max_side = max(frame.width, frame.height)
                    if max_side == 0:
                        scale = 1.0
                    else:
                        scale = 32.0 / float(max_side)

                new_w = max(1, int(round(frame.width * scale)))
                new_h = max(1, int(round(frame.height * scale)))

                frame_resized = frame.resize((new_w, new_h), resample=Image.LANCZOS)

                # Place the resized frame on a 32x32 canvas and align it bottom-center
                canvas32 = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
                offset_x = (32 - new_w) // 2
                offset_y = 32 - new_h
                canvas32.paste(frame_resized, (offset_x, offset_y), frame_resized)

                # Save the canvas directly as the output asset and return early
                try:
                    with open(destination_path, "wb") as target:
                        import io as _io
                        buf = _io.BytesIO()
                        canvas32.save(buf, format="PNG")
                        data = buf.getvalue()
                        target.write(data)

                    asset_b64 = None
                    if include_asset:
                        import base64 as _base64
                        asset_b64 = _base64.b64encode(data).decode("ascii")

                    return filename, asset_b64, 32, 32
                except Exception as e:
                    logger.error(f"Failed to write sprite_flat asset for {item_id}: {e}")
                    # Fallthrough to normal rendering as a fallback
                    raw_up = canvas32
                    raw_left = canvas32
                    raw_right = canvas32
            elif block_type == "mob_head":
                # Initialize with dummy images, will be overwritten later
                dummy = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
                raw_up = dummy
                raw_left = dummy
                raw_right = dummy
            else:
                raw_up = Image.open(io.BytesIO(textures['up'])).convert("RGBA")
                raw_left = Image.open(io.BytesIO(textures['left'])).convert("RGBA")
                raw_right = Image.open(io.BytesIO(textures['right'])).convert("RGBA")

            # Special-case default tint for some block types BEFORE applying tints
            if block_type == 'conduit' and tint is None:
                # Subtle cyan tint for conduits
                tint = (160, 200, 255)

            # Apply tint if provided
            if tint:
                # Helper to apply tint
                def apply_tint(img, color):
                    """Blend the image toward the given color to create a visible tint effect."""
                    if img.mode != 'RGBA':
                        img = img.convert('RGBA')
                    # Create a solid color image and blend toward it
                    tint_img = Image.new('RGBA', img.size, color + (255,))
                    # Blend alpha >0.5 to favor the tint (value tuned empirically)
                    return Image.blend(img, tint_img, alpha=0.6)

                # Apply to faces we loaded (ensure conduits get full tinting)
                if 'up' in textures:
                    raw_up = apply_tint(raw_up, tint)
                if 'left' in textures:
                    raw_left = apply_tint(raw_left, tint)
                if 'right' in textures:
                    raw_right = apply_tint(raw_right, tint)

                # For grass block, side overlay might need tinting too, but we usually just get 'left'/'right' which are pre-composed or just side.
                # If the side texture is actually an overlay, we should tint it.
                # But usually 'grass_block_side' is the dirt+grass combo or just dirt.
                # If we are rendering a grass block, 'up' is the main one to tint.
                # If we have 'overlay' in textures, we might need to handle it, but find_block_textures usually resolves to up/left/right.
                # Let's assume for now only 'up' needs tinting for standard grass block top view.
                # Wait, in isometric view, we see Top, Left (South), Right (East).
                # Grass block top is tinted.
                # Grass block side has an overlay that is tinted.
                # If our texture extractor just grabbed 'grass_block_side.png', it's the dirt part.
                # The overlay is 'grass_block_side_overlay.png'.
                # If we want perfect grass, we need to compose them.
                # For now, let's just tint the Top face, as that's the most obvious one.
                pass

            # Decide output final size: prefer 64 when textures support >=64, then 32 when >=32, otherwise 16
            max_tex_side = max(raw_up.width, raw_up.height, raw_left.width, raw_left.height, raw_right.width, raw_right.height)
            if max_tex_side >= 64:
                final_size = 64
            elif max_tex_side >= 32:
                final_size = 32
            else:
                final_size = 16

            logger.debug(f"Rendering 3D block for {item_id}: final_size={final_size}")

            # Our internal renderer expects 16x16 face tiles and produces a 32x32 canvas.
            # So normalize textures to 16x16 for the drawing step.
            img_up = raw_up.resize((16, 16), resample=Image.LANCZOS)
            img_left = raw_left.resize((16, 16), resample=Image.LANCZOS)
            img_right = raw_right.resize((16, 16), resample=Image.LANCZOS)

            # Apply shading
            def apply_shading(img, factor):
                if img.mode == 'RGBA':
                    r, g, b, a = img.split()
                    r = r.point(lambda p: int(p * factor))
                    g = g.point(lambda p: int(p * factor))
                    b = b.point(lambda p: int(p * factor))
                    return Image.merge('RGBA', (r, g, b, a))
                else:
                    return img.point(lambda p: int(p * factor))

            img_left = apply_shading(img_left, 0.8)
            img_right = apply_shading(img_right, 0.6)

            canvas = Image.new("RGBA", (32, 32), (0, 0, 0, 0))

            def draw_cuboid(e_off, s_off, u_off, w, d, h):
                # e_off, s_off, u_off: Origin (East, South, Up)
                # w, d, h: Dimensions (East, South, Up)

                # Top Face (at u_off + h)
                # Texture: x=East, y=South
                y_shift = 16 - (u_off + h)
                for s in range(s_off, s_off + d):
                    for e in range(e_off, e_off + w):
                        # Texture coords
                        tex_x = e
                        tex_y = s
                        # Screen coords
                        tx = 16 + e - s
                        ty = (e + s) // 2 + y_shift
                        if 0 <= tx < 32 and 0 <= ty < 32:
                            p = img_up.getpixel((tex_x, tex_y))
                            if p[3] > 0:
                                canvas.putpixel((tx, ty), p)

                # Left Face (South Face, at s_off + d)
                # Texture: x=East, y=Down (inverted Up)
                # Shift for South position
                south_shift = 16 - (s_off + d)
                tx_shift = south_shift
                ty_shift = -south_shift // 2

                for u in range(u_off, u_off + h):
                    for e in range(e_off, e_off + w):
                        # Texture coords
                        tex_x = e
                        tex_y = 15 - u

                        # Screen coords (Standard Left Face)
                        tx_base = e
                        ty_base = 8 + tex_y + e // 2

                        tx = tx_base + tx_shift
                        ty = ty_base + ty_shift

                        if 0 <= tx < 32 and 0 <= ty < 32:
                            p = img_left.getpixel((tex_x, tex_y))
                            if p[3] > 0:
                                canvas.putpixel((tx, ty), p)

                # Right Face (East Face, at e_off + w)
                # Texture: x=Inv South, y=Down
                # Shift for East position
                east_shift = 16 - (e_off + w)
                tx_shift = -east_shift
                ty_shift = -east_shift // 2

                for u in range(u_off, u_off + h):
                    for s in range(s_off, s_off + d):
                        # Texture coords
                        tex_x = 15 - s
                        tex_y = 15 - u

                        # Screen coords (Standard Right Face)
                        tx_base = 16 + tex_x
                        ty_base = 8 + tex_y + (15 - tex_x) // 2

                        tx = tx_base + tx_shift
                        ty = ty_base + ty_shift

                        if 0 <= tx < 32 and 0 <= ty < 32:
                            p = img_right.getpixel((tex_x, tex_y))
                            if p[3] > 0:
                                canvas.putpixel((tx, ty), p)

            # Render based on type
            if block_type == "block":
                draw_cuboid(0, 0, 0, 16, 16, 16)
            elif block_type == "slab":
                draw_cuboid(0, 0, 0, 16, 16, 8)
            elif block_type == "stairs":
                # Bottom Slab
                draw_cuboid(0, 0, 0, 16, 16, 8)
                # Top Step (Back/North half - South=0..8)
                draw_cuboid(0, 0, 8, 16, 8, 8)
            elif block_type == "fence":
                # Two posts connected by bars
                # Improved Fence Geometry
                # Post 1: x=6..10, z=6..10 (Centered) - No, inventory is two posts.
                # Vanilla inventory: Two posts at x=4 and x=12 (approx), connected by rails.
                # Post 1: x=2..6, z=6..10
                draw_cuboid(2, 6, 0, 4, 4, 16)
                # Post 2: x=10..14, z=6..10
                draw_cuboid(10, 6, 0, 4, 4, 16)
                # Top Bar: x=6..10, z=7..9, y=12..14
                draw_cuboid(6, 7, 12, 4, 2, 3)
                # Bottom Bar: x=6..10, z=7..9, y=6..9
                draw_cuboid(6, 7, 6, 4, 2, 3)
                # Wait, the previous code was exactly this.
                # Maybe the user wants the posts to be thicker or spaced differently?
                # Let's try to match the vanilla icon more closely.
                # Vanilla icon posts look like they are at x=5 and x=11?
                # Let's try:
                # Post 1: x=3..7
                # Post 2: x=9..13
                # Bar: x=7..9
                # This is tighter.
                # Let's stick to the previous one but maybe check the bar height.
                # Top bar y=12..15 (3 high)
                # Bottom bar y=6..9 (3 high)
                # This seems fine.
                # Maybe the issue is the texture mapping?
                # Fence uses "texture" which maps to "all".
                # So posts and bars get the same texture.
                # This is correct for wood fences.
                pass # Keep existing for now, maybe tweak later if specific feedback.

            elif block_type == "cross":
                # Render two intersecting planes at 45 degrees (which aligns them with X and Z axes in iso view)
                # Plane 2 (Z-aligned, East Face)
                # X=8, Z=0..16
                for u in range(16): # Height
                    for s in range(16): # South/Z
                        # Texture coords: x=15-s (inverted for Right face logic), y=15-u
                        tex_x = 15 - s
                        tex_y = 15 - u

                        x = 8
                        z = s
                        y = u

                        tx = 16 + x - z
                        ty = (x + z) // 2 + (16 - y)

                        if 0 <= tx < 32 and 0 <= ty < 32:
                            p = img_right.getpixel((tex_x, tex_y))
                            if p[3] > 0:
                                canvas.putpixel((tx, ty), p)

                # Plane 1 (X-aligned, South Face)
                # Z=8, X=0..16
                for u in range(16): # Height
                    for e in range(16): # East/X
                        # Texture coords: x=e, y=15-u
                        tex_x = e
                        tex_y = 15 - u

                        x = e
                        z = 8
                        y = u

                        tx = 16 + x - z
                        ty = (x + z) // 2 + (16 - y)

                        if 0 <= tx < 32 and 0 <= ty < 32:
                            p = img_left.getpixel((tex_x, tex_y))
                            if p[3] > 0:
                                canvas.putpixel((tx, ty), p)

            elif block_type == "fence_gate":
                # Improved Fence Gate
                # Standard icon: Closed gate.
                # Two posts (thinner?) and a central plank.
                # Post 1: x=6..8, z=7..9, y=5..15?
                # Actually, fence gate inventory is usually just the gate part, no posts?
                # No, it has the side posts.
                # Let's try:
                # Post 1: x=2..6, z=7..9
                draw_cuboid(2, 7, 4, 4, 2, 12)
                # Post 2: x=10..14, z=7..9
                draw_cuboid(10, 7, 4, 4, 2, 12)
                # Bar: x=6..10, z=7..9, y=12..14
                draw_cuboid(6, 7, 12, 4, 2, 3)
                # Bar: x=6..10, z=7..9, y=6..9
                draw_cuboid(6, 7, 6, 4, 2, 3)
                # Central Plank?
                # Usually fence gate has a central vertical piece?
                # Let's just draw the horizontal bars connecting the posts.

            elif block_type == "wall":
                # Improved wall geometry to better match vanilla inventory icons
                # Left post: x=3..6, z=5..11 (slightly inset)
                draw_cuboid(3, 5, 0, 3, 6, 16)
                # Right post: x=10..13, z=5..11
                draw_cuboid(10, 5, 0, 3, 6, 16)
                # Central wall segment: x=6..10, z=6..10, height=14 (connects posts)
                draw_cuboid(6, 6, 0, 4, 4, 14)

            elif block_type == "scaffolding":
                # Scaffolding: four corner posts and horizontal crossbars
                # Corner posts (thin, tall)
                draw_cuboid(2, 2, 0, 2, 2, 16)
                draw_cuboid(12, 2, 0, 2, 2, 16)
                draw_cuboid(2, 12, 0, 2, 2, 16)
                draw_cuboid(12, 12, 0, 2, 2, 16)
                # Horizontal crossbars at multiple heights
                for y in (3, 7, 11):
                    draw_cuboid(2, 2, y, 12, 12, 1)
                    # Inner supports
                    draw_cuboid(5, 2, y, 6, 1, 1)
                    draw_cuboid(5, 12, y, 6, 1, 1)

            elif block_type == "conduit":
                # Conduit: small centered cube with subtle cyan tint if none provided
                # Centered 8x8x8 cube at x=4..12, z=4..12, y=4..12
                draw_cuboid(4, 4, 4, 8, 8, 8)
                # Add an outer frame/ring to give the 'ridges' visual
                draw_cuboid(3, 3, 3, 10, 10, 1)  # top rim
                draw_cuboid(3, 3, 12, 10, 10, 1)  # bottom rim
                # If a tint wasn't provided, apply a bluish tint to the 'up' face texture
                if tint is None:
                    tint = (160, 200, 255)
            elif block_type == "teleport_pad":
                # Teleport Pad (AllTheModium)
                # Slab-like, height 3
                draw_cuboid(0, 0, 0, 16, 16, 3)
            elif block_type == "trapdoor":
                # Flat block against side or bottom. Inventory is usually flat.
                draw_cuboid(0, 0, 0, 16, 16, 3)
            elif block_type == "pressure_plate":
                # Very thin slab
                draw_cuboid(1, 1, 0, 14, 14, 1)
            elif block_type == "button":
                # Small block
                draw_cuboid(5, 6, 6, 6, 4, 4)
            elif block_type == "carpet":
                # Thin layer
                draw_cuboid(0, 0, 0, 16, 16, 1)
            elif block_type == "pad":
                # Flat layer at the bottom, sides/top transparent
                draw_cuboid(0, 0, 0, 16, 16, 0)
            elif block_type == "sprite_flat":
                # Flat layer at the bottom, sides/top transparent
                # draw like 2d flat
                draw_cuboid(0, 0, 0, 16, 16, 0)
                # draw_cuboid(0, 7, 0, 16, 2, 16)?
            elif block_type == "snow":
                # Snow layer (height 2)
                draw_cuboid(0, 0, 0, 16, 16, 2)
            elif block_type == "pane":
                # Glass pane - cross or flat? Inventory is usually flat face.
                # Let's draw a thin sheet
                draw_cuboid(0, 7, 0, 16, 2, 16)
            elif block_type == "daylight_detector":
                # Slab-like
                draw_cuboid(0, 0, 0, 16, 16, 6)
            elif block_type == "hopper":
                # Funnel shape
                # Top rim (simplified as solid for now)
                draw_cuboid(0, 0, 10, 16, 16, 6)
                # Bottom spout
                draw_cuboid(6, 6, 0, 4, 4, 10)
            elif block_type == "cauldron":
                # Standard block size for now
                draw_cuboid(0, 0, 0, 16, 16, 16)
            elif block_type == "anvil":
                # Anvil Geometry
                # Base: x=2..14, z=2..14, y=0..4
                # Top/Bottom texture?
                # Let's assume standard orientation
                # Base (North-South): x=4..12, z=0..16, y=0..4?
                # Anvil base is wide on X or Z?
                # Base: 12x12?
                draw_cuboid(2, 2, 0, 12, 12, 4)
                # Neck: x=6..10, z=5..11, y=4..5
                draw_cuboid(6, 5, 4, 4, 6, 1)
                # Neck narrow: x=7..9, z=6..10, y=5..10
                draw_cuboid(7, 6, 5, 2, 4, 5)
                # Top: x=0..16, z=3..13, y=10..16
                draw_cuboid(0, 3, 10, 16, 10, 6)
            elif block_type == "chest":
                # Chest is 14x14x14 centered (simplified)
                draw_cuboid(1, 1, 0, 14, 14, 14)
            elif block_type == "lantern":
                # Lantern: x=5..11, z=5..11, y=0..7 + top
                draw_cuboid(5, 5, 0, 6, 6, 7)
                draw_cuboid(6, 6, 7, 4, 4, 2)
            elif block_type == "beacon":
                # Beacon: Inner glass + obsidian base
                # Base
                draw_cuboid(0, 0, 0, 16, 16, 3)
                # Glass
                draw_cuboid(2, 2, 3, 12, 12, 13)
            elif block_type == "dragon_egg":
                # Dragon Egg Geometry (7 layers)
                # Layer 7 (Bottom): 12x12, height 2
                draw_cuboid(2, 2, 0, 12, 12, 2)
                # Layer 6: 14x14, height 2
                draw_cuboid(1, 1, 2, 14, 14, 2)
                # Layer 5 (Middle/Widest): 16x16, height 3
                draw_cuboid(0, 0, 4, 16, 16, 3)
                # Layer 4: 14x14, height 3
                draw_cuboid(1, 1, 7, 14, 14, 3)
                # Layer 3: 12x12, height 2
                draw_cuboid(2, 2, 10, 12, 12, 2)
                # Layer 2: 8x8, height 2
                draw_cuboid(4, 4, 12, 8, 8, 2)
                # Layer 1 (Top): 6x6, height 2 (Button-like)
                draw_cuboid(5, 5, 14, 6, 6, 2)
            elif block_type == "mob_head":
                # Mob Head (8x8x8)
                # Expects 'skin' in textures
                if 'skin' in textures:
                    skin_data = textures['skin']
                    skin_img = Image.open(io.BytesIO(skin_data)).convert("RGBA")

                    # Crop faces from standard skin layout
                    # Top: (8, 0, 16, 8)
                    # Front: (8, 8, 16, 16)
                    # Right: (0, 8, 8, 16)

                    face_top = skin_img.crop((8, 0, 16, 8))
                    face_front = skin_img.crop((8, 8, 16, 16))
                    face_right = skin_img.crop((0, 8, 8, 16))

                    # Create 16x16 canvas for each face to align with draw_cuboid coordinate system
                    # Top: Centered at (4, 4)
                    new_up = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
                    new_up.paste(face_top, (4, 4))

                    # Left (Front): Centered horizontally (4), Bottom aligned (8) for y=0..8
                    new_left = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
                    new_left.paste(face_front, (4, 8))

                    # Right: Centered horizontally (4), Bottom aligned (8)
                    new_right = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
                    new_right.paste(face_right, (4, 8))

                    # Update images used by draw_cuboid
                    img_up = new_up
                    img_left = apply_shading(new_left, 0.8)
                    img_right = apply_shading(new_right, 0.6)

                    draw_cuboid(4, 4, 0, 8, 8, 8)
                else:
                    draw_cuboid(4, 4, 0, 8, 8, 8)
            elif block_type == "pad":
                # Pad: Draw only a thin top-facing plane (no sides/top transparency)
                # We draw the top face for a cuboid of height=1 (thin plane)
                y_shift = 16 - (0 + 1)
                for s in range(0, 1):
                    for e in range(0, 16):
                        tex_x = e
                        tex_y = s
                        tx = 16 + e - s
                        ty = (e + s) // 2 + y_shift
                        if 0 <= tx < 32 and 0 <= ty < 32:
                            p = img_up.getpixel((tex_x, tex_y))
                            if p[3] > 0:
                                canvas.putpixel((tx, ty), p)

            # If a smaller final size was requested, downscale; if larger (64) requested, upscale.
            if final_size == 16:
                final_canvas = canvas.resize((16, 16), resample=Image.LANCZOS)
            elif final_size == 64:
                final_canvas = canvas.resize((64, 64), resample=Image.LANCZOS)
            else:
                final_canvas = canvas

            # Save to disk
            final_canvas.save(destination_path)

            asset_b64 = None
            if include_asset:
                buffered = io.BytesIO()
                final_canvas.save(buffered, format="PNG")
                asset_b64 = base64.b64encode(buffered.getvalue()).decode("ascii")

            width, height = final_canvas.size

            return filename, asset_b64, width, height

        except Exception as e:
            logger.error(f"Failed to render 3D block for {item_id}: {e}")
            return None, None, None, None
