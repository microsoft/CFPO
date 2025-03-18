# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import re
from typing import List, Dict, Tuple, Optional

def parse_tagged_text(text: str, start_tag: str, end_tag: str, logger=None) -> List[str]:
    """Parse text that is tagged with start and end tags."""
    texts = []
    text_0 = text  # Save the original text for logging purposes

    while True:
        start_index = text.find(start_tag)
        if start_index == -1:
            break
        end_index = text.find(end_tag, start_index)
        if end_index == -1:
            break
        start_index += len(start_tag)
        texts.append(text[start_index:end_index].strip())
        text = text[end_index + len(end_tag):]

    if len(texts) == 0:
        if logger:
            logger.warning("\nNo components found between tags <START> and <END>\n")
            logger.warning(f"\nResponse:\n{text_0}\n")
        else:
            print("\nNo components found between tags <START> and <END>\n")
            print(f"\nResponse:\n{text_0}\n")
        return [None]

    return texts

def log_to_file(filename, content, mode='a'):
    """
    :param filename: str
    :param content: str
    :param mode: str
    """
    with open(filename, mode) as outf:
        outf.write(content + '\n')

def get_component_desc(component_name):
    component_desc_map = {
        'TASK_INSTRUCTION': "Defines the primary goal or objective of the task, guiding the model to understand what is expected.",
        'TASK_DETAIL': "Supplies supplementary information related to the task, possibly outlining the steps or providing clues for resolution.",
        'OUTPUT_FORMAT': "Specifies the desired format for the model's output, detailing the structure, type, or stylistic approach it should adhere to.",
        'EXAMPLE_HINTER': "Offers a brief hint indicating that examples will follow, such as, 'Here are some examples:', 'To illustrate how to approach these problems, consider the following examples:'.",
        'EXAMPLES': "Presents specific instances or scenarios pertinent to the task, including inputs, expected outputs, and correct responses.",
        'COT_HINTER': "Provides a concise sentence to encourage the generation that incorporate a chain of thought or reasoning process, such as 'Let's think step by step'.",
        'PROMPT_RENDERER': "Defines how to aggregate all components into a structured prompt.",
        'QUERY_FORMAT': "Defines how to structure the rendering of examples and queries.",
    }
    if component_name in component_desc_map or component_name.upper() in component_desc_map:
        return component_desc_map[component_name.upper()]
    else:
        return ""

def stringify_key(key):
    if callable(key):
        return key.__name__
    else:
        return str(key)

def stringify_value(value):
    if isinstance(value, dict):
        return stringify_dict(value)
    elif isinstance(value, list):
        return [stringify_value(item) for item in value]
    elif isinstance(value, tuple):
        return tuple(stringify_value(item) for item in value)
    else:
        return value

def stringify_dict(d):
    return {stringify_key(k): stringify_value(v) for k, v in d.items()}

def convert_seconds(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    formatted_hours = f"{hours:.0f}"
    formatted_minutes = f"{minutes:.0f}"
    formatted_secs = f"{secs:.0f}"
    
    return f"{formatted_hours} H {formatted_minutes} MIN {formatted_secs} S"

import json
import re
import os
import random
import numpy as np
import torch
import multiprocessing
from typing import Tuple
from statistics import mean
from torch.utils.data import Dataset


def fix_seeds(seed):
    # random
    random.seed(seed)
    # Numpy
    np.random.seed(seed)
    # Pytorch
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def setup_model_parallel() -> Tuple[int, int]:
    from fairscale.nn.model_parallel.initialize import initialize_model_parallel
    
    local_rank = int(os.environ.get("LOCAL_RANK", -1))
    world_size = int(os.environ.get("WORLD_SIZE", -1))

    torch.distributed.init_process_group("nccl")
    initialize_model_parallel(world_size)
    torch.cuda.set_device(local_rank)

    return local_rank, world_size


def read_json(file_path):
    assert str(file_path).endswith(".json")
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data


def save_json(js_obj, file_path):
    assert str(file_path).endswith(".json")
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(js_obj, f, indent=4)


def read_txt(file_path):
    assert str(file_path).endswith(".txt")
    with open(file_path, 'r', encoding='utf-8') as f:
        data = f.read()
    return data


def regex_calibrate(output_text: str):
    """
    use regex to extract_answer_from_response the mathematic equation and use python to correct answer 
    """
    equation_regex = r"([\d\.\%\/\*\+\-\$\s]+) = ([\d\.\$\s]+)(?=[A-Za-z,.;!?]|\b)"

    def evaluate_expression(expression):
        cleaned_expression = re.sub(r'\s+\.', '.', expression)
        cleaned_expression = re.sub(r'\.\s+', '.', cleaned_expression)
        cleaned_expression = cleaned_expression.replace(' x ', ' * ').replace('$', '').replace('%', '/100')
        cleaned_expression = re.sub(r'\s+', '', cleaned_expression)
        try:
            return eval(cleaned_expression, {}, {})
        except Exception:
            return None

    def handle_units(match):
        expression, current_answer = match.groups()
        unit = re.findall(r"[\$\$\$]", current_answer)
        unit = unit[0] if unit else ''
        correct_answer = evaluate_expression(expression)
        if correct_answer is None:
            return match.group(0)
        if '.' in current_answer or correct_answer % 1 != 0:
            correct_answer = f"{correct_answer:.6f}"
        else:
            correct_answer = int(correct_answer)
        return f" {expression.strip()} = {unit}{correct_answer} " if correct_answer is not None else match.group(0)

    calibrated_text = re.sub(equation_regex, handle_units, output_text)
    calibrated_text = calibrated_text.strip()

    calibrated_text = re.sub(r"(\d)([A-Za-z,.;!?])", r"\1 \2", calibrated_text)
    calibrated_text = re.sub(r"(\d)\s+(\.\d+)", r"\1\2", calibrated_text)

    return calibrated_text

# https://review-of-my-life.blogspot.com/2017/11/python-dict-shuffle.html
def shuffleDict(d):
    keys = list(d.keys())
    random.shuffle(keys)
    [(key, d[key]) for key in keys]
    random.shuffle(keys)
    [(key, d[key]) for key in keys]
    random.shuffle(keys)
    keys = [(key, d[key]) for key in keys]
    #keys = d(keys)
    return dict(keys)


def data_reader(args):
    questions = []
    answers = []
    decoder = json.JSONDecoder()

    dataset_path = os.path.join(args.data_root, args.dataset_name, "test.jsonl")

    if args.dataset_name == "aqua":
      with open(dataset_path) as f:
        lines = f.readlines()
        for line in lines:
          json_res = decoder.raw_decode(line)[0]
          choice = "(" + "(".join(json_res["options"])
          choice = choice.replace("(", " (").replace(")", ") ")
          choice = "Answer Choices:" + choice
          questions.append(json_res["question"].strip() + " " + choice)
          answers.append(json_res["correct"])
  
    elif args.dataset_name == "gsm8k":
      with open(dataset_path) as f:
        lines = f.readlines()
        for line in lines:
          json_res = decoder.raw_decode(line)[0]
          questions.append(json_res["question"].strip())
          answers.append(json_res["answer"].split("#### ")[-1])
  
    elif args.dataset_name == "commonsensqa":
      with open(dataset_path) as f:
        lines = f.readlines()
        for line in lines:
          json_res = decoder.raw_decode(line)[0]
          choice = "Answer Choices:"
          for c in json_res["question"]["choices"]:
              choice += " ("
              choice += c["label"]
              choice += ") "
              choice += c["text"]
          questions.append(json_res["question"]["stem"].strip() + " " + choice)
          answers.append(json_res["answerKey"])

    elif args.dataset_name in ("addsub", "multiarith", "singleeq"):
      with open(dataset_path) as f:
        json_data = json.load(f)
        for line in json_data:
          q = line["sQuestion"].strip()
          a = str(line["lSolutions"][0])
          if a[-2:] == ".0":
              a = a[:-2]
          questions.append(q)
          answers.append(a)
        
    elif args.dataset_name == "strategyqa":
      with open(dataset_path) as f:
        json_data = json.load(f)["examples"]
        for line in json_data:
          q = line["input"].strip()
          a = int(line["target_scores"]["Yes"])
          if a == 1:
              a = "yes"
          else:
              a = "no"
          questions.append(q)
          answers.append(a)
        
    elif args.dataset_name == "svamp":
      with open(dataset_path) as f:
        json_data = json.load(f)
        for line in json_data:
            q = line["Body"].strip() + " " + line["Question"].strip()
            a = str(line["Answer"])
            if a[-2:] == ".0":
                a = a[:-2]
            questions.append(q)
            answers.append(a)
            
    elif args.dataset_name in ("bigbench_date", "object_tracking"):
      with open(dataset_path) as f:
        json_data = json.load(f)
        json_data = json_data["examples"]
        if args.dataset_name == "bigbench_date":
            choice_index = ['A','B','C','D','E','F']
        elif args.dataset_name in ("object_tracking"):
            choice_index = ['A','B','C']
        else:
            raise ValueError("dataset is not properly defined ...")
        for line in json_data:
          q = line["input"].strip()
          if args.dataset_name == "bigbench_date":
              choice = "Answer Choices:"
              # Randomly shuffle the answer choice dictionary because the original answer is always A ...
              choice_dic = shuffleDict(line["target_scores"])
          elif args.dataset_name == "object_tracking":
              choice = "\nWhich choice is true ? Answer Choices:"
              choice_dic = line["target_scores"]
          else:
              raise ValueError("dataset is not properly defined ...")
          for i, key_value in enumerate(choice_dic.items()):
              key, value = key_value
              choice += " ("
              choice += choice_index[i]
              choice += ") "
              choice += key
              if value == 1:
                  a = choice_index[i]
                  #a = key
          q = q + " " + choice
          questions.append(q)
          answers.append(a)            
          
    elif args.dataset_name in ("coin_flip", "last_letters"):
      with open(dataset_path) as f:
        json_data = json.load(f)
        json_data = json_data["examples"]
        for line in json_data:
          q = line["question"]
          a = line["answer"]
          questions.append(q)
          answers.append(a)
        
    else:
        raise ValueError("dataset is not properly defined ...")
    
    q_len_list = []
    for q in questions:
        q_len_list.append(len(q.split(" ")))
    q_len_mean = mean(q_len_list)
    
    if args.verbose:
        print("dataset : {}".format(args.dataset_name))
        print("data size : {}".format(len(answers)))
        print("average num of words for each sample : {}".format(q_len_mean))
    
    return questions, answers

# Create dataset object before dataloader ...
class MyDataset(Dataset):
    def __init__(self, args):
        super().__init__()
        self.questions, self.answers = data_reader(args)
        self.len = len(self.questions)
        
    def __len__(self):
        return self.len
    
    def __getitem__(self, index):
        input = self.questions[index]
        output = self.answers[index]
        return input, output

def setup_data_loader(args):
    # fix randomness of dataloader to ensure reproducibility
    # https://pytorch.org/docs/stable/notes/randomness.html
    fix_seeds(args.seed)
    worker_seed = torch.initial_seed() % 2**32
    if args.verbose:
        print("worker_seed : {}".format(worker_seed))
    def seed_worker(worker_id):
        np.random.seed(worker_seed)
        random.seed(worker_seed)
    g = torch.Generator()
    g.manual_seed(worker_seed)
    
    dataloader_num_workers = multiprocessing.cpu_count()
    dataloader_num_workers = min(dataloader_num_workers, args.max_num_worker)
    if args.verbose:
        print("dataloader_num_workers: " + str(dataloader_num_workers))
    
    dataset = MyDataset(args)
    
    dataloader = torch.utils.data.DataLoader(dataset,
                  shuffle=False,
                  batch_size=1,
                  drop_last=False,
                  num_workers=dataloader_num_workers,
                  worker_init_fn=seed_worker,
                  generator=g,
                  pin_memory=True)

    return dataloader

# ver 0.2
def answer_cleansing(args, pred):
    if args.verbose:
        print("pred_before : " + pred)

    if args.method in ("few_shot", "few_shot_cot"):
        preds = pred.split('The answer is')
        answer_flag = True if len(preds) > 1 else False 
        if answer_flag:
            # Pick first answer with flag
            pred = preds[1]
        else:
            # Pick last number without flag
            pred = preds[-1]
    else:
        preds = pred.split('\nTherefore, the answer (arabic numerals) is')
        answer_flag = True if len(preds) > 1 else False 
        if answer_flag:
            # Pick first answer with flag
            pred = preds[1]
        else:
            # Pick last number without flag
            pred = preds[-1]

    model_response = pred
    if args.dataset_name in ("aqua", "commonsensqa"):
        pred = re.findall(r'A|B|C|D|E', pred)
    elif args.dataset_name == "bigbench_date":
        pred = re.findall(r'A|B|C|D|E|F', pred)
    elif args.dataset_name in ("object_tracking"):
        pred = re.findall(r'A|B|C', pred)
    elif args.dataset_name in ("gsm8k", "addsub", "multiarith", "svamp", "singleeq"):
        pred = pred.replace(",", "")
        pred = [s for s in re.findall(r'-?\d+\.?\d*', pred)]
    elif args.dataset_name in ("strategyqa", "coin_flip"):
        pred = pred.lower()
        pred = re.sub("\"|\'|\n|\.|\s|\:|\,"," ", pred)
        pred = pred.split(" ")
        pred = [i for i in pred if i in ("yes", "no")]
    elif args.dataset_name == "last_letters":
        pred = re.sub("\"|\'|\n|\.|\s","", pred)
        pred = [pred]
    else:
        raise ValueError("dataset is not properly defined ...")

    # If there is no candidate in list, null is set.
    if len(pred) == 0:
        pred = ""
    else:
        if args.method in ("few_shot", "few_shot_cot"):
            if answer_flag:
                # choose the first element in list ...
                pred = pred[0]
            else:
                # choose the last element in list ...
                pred = pred[-1]
        elif args.method in ("zero_shot", "zero_shot_cot"):
            # choose the first element in list ...
            pred = pred[0]
        else:
            raise ValueError("method is not properly defined ...")
    
    # (For arithmetic tasks) if a word ends with period, it will be omitted ...
    if pred != "" and pred[-1] == ".":
            pred = pred[:-1]
    
    if args.verbose:
        print("pred_after : " + pred)
    
    return pred, model_response


def is_number(s):    
    try:      
        float(s)        
        return True    
    except ValueError:  
        pass  
    try:        
        import unicodedata  
        unicodedata.numeric(s) 
        return True    
    except (TypeError, ValueError):        
        pass    
        return False
