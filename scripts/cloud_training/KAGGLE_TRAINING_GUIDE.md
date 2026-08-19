# NES Local Fine-Tuning Guide (Kaggle / Lightning AI)

Since DashScope API training is restricted due to billing permissions, you can fine-tune the NES intelligence locally on a free GPU cloud notebook (such as Kaggle, Google Colab, or Lightning AI).

## Prerequisites
1. You need the dataset `alibaba_real_sft.jsonl` (found in this folder).
2. You need the training script `local_finetuning_script.py`.

## Steps to Train on Kaggle

1. **Create a Kaggle Notebook:**
   - Go to [Kaggle](https://www.kaggle.com/) and click "Create -> Notebook".
   - Under Settings (right sidebar), turn on **GPU T4 x2** or **P100** under Accelerator.
   - Turn on **Internet**.

2. **Upload Files:**
   - On the right sidebar, click the `+ Add Data` button, or use the file explorer to upload `alibaba_real_sft.jsonl` and `local_finetuning_script.py` directly to the notebook's working directory (`/kaggle/working`).

3. **Install Dependencies:**
   - Create a code cell and run this to install the HuggingFace stack:
     ```python
     !pip install -q -U transformers datasets trl peft accelerate bitsandbytes
     ```

4. **Run the Training Script:**
   - Create a new code cell and run:
     ```python
     !python local_finetuning_script.py
     ```
   - *Note: If you uploaded the JSONL file to a specific dataset folder (e.g. `/kaggle/input/...`), you must edit the script to point to the correct absolute path before running.*

5. **Download the Weights:**
   - Once training is complete (it will take a while), a folder named `nes-llama-finetune` will be created.
   - Zip this folder and download it.
   - These are your new LoRA adapter weights for NES!
