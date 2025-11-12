# ComfyUI Workflow Guide

## How to Create Custom Workflows with Full Control

You have **complete control** over the ComfyUI workflow. Here's how to design custom node graphs.

## Method 1: Design in ComfyUI Web Interface (Easiest)

### Step 1: Open ComfyUI

Access your RunPod ComfyUI instance:
```
https://jfmkqw45px5o3x-8188.proxy.runpod.net
```

### Step 2: Design Your Workflow

1. **Clear the default workflow** (Ctrl+A, Delete)
2. **Add nodes** (Right-click → Add Node)
   - Load Checkpoint
   - CLIP Text Encode (for prompts)
   - KSampler
   - VAE Decode
   - Save Image
   - **Custom nodes** (like NanoBananaHaas!)
3. **Connect nodes** by dragging from outputs to inputs
4. **Configure parameters** (resolution, steps, CFG, sampler, etc.)

### Step 3: Export Workflow as API Format

1. Click **"Save (API Format)"** button
2. This downloads a JSON file with your node graph
3. Open the JSON file - this is your workflow!

### Step 4: Use in Python

Copy the JSON into your script:

```python
MY_CUSTOM_WORKFLOW = {
    # Paste the exported JSON here
}

# Then use it
result = await client.execute_workflow(MY_CUSTOM_WORKFLOW)
```

## Method 2: Write JSON Directly (Advanced)

You can also hand-write workflows in JSON if you know the node structure.

### Basic Node Structure

```python
{
    "node_id": {
        "inputs": {
            "param_name": value_or_connection,
            "another_param": ["other_node_id", output_slot]
        },
        "class_type": "NodeClassName",
        "_meta": {
            "title": "Display Name"
        }
    }
}
```

### Connection Syntax

```python
# Static value
"width": 1920

# Connect to another node
"model": ["4", 0]  # Node 4, output slot 0
```

### Node Output Slots

Different nodes output different things:

```python
CheckpointLoaderSimple outputs:
  [0] = model
  [1] = clip
  [2] = vae

KSampler outputs:
  [0] = latent samples

VAEDecode outputs:
  [0] = images

CLIPTextEncode outputs:
  [0] = conditioning
```

## Adding Custom Nodes (Like NanoBananaHaas)

### Step 1: Install Custom Node in RunPod

In your RunPod web terminal:

```bash
cd /workspace/ComfyUI/custom_nodes
git clone https://github.com/username/ComfyUI-NanoBananaHaas.git
cd ComfyUI-NanoBananaHaas
pip install -r requirements.txt
```

Then restart ComfyUI:
```bash
cd /workspace/ComfyUI
python main.py --listen 0.0.0.0 --port 8188
```

### Step 2: Find Node Class Name

Check the custom node's documentation or code to find the class name.

For example:
- `NanoBananaHaasProcessor`
- `BananaStyleTransfer`
- etc.

### Step 3: Add to Workflow

Design in ComfyUI UI (easiest), or add manually:

```python
CUSTOM_WORKFLOW = {
    # ... other nodes ...

    "10": {
        "inputs": {
            "image": ["8", 0],  # From VAE decode
            "strength": 0.8,
            "style": "banana_classic"
        },
        "class_type": "NanoBananaHaasProcessor",
        "_meta": {
            "title": "Banana Style"
        }
    },

    "11": {
        "inputs": {
            "filename_prefix": "banana_hero",
            "images": ["10", 0]  # From Banana processor
        },
        "class_type": "SaveImage",
        "_meta": {
            "title": "Save Banana Image"
        }
    }
}
```

## Discovering Available Nodes

### Check What's Installed

Run this script to see all available nodes:

```python
import aiohttp
import asyncio

async def get_nodes():
    url = "https://jfmkqw45px5o3x-8188.proxy.runpod.net/object_info"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()

            print("Available Nodes:")
            for node_name in sorted(data.keys()):
                print(f"  - {node_name}")

                # Show inputs for this node
                if "input" in data[node_name]:
                    inputs = data[node_name]["input"].get("required", {})
                    print(f"    Inputs: {list(inputs.keys())}")

asyncio.run(get_nodes())
```

This will show you:
- All installed nodes (including custom ones)
- What inputs each node accepts
- What values are valid for each input

## Example: Complex Workflow with Custom Nodes

Here's an example workflow that uses multiple custom processing steps:

```python
ADVANCED_WORKFLOW = {
    # Load model
    "1": {
        "inputs": {"ckpt_name": "v1-5-pruned-emaonly.ckpt"},
        "class_type": "CheckpointLoaderSimple"
    },

    # Positive prompt
    "2": {
        "inputs": {
            "text": "beautiful coral gradient background",
            "clip": ["1", 1]
        },
        "class_type": "CLIPTextEncode"
    },

    # Negative prompt
    "3": {
        "inputs": {
            "text": "blurry, low quality",
            "clip": ["1", 1]
        },
        "class_type": "CLIPTextEncode"
    },

    # Empty latent
    "4": {
        "inputs": {"width": 1920, "height": 1080, "batch_size": 1},
        "class_type": "EmptyLatentImage"
    },

    # Sample
    "5": {
        "inputs": {
            "seed": 42,
            "steps": 30,
            "cfg": 8.0,
            "sampler_name": "dpmpp_2m",
            "scheduler": "karras",
            "denoise": 1,
            "model": ["1", 0],
            "positive": ["2", 0],
            "negative": ["3", 0],
            "latent_image": ["4", 0]
        },
        "class_type": "KSampler"
    },

    # Decode
    "6": {
        "inputs": {
            "samples": ["5", 0],
            "vae": ["1", 2]
        },
        "class_type": "VAEDecode"
    },

    # *** CUSTOM NODE: Apply banana style ***
    "7": {
        "inputs": {
            "images": ["6", 0],
            "intensity": 0.75
        },
        "class_type": "NanoBananaHaasProcessor"
    },

    # *** CUSTOM NODE: Color correction ***
    "8": {
        "inputs": {
            "images": ["7", 0],
            "brightness": 1.1,
            "contrast": 1.2,
            "saturation": 1.3
        },
        "class_type": "ColorCorrect"
    },

    # Save final image
    "9": {
        "inputs": {
            "filename_prefix": "final_output",
            "images": ["8", 0]
        },
        "class_type": "SaveImage"
    }
}
```

## Tips for Workflow Design

1. **Start in ComfyUI UI**: Design visually first, then export
2. **Check node docs**: Each custom node has different inputs/outputs
3. **Test incrementally**: Add one custom node at a time
4. **Use `/object_info` API**: Query available nodes and their parameters
5. **Save workflow templates**: Keep reusable workflows in separate files

## Workflow Library

Create a library of reusable workflows:

```python
# workflows/basic_txt2img.json
# workflows/img2img_with_controlnet.json
# workflows/banana_style_hero.json
# workflows/upscale_4x.json
```

Load dynamically:

```python
import json

def load_workflow(name: str):
    with open(f"workflows/{name}.json") as f:
        return json.load(f)

workflow = load_workflow("banana_style_hero")
result = await client.execute_workflow(workflow)
```

## Next Steps

1. Open your RunPod ComfyUI web interface
2. Install NanoBananaHaas custom node (or whatever you want to use)
3. Design your workflow visually
4. Export as API format
5. Use in Python scripts
6. Profit! 🍌

---

**Remember**: You have full control. The workflow is just a JSON graph. You can modify any node, any connection, any parameter!
