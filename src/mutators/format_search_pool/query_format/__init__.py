# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from .reasoning_question import QA_query_format_pool, query_format_desc_map_QA
from .multiple_choice import multiple_choice_query_format_pool, query_format_desc_map_MultiChoice
from .classification import classification_query_format_pool

from .generated_format_QA import generated_query_format_pool as generated_query_format_pool_QA
from .generated_format_MultiChoices import generated_query_format_pool as generated_query_format_pool_MultiChoice

