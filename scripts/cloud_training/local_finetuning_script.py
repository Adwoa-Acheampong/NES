# NES Local Fine-Tuning Script (HuggingFace + PEFT)
# Optimized for free GPU notebooks like Kaggle or Lightning AI Studio

# 1. Install Required Libraries
import subprocess
import sys
subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "-U",
    "transformers", "datasets", "trl", "peft", "accelerate", "bitsandbytes"])

import os
import argparse
import torch
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
)
from peft import LoraConfig, get_peft_model
from trl import SFTTrainer

def parse_args():
    parser = argparse.ArgumentParser(description="NES Local Fine-Tuning Script")
    parser.add_argument("--data_path", type=str, default="alibaba_real_sft.jsonl", help="Path to JSONL dataset")
    parser.add_argument("--output_dir", type=str, default="./nes-qwen-finetune", help="Output directory for model")
    return parser.parse_args()

def setup_and_train(data_path="alibaba_real_sft.jsonl", output_dir="./nes-qwen-finetune"):
    print("Initializing NES Local Fine-Tuning Pipeline...")
    
    # Check if dataset exists
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Dataset not found at {data_path}. Please upload your JSONL file.")

    # Load the NES dataset
    print("Loading dataset...")
    dataset = load_dataset("json", data_files=data_path, split="train")

    # We use a lightweight Qwen-based model that can fit on a free T4 GPU (Kaggle/Colab)
    model_id = "Qwen/Qwen2.5-1.5B-Instruct"
    
    # 4-bit Quantization to save memory
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16
    )

    print(f"Loading base model: {model_id}")
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    tokenizer.pad_token = tokenizer.eos_token
    
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        quantization_config=bnb_config,
        device_map="auto"
    )

    # Setup LoRA (Low-Rank Adaptation)
    print("Applying LoRA configuration...")
    peft_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM"
    )
    model = get_peft_model(model, peft_config)

    # Format the messages into standard chat templates
    def format_prompt(examples):
        texts = []
        for messages in examples['messages']:
            # Combine system, user, and assistant messages
            formatted = ""
            for msg in messages:
                role = msg['role'].upper()
                content = msg['content']
                formatted += f"<|{role}|>\n{content}</s>\n"
            texts.append(formatted)
        return {"text": texts}

    print("Formatting prompts...")
    dataset = dataset.map(format_prompt, batched=True)

    # Training Arguments
    training_args = TrainingArguments(
        output_dir=output_dir,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        logging_steps=10,
        max_steps=100, # Adjust for longer training
        optim="paged_adamw_8bit",
        fp16=True,
        run_name="nes-qwen-sft"
    )

    # Start the Trainer
    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset,
        peft_config=peft_config,
        dataset_text_field="text",
        max_seq_length=512,
        tokenizer=tokenizer,
        args=training_args,
    )

    print("Starting Training! This may take a while depending on your GPU...")
    trainer.train()
    
    # Save the fine-tuned model adapter
    print(f"Saving fine-tuned model to {output_dir}")
    trainer.model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    print("Training Complete!")

if __name__ == "__main__":
    args = parse_args()
    
    # Auto-detect Kaggle environment
    if os.path.exists("/kaggle/input"):
        print("Kaggle environment detected!")
        # Find the jsonl file inside /kaggle/input
        dataset_found = False
        for root, dirs, files in os.walk("/kaggle/input"):
            if "alibaba_real_sft.jsonl" in files:
                args.data_path = os.path.join(root, "alibaba_real_sft.jsonl")
                dataset_found = True
                break
        if not dataset_found:
            print("Warning: alibaba_real_sft.jsonl not found in /kaggle/input, falling back to default.")
        
        # Save output to /kaggle/working so it is persisted
        args.output_dir = "/kaggle/working/nes-qwen-finetune"
        
    setup_and_train(data_path=args.data_path, output_dir=args.output_dir)
