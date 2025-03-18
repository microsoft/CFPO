# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

# Script to run GSM8K

current_time=$(date +"%Y%m%d%H%M%S")

python src/main.py \
    --task GSM8K \
    --output_marker GSM8K_MISTRAL \
    --train_size 10 \
    --minibatch_size 10 \
    --valid_size 10 \
    --test_size -1 \
    --controller multimute_1-linear_temp_0.7-beam_1 \
    --opt_llm GPT4 \
    --eval_llm Mistral \
    --vllm_pth ../Mistral-7B-v0.1 \
    --init_temperature 1.0 \
    --rounds 5 \
    --beam_size 8 \
    --num_return 2 \
    --num_feedbacks 1 \
    --errors_per_feedback 1 \
    --correct_per_feedback 1 \
    --apply_per_feedback 1 \
    --num_random 1 \
    --num_format 1 \
    --select_method UCT \
    --gpu_id 0