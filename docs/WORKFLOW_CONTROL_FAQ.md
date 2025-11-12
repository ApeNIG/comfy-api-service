# ComfyUI Workflow Control FAQ

## Your Questions Answered

### Q1: Can we turn workflows on and off?

**Yes! Multiple ways:**

#### Method 1: Conditional Execution
```python
# Define multiple workflows
BASIC_WORKFLOW = {...}
ADVANCED_WORKFLOW = {...}

# Choose which to use
if user_wants_advanced:
    workflow = ADVANCED_WORKFLOW
else:
    workflow = BASIC_WORKFLOW

await client.execute_workflow(workflow)
```

#### Method 2: Feature Flags
```python
from workflow_builder import WorkflowBuilder

builder = WorkflowBuilder()
workflow = builder.build_advanced(
    prompt="your prompt",
    use_gemini=True,      # Turn on/off
    use_adetailer=False,  # Turn on/off
    use_upscaling=True    # Turn on/off
)
```

#### Method 3: Configuration-Based
```python
# User settings or environment config
WORKFLOW_CONFIG = {
    "gemini_enabled": os.getenv("ENABLE_GEMINI", "false") == "true",
    "adetailer_enabled": True,
    "upscaling_enabled": False
}

workflow = build_workflow_from_config(WORKFLOW_CONFIG)
```

### Q2: Can we add and remove nodes?

**Absolutely! Workflows are just Python dicts.**

#### Removing Nodes
```python
# Load existing workflow
workflow = load_my_workflow()

# Remove by node ID
del workflow["63"]  # Remove upscale node
del workflow["adetailer_node"]

# Remove by type
workflow = {
    k: v for k, v in workflow.items()
    if v.get("class_type") != "ADetailer"  # Remove all Adetailer nodes
}
```

#### Adding Nodes
```python
# Add new node
workflow["new_100"] = {
    "inputs": {
        "images": ["8", 0],  # Connect to previous node
        "param": "value"
    },
    "class_type": "MyNewNode"
}

# Update connections
workflow["9"]["inputs"]["images"] = ["new_100", 0]  # Route through new node
```

#### Modifying Connections
```python
# Change which node feeds into another
workflow["save_node"]["inputs"]["images"] = ["6", 0]  # Skip processing nodes

# Change parameters
workflow["ksampler"]["inputs"]["steps"] = 50  # More steps
workflow["ksampler"]["inputs"]["cfg"] = 8.5   # Higher CFG
```

## Practical Examples

### Example 1: User Preference System

```python
class UserWorkflowPreferences:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.preferences = self.load_preferences()

    def get_workflow(self, prompt: str) -> dict:
        """Build workflow based on user preferences."""
        builder = WorkflowBuilder()

        return builder.build_advanced(
            prompt=prompt,
            use_gemini=self.preferences.get("use_gemini", False),
            use_adetailer=self.preferences.get("use_face_enhancement", False),
            use_upscaling=self.preferences.get("use_upscaling", False)
        )

# Usage
user = UserWorkflowPreferences("user_123")
workflow = user.get_workflow("beautiful sunset")
result = await client.execute_workflow(workflow)
```

### Example 2: A/B Testing Different Workflows

```python
async def ab_test_workflows(prompt: str):
    """Test two workflow variations."""

    # Variant A: Simple, fast
    workflow_a = WorkflowBuilder().build_basic(
        prompt=prompt,
        steps=20  # Fast
    )

    # Variant B: Complex, high quality
    workflow_b = WorkflowBuilder().build_advanced(
        prompt=prompt,
        use_gemini=True,
        use_adetailer=True,
        use_upscaling=True
    )

    # Run both
    result_a = await client.execute_workflow(workflow_a)
    result_b = await client.execute_workflow(workflow_b)

    return {
        "variant_a": result_a,
        "variant_b": result_b
    }
```

### Example 3: Subscription Tier Workflows

```python
def get_workflow_for_tier(tier: str, prompt: str) -> dict:
    """Different features for different subscription tiers."""

    builder = WorkflowBuilder()

    if tier == "free":
        # Basic features only
        return builder.build_basic(prompt, steps=15)

    elif tier == "pro":
        # Add Gemini
        return builder.build_advanced(
            prompt,
            use_gemini=True,
            use_adetailer=False,
            use_upscaling=False
        )

    elif tier == "premium":
        # All features
        return builder.build_advanced(
            prompt,
            use_gemini=True,
            use_adetailer=True,
            use_upscaling=True
        )
```

### Example 4: API Endpoint with Feature Toggles

```python
from fastapi import FastAPI, Body
from pydantic import BaseModel

app = FastAPI()

class GenerationRequest(BaseModel):
    prompt: str
    enable_gemini: bool = False
    enable_face_enhancement: bool = False
    enable_upscaling: bool = False
    quality: str = "medium"  # low, medium, high

@app.post("/generate")
async def generate_image(request: GenerationRequest):
    """Generate image with user-controlled features."""

    builder = WorkflowBuilder()

    # Build workflow based on request
    workflow = builder.build_advanced(
        prompt=request.prompt,
        use_gemini=request.enable_gemini,
        use_adetailer=request.enable_face_enhancement,
        use_upscaling=request.enable_upscaling
    )

    # Apply quality preset
    quality_settings = {
        "low": {"steps": 15, "cfg": 6.0},
        "medium": {"steps": 25, "cfg": 7.5},
        "high": {"steps": 40, "cfg": 8.5}
    }

    settings = quality_settings[request.quality]
    for node_id, node in workflow.items():
        if node.get("class_type") == "KSampler":
            workflow[node_id]["inputs"]["steps"] = settings["steps"]
            workflow[node_id]["inputs"]["cfg"] = settings["cfg"]

    # Execute
    client = get_comfyui_client()
    result = await client.execute_workflow(workflow)

    return {
        "prompt_id": result.prompt_id,
        "status": result.status,
        "features_used": {
            "gemini": request.enable_gemini,
            "face_enhancement": request.enable_face_enhancement,
            "upscaling": request.enable_upscaling,
            "quality": request.quality
        }
    }
```

## Working with Your Complex Workflow

The workflow JSON you shared has many nodes. Here's how to control it:

### Simplify It
```python
import json

# Load your complex workflow
with open("complex_workflow.json") as f:
    workflow = json.load(f)

print(f"Original: {len(workflow)} nodes")

# Keep only essential nodes
essential_nodes = [
    "4",   # CheckpointLoader
    "6",   # Positive prompt
    "7",   # Negative prompt
    "5",   # EmptyLatent
    "3",   # KSampler
    "8",   # VAEDecode
    "9"    # SaveImage
]

simplified = {k: workflow[k] for k in essential_nodes if k in workflow}
print(f"Simplified: {len(simplified)} nodes")
```

### Extract Specific Features
```python
def extract_adetailer_nodes(workflow: dict) -> dict:
    """Extract only Adetailer-related nodes."""
    adetailer = {}

    for node_id, node in workflow.items():
        if "ADetailer" in node.get("class_type", ""):
            adetailer[node_id] = node

    return adetailer

# Extract and potentially reuse
adetailer_nodes = extract_adetailer_nodes(workflow)
print(f"Found {len(adetailer_nodes)} Adetailer nodes")
```

### Toggle Features in Complex Workflow
```python
def toggle_workflow_features(
    workflow: dict,
    use_adetailer: bool = True,
    use_upscaling: bool = True,
    use_gemini: bool = False
) -> dict:
    """Enable/disable features in complex workflow."""

    result = workflow.copy()

    # Remove Adetailer if disabled
    if not use_adetailer:
        result = {
            k: v for k, v in result.items()
            if "ADetailer" not in v.get("class_type", "")
        }

    # Remove upscaling if disabled
    if not use_upscaling:
        result = {
            k: v for k, v in result.items()
            if "Upscale" not in v.get("class_type", "")
        }

    # Add Gemini if enabled
    if use_gemini and "gemini_node" not in result:
        # Find VAE decode node
        vae_node = None
        for node_id, node in result.items():
            if node.get("class_type") == "VAEDecode":
                vae_node = node_id
                break

        if vae_node:
            # Insert Gemini after VAE decode
            result["gemini_node"] = {
                "inputs": {
                    "images": [vae_node, 0],
                    "intensity": 0.75
                },
                "class_type": "NanoBananoGeminiFlash"
            }

            # Update save node to use Gemini output
            for node_id, node in result.items():
                if node.get("class_type") == "SaveImage":
                    result[node_id]["inputs"]["images"] = ["gemini_node", 0]
                    break

    return result

# Use it
modified = toggle_workflow_features(
    workflow,
    use_adetailer=False,  # Disable face enhancement
    use_upscaling=True,   # Keep upscaling
    use_gemini=True       # Add Gemini
)
```

## Best Practices

1. **Start Simple**: Build basic workflows first, add complexity gradually
2. **Use Builder Pattern**: The `WorkflowBuilder` class makes it easier
3. **Version Your Workflows**: Save different versions as JSON files
4. **Test Incrementally**: Test each feature toggle independently
5. **Document Connections**: Comment which nodes connect to what
6. **Use Meaningful IDs**: When adding nodes manually, use descriptive IDs like `"gemini_processor"` instead of `"99"`

## Summary

**Yes, you have complete control:**

✅ **Turn workflows on/off** - Use conditionals, feature flags, or config
✅ **Add nodes** - `workflow["new_id"] = {...}`
✅ **Remove nodes** - `del workflow["node_id"]`
✅ **Modify parameters** - `workflow["3"]["inputs"]["steps"] = 50`
✅ **Change connections** - `workflow["9"]["inputs"]["images"] = ["8", 0]`
✅ **Build dynamically** - Use `WorkflowBuilder` class

Workflows are just JSON. You can do anything you want with them programmatically!
