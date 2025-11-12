"""
Dynamic ComfyUI Workflow Builder

This module shows how to programmatically control workflows:
- Enable/disable features
- Add/remove nodes
- Modify connections
- Create reusable workflow templates
"""

import random
from typing import Optional
from copy import deepcopy


class WorkflowBuilder:
    """Build ComfyUI workflows programmatically with full control."""

    def __init__(self, model: str = "v1-5-pruned-emaonly.ckpt"):
        self.model = model
        self.workflow = {}
        self.node_id_counter = 1

    def _next_id(self) -> str:
        """Get next available node ID."""
        node_id = str(self.node_id_counter)
        self.node_id_counter += 1
        return node_id

    def add_checkpoint_loader(self) -> str:
        """Add checkpoint loader node. Returns node ID."""
        node_id = self._next_id()
        self.workflow[node_id] = {
            "inputs": {"ckpt_name": self.model},
            "class_type": "CheckpointLoaderSimple"
        }
        return node_id

    def add_text_encode(self, text: str, clip_node_id: str, clip_output: int = 1) -> str:
        """Add CLIP text encoder. Returns node ID."""
        node_id = self._next_id()
        self.workflow[node_id] = {
            "inputs": {
                "text": text,
                "clip": [clip_node_id, clip_output]
            },
            "class_type": "CLIPTextEncode"
        }
        return node_id

    def add_empty_latent(self, width: int, height: int, batch_size: int = 1) -> str:
        """Add empty latent image. Returns node ID."""
        node_id = self._next_id()
        self.workflow[node_id] = {
            "inputs": {
                "width": width,
                "height": height,
                "batch_size": batch_size
            },
            "class_type": "EmptyLatentImage"
        }
        return node_id

    def add_ksampler(
        self,
        model_node: str,
        positive_node: str,
        negative_node: str,
        latent_node: str,
        seed: Optional[int] = None,
        steps: int = 25,
        cfg: float = 7.5,
        sampler: str = "dpmpp_2m",
        scheduler: str = "karras"
    ) -> str:
        """Add KSampler node. Returns node ID."""
        node_id = self._next_id()
        self.workflow[node_id] = {
            "inputs": {
                "seed": seed if seed is not None else random.randint(0, 1000000),
                "steps": steps,
                "cfg": cfg,
                "sampler_name": sampler,
                "scheduler": scheduler,
                "denoise": 1,
                "model": [model_node, 0],
                "positive": [positive_node, 0],
                "negative": [negative_node, 0],
                "latent_image": [latent_node, 0]
            },
            "class_type": "KSampler"
        }
        return node_id

    def add_vae_decode(self, samples_node: str, vae_node: str, vae_output: int = 2) -> str:
        """Add VAE decoder. Returns node ID."""
        node_id = self._next_id()
        self.workflow[node_id] = {
            "inputs": {
                "samples": [samples_node, 0],
                "vae": [vae_node, vae_output]
            },
            "class_type": "VAEDecode"
        }
        return node_id

    def add_save_image(self, images_node: str, prefix: str = "output") -> str:
        """Add save image node. Returns node ID."""
        node_id = self._next_id()
        self.workflow[node_id] = {
            "inputs": {
                "filename_prefix": prefix,
                "images": [images_node, 0]
            },
            "class_type": "SaveImage"
        }
        return node_id

    def add_gemini_flash(self, images_node: str, intensity: float = 0.75) -> str:
        """Add Gemini 2.5 Flash processing (NanoBanano). Returns node ID."""
        node_id = self._next_id()
        self.workflow[node_id] = {
            "inputs": {
                "images": [images_node, 0],
                "intensity": intensity
            },
            "class_type": "NanoBananoGeminiFlash"
        }
        return node_id

    def add_adetailer(self, images_node: str, model: str = "face_yolov8n.pt") -> str:
        """Add Adetailer for face detection/enhancement. Returns node ID."""
        node_id = self._next_id()
        self.workflow[node_id] = {
            "inputs": {
                "images": [images_node, 0],
                "model": model
            },
            "class_type": "ADetailer"
        }
        return node_id

    def add_upscale(
        self,
        images_node: str,
        upscale_by: float = 2.0,
        model: str = "RealESRGAN_x4plus.pth"
    ) -> str:
        """Add upscaling node. Returns node ID."""
        node_id = self._next_id()
        self.workflow[node_id] = {
            "inputs": {
                "images": [images_node, 0],
                "upscale_by": upscale_by,
                "model_name": model
            },
            "class_type": "ImageUpscaleWithModel"
        }
        return node_id

    def remove_node(self, node_id: str):
        """Remove a node from the workflow."""
        if node_id in self.workflow:
            del self.workflow[node_id]

    def get_workflow(self) -> dict:
        """Get the complete workflow JSON."""
        return deepcopy(self.workflow)

    def build_basic(
        self,
        prompt: str,
        negative: str = "low quality, blurry",
        width: int = 1920,
        height: int = 1080,
        steps: int = 25,
        cfg: float = 7.5
    ) -> dict:
        """Build a basic text-to-image workflow."""
        # Reset
        self.workflow = {}
        self.node_id_counter = 1

        # Build pipeline
        checkpoint = self.add_checkpoint_loader()
        positive = self.add_text_encode(prompt, checkpoint)
        negative_cond = self.add_text_encode(negative, checkpoint)
        latent = self.add_empty_latent(width, height)
        sampler = self.add_ksampler(checkpoint, positive, negative_cond, latent, steps=steps, cfg=cfg)
        decoded = self.add_vae_decode(sampler, checkpoint)
        self.add_save_image(decoded)

        return self.get_workflow()

    def build_advanced(
        self,
        prompt: str,
        use_gemini: bool = False,
        use_adetailer: bool = False,
        use_upscaling: bool = False,
        width: int = 1920,
        height: int = 1080
    ) -> dict:
        """Build an advanced workflow with optional features."""
        # Reset
        self.workflow = {}
        self.node_id_counter = 1

        # Base pipeline
        checkpoint = self.add_checkpoint_loader()
        positive = self.add_text_encode(prompt, checkpoint)
        negative = self.add_text_encode("low quality, blurry", checkpoint)
        latent = self.add_empty_latent(width, height)
        sampler = self.add_ksampler(checkpoint, positive, negative, latent)
        decoded = self.add_vae_decode(sampler, checkpoint)

        # Track last image node
        last_node = decoded

        # Add optional processing nodes
        if use_gemini:
            last_node = self.add_gemini_flash(last_node)

        if use_adetailer:
            last_node = self.add_adetailer(last_node)

        if use_upscaling:
            last_node = self.add_upscale(last_node)

        # Save final result
        self.add_save_image(last_node)

        return self.get_workflow()


# Example usage functions
def example_basic():
    """Example: Basic workflow."""
    builder = WorkflowBuilder()
    workflow = builder.build_basic(
        prompt="beautiful coral gradient background, modern minimalist",
        width=1920,
        height=1080,
        steps=30
    )
    return workflow


def example_with_gemini():
    """Example: Workflow with Gemini 2.5 Flash."""
    builder = WorkflowBuilder()
    workflow = builder.build_advanced(
        prompt="futuristic tech background",
        use_gemini=True,
        use_adetailer=False,
        use_upscaling=False
    )
    return workflow


def example_full_pipeline():
    """Example: Full pipeline with all features."""
    builder = WorkflowBuilder()
    workflow = builder.build_advanced(
        prompt="professional portrait photo",
        use_gemini=True,
        use_adetailer=True,  # Face enhancement
        use_upscaling=True,  # 2x upscale
        width=1024,
        height=1024
    )
    return workflow


def example_custom_modification():
    """Example: Build workflow then modify it."""
    builder = WorkflowBuilder()

    # Start with basic workflow
    workflow = builder.build_basic("sunset landscape")

    # Manually add custom node
    builder.workflow["custom_99"] = {
        "inputs": {
            "images": ["6", 0],  # Connect to VAE decode
            "custom_param": "special_value"
        },
        "class_type": "MyCustomNode"
    }

    # Update save node to use custom node output
    builder.workflow["7"]["inputs"]["images"] = ["custom_99", 0]

    return builder.get_workflow()


if __name__ == "__main__":
    import json

    print("🎨 ComfyUI Workflow Builder Examples")
    print("=" * 60)

    print("\n1. Basic Workflow:")
    basic = example_basic()
    print(f"   Nodes: {len(basic)}")
    print(f"   Node IDs: {list(basic.keys())}")

    print("\n2. With Gemini Flash:")
    gemini = example_with_gemini()
    print(f"   Nodes: {len(gemini)}")

    print("\n3. Full Pipeline:")
    full = example_full_pipeline()
    print(f"   Nodes: {len(full)}")

    print("\n4. Custom Modified:")
    custom = example_custom_modification()
    print(f"   Nodes: {len(custom)}")

    print("\n✅ All examples generated successfully!")
    print("\nTo use these workflows:")
    print("  workflow = example_basic()")
    print("  result = await client.execute_workflow(workflow)")
