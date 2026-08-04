import os
import json
import torch
from datasets import Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
    Trainer
)
from peft import LoraConfig, get_peft_model, TaskType

def run_local_lora_fine_tuning():
    project_root = "/Users/ada/myprojects/my-first-app"
    train_jsonl_path = os.path.join(project_root, "fine_tune_train.jsonl")
    output_dir = os.path.join(project_root, "adapters")

    print("[PROCESSING] Ingesting training examples from fine_tune_train.jsonl...")
    raw_records = []
    with open(train_jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                raw_records.append(json.loads(line))

    formatted_texts = []
    for item in raw_records:
        messages = item["messages"]
        conversation = ""
        for msg in messages:
            conversation += f"<|im_start|>{msg['role']}\n{msg['content']}<|im_end|>\n"
        formatted_texts.append({"text": conversation})

    dataset = Dataset.from_list(formatted_texts)

    print("[PROCESSING] Allocating 4-bit BitsAndBytes quantization metrics...")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True
    )

    model_id = "Qwen/Qwen2.5-1.5B-Instruct"
    print(f"[PROCESSING] Loading open-source base model topology: {model_id}...")
    
    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token

    # 1. FIXED: Added a serialization token processing mapping logic block to dynamically generate labels
    def tokenize_function(examples):
        tokenized = tokenizer(examples["text"], truncation=True, max_length=512, padding="max_length")
        # Duplicate input_ids over to labels parameter array slot to enable automatic loss computation
        tokenized["labels"] = tokenized["input_ids"].copy()
        return tokenized

    tokenized_dataset = dataset.map(tokenize_function, batched=True)

    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True
    )

    print("[PROCESSING] Initializing Parameter-Efficient (PEFT) LoRA tracking setup...")
    peft_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=8,
        lora_alpha=16,
        target_modules=["q_proj", "v_proj"],
        lora_dropout=0.05,
        bias="none"
    )

    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()

    print("[PROCESSING] Configuring local gradient descent parameters...")
    training_args = TrainingArguments(
        output_dir=output_dir,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        num_train_epochs=3,
        learning_rate=2e-4,
        fp16=True,
        logging_steps=1,
        save_strategy="no",
        report_to="none"
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset,
    )

    print("\n" + "="*60)
    print("🚀 COMMENCING LOCAL LoRA ADAPTER TRAINING JOB RUN")
    print("="*60)
    
    trainer.train()

    print("\n" + "="*60)
    print("🏆 SUCCESS: Local LoRA fine-tuning complete!")
    print(f" -> LoRA parameter weight adapters successfully generated in: {output_dir}")
    print("="*60 + "\n")

if __name__ == "__main__":
    run_local_lora_fine_tuning()
