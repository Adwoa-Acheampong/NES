"""Tool for interacting with Kaggle API for fine-tuning orchestrator."""
import os
import subprocess
import json
from typing import Any
from nes.core.registry import ToolRegistry
from nes.core.types import ToolResult
from nes.tools._stubs import BaseTool, ToolSpec

@ToolRegistry.register("kaggle_finetune")
class KaggleTool(BaseTool):
    tool_id = "kaggle_finetune"
    is_local = True

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="kaggle_finetune",
            description="Sync local data to Kaggle and push a fine-tuning notebook or script.",
            parameters={
                "type": "object",
                "properties": {
                    "dataset_path": {"type": "string", "description": "Local path to dataset directory"},
                    "dataset_name": {"type": "string", "description": "Name for the Kaggle dataset"},
                    "notebook_path": {"type": "string", "description": "Local path to Jupyter Notebook (.ipynb) or script (.py)"}
                },
                "required": ["dataset_path", "dataset_name", "notebook_path"]
            },
            category="mlops"
        )
    
    def execute(self, **params: Any) -> ToolResult:
        dataset_path = params.get("dataset_path")
        dataset_name = params.get("dataset_name")
        notebook_path = params.get("notebook_path")
        
        # Verify paths
        if not os.path.exists(dataset_path):
            return ToolResult(tool_name="kaggle_finetune", content=f"Dataset path not found: {dataset_path}", success=False)
        if not os.path.exists(notebook_path):
            return ToolResult(tool_name="kaggle_finetune", content=f"Notebook path not found: {notebook_path}", success=False)

        kaggle_username = os.environ.get("KAGGLE_USERNAME")
        if not kaggle_username:
            return ToolResult(tool_name="kaggle_finetune", content="KAGGLE_USERNAME environment variable not set. Required for slug generation.", success=False)

        # Check for Kaggle CLI v2.2.4+ auth token
        if not os.environ.get("KAGGLE_API_TOKEN"):
            return ToolResult(tool_name="kaggle_finetune", content="KAGGLE_API_TOKEN environment variable not set. Required for Kaggle API authentication.", success=False)

        results = []
        try:
            # 1. Initialize dataset metadata if not present
            meta_path = os.path.join(dataset_path, "dataset-metadata.json")
            if not os.path.exists(meta_path):
                subprocess.run(
                    ["kaggle", "datasets", "init", "-p", dataset_path], 
                    check=True, capture_output=True, text=True
                )
            
            # Use json parser to safely modify metadata
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            
            meta["title"] = dataset_name
            meta["id"] = f"{kaggle_username}/{dataset_name}"
            
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2)
            
            # 2. Create or Update Dataset
            try:
                out = subprocess.run(["kaggle", "datasets", "create", "-p", dataset_path], check=True, capture_output=True, text=True)
                results.append(f"Dataset created: {out.stdout.strip()}")
            except subprocess.CalledProcessError:
                out = subprocess.run(["kaggle", "datasets", "version", "-p", dataset_path, "-m", "Auto-update from NES"], check=True, capture_output=True, text=True)
                results.append(f"Dataset updated: {out.stdout.strip()}")
                
            # 3. Push Notebook Kernel
            kernel_dir = os.path.dirname(notebook_path)
            kernel_meta_path = os.path.join(kernel_dir, "kernel-metadata.json")
            if not os.path.exists(kernel_meta_path):
                subprocess.run(["kaggle", "kernels", "init", "-p", kernel_dir], check=True, capture_output=True, text=True)
                
            with open(kernel_meta_path, "r", encoding="utf-8") as f:
                kmeta = json.load(f)
                
            kernel_slug = os.path.basename(notebook_path).replace(".ipynb", "").replace(".py", "").lower().replace("_", "-")
            kmeta["id"] = f"{kaggle_username}/{kernel_slug}"
            kmeta["title"] = f"{dataset_name} Finetuning"
            kmeta["code_file"] = os.path.basename(notebook_path)
            kmeta["language"] = "python"
            kmeta["kernel_type"] = "script" if notebook_path.endswith('.py') else "notebook"
            kmeta["is_private"] = "true"
            kmeta["enable_gpu"] = "true"
            kmeta["enable_internet"] = "true"
            kmeta["dataset_sources"] = [f"{kaggle_username}/{dataset_name}"]
            
            with open(kernel_meta_path, "w", encoding="utf-8") as f:
                json.dump(kmeta, f, indent=2)
                    
            kout = subprocess.run(["kaggle", "kernels", "push", "-p", kernel_dir], check=True, capture_output=True, text=True)
            results.append(f"Kernel pushed: {kout.stdout.strip()}")
            
            return ToolResult(tool_name="kaggle_finetune", content="\n".join(results), success=True)
            
        except subprocess.CalledProcessError as e:
            return ToolResult(tool_name="kaggle_finetune", content=f"Kaggle CLI Error: {e.stderr}", success=False)
        except Exception as e:
            return ToolResult(tool_name="kaggle_finetune", content=f"Error: {e}", success=False)
