# Minecraft Item and Block Exporter Instructions

---



## Minecraft Model Definition Guide
Minecraft uses a flexible model system to define the shapes and appearances of blocks and items in the game. These
models are defined in JSON files using cuboid elements, each specified by its size, position, rotation, and textures. These files are stored in resource packs under the assets/<namespace>/models/ folder. 

### Core Model Structure
A model is a JSON object with several optional properties. The most important properties for defining the visual shape are parent, textures, and elements. 

```json
{
  "parent": "block/cube_all", // Optional: Inherit properties from another model
  "ambientocclusion": true,   // Optional: Whether to use ambient occlusion (default: true for blocks)
  "textures": {               // Maps texture variables to file locations
    "texture_variable_name": "namespace:block/texture_file_location",
    "particle": "namespace:block/texture_file_location"
  },
  "elements": [               // An array of cuboid elements
    // Element definitions go here
  ]
}
```
 
### Element Properties
Each object within the elements array is a single cuboid with the following properties: 

- from: The start corner of the cuboid, as a [x, y, z] coordinate array, in 1/16th block units (from [0, 0, 0] to [16, 16, 16]).
- to: The end corner of the cuboid, as a [x, y, z] coordinate array, also in 1/16th block units.
- rotation: (Optional) An object defining rotation around a specific axis.
  - origin: The center of rotation [x, y, z].
  - axis: The axis of rotation ("x", "y", or "z").
  - angle: The angle of rotation (e.g., -45.0 to 45.0).
  - rescale: (Optional) Set to true to rescale the element's faces to fit the bounding box after rotation.
- faces: An object mapping directions to face properties ("down", "up", "north", "south", "west", "east"). Each face object includes:
  - uv: (Optional) The texture area [u1, v1, u2, v2] in 1/16th texture units.
  - texture: A reference to a texture variable defined in the root textures object (e.g., "#texture_variable_name").
  - cullface: (Optional) The face of an adjacent block that this face should be culled (hidden) against (e.g., "up").
  - tintindex: (Optional) An integer used for tinting the face with a color (e.g., grass color).
