"""Patch model_comparator.html – rewrite MODEL_CATALOG + fix card footer stats."""

import sys

HTML = r"C:\Users\dvdze\Documents\GitHub\GeorgeHaber\Swarm\model_comparator.html"

NEW_CATALOG = r"""const _MODEL_CATALOG = [
  // == Llama (Meta) ===========================================================
  { id:'llama32-1b',  name:'Llama 3.2 1B Instruct',    family:'Llama',   params:'1B',      sizeGb:0.7,
    quant:'Q4_K_M', tags:['fast','chat'],
    color:'#7c3aed', textColor:'#ede9fe',
    hfPath:'bartowski/Llama-3.2-1B-Instruct-GGUF/Llama-3.2-1B-Instruct-Q4_K_M.gguf',
    bestFor:'Edge devices  /  ultra-fast replies  /  simple tasks',
    desc:"Meta's tiny powerhouse. Runs on anything. Ideal when speed matters most.",
    params_preset:{temperature:0.7, max_tokens:512, n_ctx:4096},
    downloads:850000, releasedMs: Date.parse('2024-09-01') },
  { id:'llama32-3b',  name:'Llama 3.2 3B Instruct',    family:'Llama',   params:'3B',      sizeGb:1.9,
    quant:'Q4_K_M', tags:['fast','chat'],
    color:'#7c3aed', textColor:'#ede9fe',
    hfPath:'bartowski/Llama-3.2-3B-Instruct-GGUF/Llama-3.2-3B-Instruct-Q4_K_M.gguf',
    bestFor:'Personal assistant  /  summarization  /  lightweight chat',
    desc:"Great balance of speed and quality for everyday tasks.",
    params_preset:{temperature:0.7, max_tokens:512, n_ctx:4096},
    downloads:890000, releasedMs: Date.parse('2024-09-01') },
  { id:'llama31-8b',  name:'Llama 3.1 8B Instruct',    family:'Llama',   params:'8B',      sizeGb:4.9,
    quant:'Q4_K_M', tags:['chat','reasoning'],
    color:'#7c3aed', textColor:'#ede9fe',
    hfPath:'bartowski/Meta-Llama-3.1-8B-Instruct-GGUF/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf',
    bestFor:'General chat  /  analysis  /  writing  /  instructions',
    desc:"Meta's flagship open model. Excellent all-rounder for chat and reasoning.",
    params_preset:{temperature:0.7, max_tokens:512, n_ctx:8192},
    downloads:2100000, releasedMs: Date.parse('2024-07-01') },
  { id:'llama31-70b', name:'Llama 3.1 70B Instruct',   family:'Llama',   params:'70B',     sizeGb:42.5,
    quant:'Q4_K_M', tags:['chat','reasoning'],
    color:'#7c3aed', textColor:'#ede9fe',
    hfPath:'bartowski/Meta-Llama-3.1-70B-Instruct-GGUF/Meta-Llama-3.1-70B-Instruct-Q4_K_M.gguf',
    bestFor:'Complex reasoning  /  high-quality writing  /  research',
    desc:"Near-GPT-4 quality. Requires significant RAM but worth it.",
    params_preset:{temperature:0.7, max_tokens:1024, n_ctx:16384},
    downloads:980000, releasedMs: Date.parse('2024-07-01') },
  { id:'llama33-70b', name:'Llama 3.3 70B Instruct',   family:'Llama',   params:'70B',     sizeGb:42.5,
    quant:'Q4_K_M', tags:['chat','reasoning'],
    color:'#7c3aed', textColor:'#ede9fe',
    hfPath:'bartowski/Llama-3.3-70B-Instruct-GGUF/Llama-3.3-70B-Instruct-Q4_K_M.gguf',
    bestFor:'Best open 70B  /  complex reasoning  /  coding  /  writing',
    desc:"Meta's flagship Dec 2024. Matches GPT-4o on many benchmarks. New 70B standard.",
    params_preset:{temperature:0.7, max_tokens:1024, n_ctx:16384},
    downloads:3400000, releasedMs: Date.parse('2024-12-06') },
  { id:'llama4-scout', name:'Llama 4 Scout 17B',        family:'Llama',   params:'17B MoE', sizeGb:10.0,
    quant:'Q4_K_M', tags:['fast','chat','reasoning','multilingual'],
    color:'#7c3aed', textColor:'#ede9fe',
    hfPath:'bartowski/Llama-4-Scout-17B-16E-Instruct-GGUF/Llama-4-Scout-17B-16E-Instruct-Q4_K_M.gguf',
    bestFor:'Fast MoE  /  multimodal  /  10M context  /  multilingual',
    desc:"Meta's 2025 generation. MoE: 17B active params, enormous 10M context window.",
    params_preset:{temperature:0.7, max_tokens:1024, n_ctx:32768},
    downloads:2100000, releasedMs: Date.parse('2025-04-05') },
  { id:'llama4-maverick', name:'Llama 4 Maverick 17B',  family:'Llama',   params:'17B MoE', sizeGb:12.0,
    quant:'Q4_K_M', tags:['chat','reasoning','code'],
    color:'#7c3aed', textColor:'#ede9fe',
    hfPath:'bartowski/Llama-4-Maverick-17B-128E-Instruct-GGUF/Llama-4-Maverick-17B-128E-Instruct-Q4_K_M.gguf',
    bestFor:'Reasoning  /  coding  /  multimodal  /  128 experts',
    desc:"Llama 4 Maverick: 128 experts, image understanding. Beats GPT-4o on many evals.",
    params_preset:{temperature:0.7, max_tokens:1024, n_ctx:32768},
    downloads:1700000, releasedMs: Date.parse('2025-04-05') },
  // == Phi (Microsoft) ========================================================
  { id:'phi35-mini',  name:'Phi-3.5 Mini Instruct',     family:'Phi',     params:'3.8B',    sizeGb:2.4,
    quant:'Q4_K_M', tags:['fast','chat','reasoning'],
    color:'#2563eb', textColor:'#dbeafe',
    hfPath:'bartowski/Phi-3.5-mini-instruct-GGUF/Phi-3.5-mini-instruct-Q4_K_M.gguf',
    bestFor:'Reasoning  /  math  /  coding tasks',
    desc:"Microsoft's efficient small model. Punches way above its weight on reasoning benchmarks.",
    params_preset:{temperature:0.3, max_tokens:512, n_ctx:8192},
    downloads:1400000, releasedMs: Date.parse('2024-08-01') },
  { id:'phi4-14b',    name:'Phi-4 14B Instruct',         family:'Phi',     params:'14B',     sizeGb:8.5,
    quant:'Q4_K_M', tags:['chat','reasoning','code'],
    color:'#2563eb', textColor:'#dbeafe',
    hfPath:'bartowski/phi-4-GGUF/phi-4-Q4_K_M.gguf',
    bestFor:'Advanced reasoning  /  coding  /  STEM',
    desc:"Microsoft's smartest Phi yet. Beats many 30B models on benchmarks.",
    params_preset:{temperature:0.3, max_tokens:1024, n_ctx:16384},
    downloads:760000, releasedMs: Date.parse('2024-12-01') },
  { id:'phi4-mini',   name:'Phi-4 Mini Instruct',         family:'Phi',     params:'3.8B',    sizeGb:2.5,
    quant:'Q4_K_M', tags:['fast','reasoning','code'],
    color:'#2563eb', textColor:'#dbeafe',
    hfPath:'bartowski/Phi-4-mini-instruct-GGUF/Phi-4-mini-instruct-Q4_K_M.gguf',
    bestFor:'Compact reasoning  /  math  /  coding  /  fast inference',
    desc:"Phi-4 at 3.8B. Beats many 7B models on STEM. Microsoft's efficient powerhouse.",
    params_preset:{temperature:0.3, max_tokens:512, n_ctx:8192},
    downloads:1200000, releasedMs: Date.parse('2025-01-31') },
  { id:'phi4-reasoning', name:'Phi-4 Reasoning Plus',    family:'Phi',     params:'14B',     sizeGb:9.0,
    quant:'Q4_K_M', tags:['reasoning','code'],
    color:'#2563eb', textColor:'#dbeafe',
    hfPath:'bartowski/Phi-4-reasoning-plus-GGUF/Phi-4-reasoning-plus-Q4_K_M.gguf',
    bestFor:'Advanced math  /  science  /  chain-of-thought step-by-step',
    desc:"Phi-4 fine-tuned for reasoning. Shows its thinking like DeepSeek R1. Very impressive at 14B.",
    params_preset:{temperature:0.0, max_tokens:2048, n_ctx:32768},
    downloads:980000, releasedMs: Date.parse('2025-04-01') },
  // == Gemma (Google) =========================================================
  { id:'gemma3-1b',   name:'Gemma 3 1B Instruct',        family:'Gemma',   params:'1B',      sizeGb:0.8,
    quant:'Q4_K_M', tags:['fast','chat','multilingual'],
    color:'#16a34a', textColor:'#dcfce7',
    hfPath:'bartowski/gemma-3-1b-it-GGUF/gemma-3-1b-it-Q4_K_M.gguf',
    bestFor:'Ultra-fast inference  /  on-device  /  multilingual  /  140 languages',
    desc:"Google's smallest Gemma 3. Fastest GGUF model available. Supports 140 languages.",
    params_preset:{temperature:0.7, max_tokens:512, n_ctx:4096},
    downloads:1400000, releasedMs: Date.parse('2025-03-12') },
  { id:'gemma2-2b',   name:'Gemma 2 2B Instruct',         family:'Gemma',   params:'2B',      sizeGb:1.6,
    quant:'Q4_K_M', tags:['fast','chat'],
    color:'#16a34a', textColor:'#dcfce7',
    hfPath:'bartowski/gemma-2-2b-it-GGUF/gemma-2-2b-it-Q4_K_M.gguf',
    bestFor:'On-device inference  /  quick chat  /  summarization',
    desc:"Google's compact model. Surprisingly good quality for its size.",
    params_preset:{temperature:0.7, max_tokens:512, n_ctx:4096},
    downloads:1100000, releasedMs: Date.parse('2024-07-01') },
  { id:'gemma2-9b',   name:'Gemma 2 9B Instruct',         family:'Gemma',   params:'9B',      sizeGb:5.8,
    quant:'Q4_K_M', tags:['chat','reasoning','multilingual'],
    color:'#16a34a', textColor:'#dcfce7',
    hfPath:'bartowski/gemma-2-9b-it-GGUF/gemma-2-9b-it-Q4_K_M.gguf',
    bestFor:'Chat  /  writing  /  multilingual  /  instruction following',
    desc:"Best-in-class 9B model. Outperforms much larger models on many benchmarks.",
    params_preset:{temperature:0.7, max_tokens:512, n_ctx:8192},
    downloads:1700000, releasedMs: Date.parse('2024-07-01') },
  { id:'gemma2-27b',  name:'Gemma 2 27B Instruct',        family:'Gemma',   params:'27B',     sizeGb:16.8,
    quant:'Q4_K_M', tags:['chat','reasoning'],
    color:'#16a34a', textColor:'#dcfce7',
    hfPath:'bartowski/gemma-2-27b-it-GGUF/gemma-2-27b-it-Q4_K_M.gguf',
    bestFor:'High-quality writing  /  deep reasoning  /  complex tasks',
    desc:"Google's largest Gemma 2. Near-GPT-4-mini quality open-weight.",
    params_preset:{temperature:0.7, max_tokens:1024, n_ctx:16384},
    downloads:620000, releasedMs: Date.parse('2024-07-01') },
  { id:'gemma3-4b',   name:'Gemma 3 4B Instruct',         family:'Gemma',   params:'4B',      sizeGb:2.5,
    quant:'Q4_K_M', tags:['fast','chat','multilingual'],
    color:'#16a34a', textColor:'#dcfce7',
    hfPath:'bartowski/gemma-3-4b-it-GGUF/gemma-3-4b-it-Q4_K_M.gguf',
    bestFor:'Multilingual chat  /  vision  /  fast inference  /  140 languages',
    desc:"Google's newest generation. Supports 140 languages with vision capability.",
    params_preset:{temperature:0.7, max_tokens:512, n_ctx:8192},
    downloads:1100000, releasedMs: Date.parse('2025-03-12') },
  { id:'gemma3-12b',  name:'Gemma 3 12B Instruct',        family:'Gemma',   params:'12B',     sizeGb:7.3,
    quant:'Q4_K_M', tags:['chat','reasoning','multilingual'],
    color:'#16a34a', textColor:'#dcfce7',
    hfPath:'bartowski/gemma-3-12b-it-GGUF/gemma-3-12b-it-Q4_K_M.gguf',
    bestFor:'High-quality multilingual  /  reasoning  /  vision tasks',
    desc:"Latest Gemma 3. Very strong multilingual benchmarks, supports images.",
    params_preset:{temperature:0.7, max_tokens:1024, n_ctx:16384},
    downloads:820000, releasedMs: Date.parse('2025-03-12') },
  { id:'gemma3-27b',  name:'Gemma 3 27B Instruct',        family:'Gemma',   params:'27B',     sizeGb:17.2,
    quant:'Q4_K_M', tags:['chat','reasoning','multilingual'],
    color:'#16a34a', textColor:'#dcfce7',
    hfPath:'bartowski/gemma-3-27b-it-GGUF/gemma-3-27b-it-Q4_K_M.gguf',
    bestFor:'High-quality reasoning  /  multilingual  /  vision  /  140 languages',
    desc:"Google's largest Gemma 3. Vision capable, 128K context. Near GPT-4o quality.",
    params_preset:{temperature:0.7, max_tokens:1024, n_ctx:32768},
    downloads:1100000, releasedMs: Date.parse('2025-03-12') },
  // == Mistral ================================================================
  { id:'mistral-7b',  name:'Mistral 7B v0.3 Instruct',   family:'Mistral', params:'7B',      sizeGb:4.4,
    quant:'Q4_K_M', tags:['chat','fast'],
    color:'#ea580c', textColor:'#ffedd5',
    hfPath:'bartowski/Mistral-7B-Instruct-v0.3-GGUF/Mistral-7B-Instruct-v0.3-Q4_K_M.gguf',
    bestFor:'Fast chat  /  text generation  /  function calling',
    desc:"The model that started the open-weights revolution. Still excellent.",
    params_preset:{temperature:0.7, max_tokens:512, n_ctx:8192},
    downloads:3200000, releasedMs: Date.parse('2024-05-01') },
  { id:'mixtral-8x7b', name:'Mixtral 8x7B Instruct',     family:'Mistral', params:'47B MoE', sizeGb:26.9,
    quant:'Q4_K_M', tags:['chat','reasoning','multilingual'],
    color:'#ea580c', textColor:'#ffedd5',
    hfPath:'bartowski/Mixtral-8x7B-Instruct-v0.1-GGUF/Mixtral-8x7B-Instruct-v0.1-Q4_K_M.gguf',
    bestFor:'Multilingual  /  complex reasoning  /  long context',
    desc:"MoE: 7B active params, 47B total. Fast despite parameter count.",
    params_preset:{temperature:0.7, max_tokens:1024, n_ctx:16384},
    downloads:2400000, releasedMs: Date.parse('2024-01-01') },
  { id:'mistral-nemo', name:'Mistral Nemo 12B Instruct',  family:'Mistral', params:'12B',     sizeGb:7.3,
    quant:'Q4_K_M', tags:['chat','multilingual'],
    color:'#ea580c', textColor:'#ffedd5',
    hfPath:'bartowski/Mistral-Nemo-Instruct-2407-GGUF/Mistral-Nemo-Instruct-2407-Q4_K_M.gguf',
    bestFor:'Multilingual chat  /  long context  /  function calling',
    desc:"Mistral + NVIDIA collaboration. 128K context, 16 languages. Great value at 12B.",
    params_preset:{temperature:0.7, max_tokens:1024, n_ctx:32768},
    downloads:1800000, releasedMs: Date.parse('2024-07-18') },
  { id:'ministral-8b', name:'Ministral 8B Instruct',      family:'Mistral', params:'8B',      sizeGb:5.0,
    quant:'Q4_K_M', tags:['fast','chat'],
    color:'#ea580c', textColor:'#ffedd5',
    hfPath:'bartowski/Ministral-8B-Instruct-2410-GGUF/Ministral-8B-Instruct-2410-Q4_K_M.gguf',
    bestFor:'Fast edge inference  /  chat  /  function calling',
    desc:"Compact Mistral for edge deployment. Efficient 8B with strong instruction following.",
    params_preset:{temperature:0.7, max_tokens:512, n_ctx:8192},
    downloads:680000, releasedMs: Date.parse('2024-10-16') },
  { id:'mistral-small31', name:'Mistral Small 3.1 24B',  family:'Mistral', params:'24B',     sizeGb:14.5,
    quant:'Q4_K_M', tags:['chat','reasoning','multilingual','code'],
    color:'#ea580c', textColor:'#ffedd5',
    hfPath:'bartowski/Mistral-Small-3.1-24B-Instruct-2503-GGUF/Mistral-Small-3.1-24B-Instruct-2503-Q4_K_M.gguf',
    bestFor:'Best open 24B  /  vision  /  128K context  /  multilingual',
    desc:"Mistral's March 2025 flagship. Vision capable, 128K context. Rivals Claude Haiku.",
    params_preset:{temperature:0.7, max_tokens:1024, n_ctx:32768},
    downloads:2200000, releasedMs: Date.parse('2025-03-17') },
  // == Qwen (Alibaba) =========================================================
  { id:'qwen25-7b',   name:'Qwen 2.5 7B Instruct',        family:'Qwen',    params:'7B',      sizeGb:4.7,
    quant:'Q4_K_M', tags:['chat','multilingual','code'],
    color:'#0d9488', textColor:'#ccfbf1',
    hfPath:'bartowski/Qwen2.5-7B-Instruct-GGUF/Qwen2.5-7B-Instruct-Q4_K_M.gguf',
    bestFor:'Multilingual chat  /  coding  /  structured data',
    desc:"Alibaba's strong open model. Excellent multilingual support across 29 languages.",
    params_preset:{temperature:0.7, max_tokens:512, n_ctx:8192},
    downloads:1900000, releasedMs: Date.parse('2024-09-01') },
  { id:'qwen25-14b',  name:'Qwen 2.5 14B Instruct',        family:'Qwen',    params:'14B',     sizeGb:9.0,
    quant:'Q4_K_M', tags:['chat','reasoning','multilingual'],
    color:'#0d9488', textColor:'#ccfbf1',
    hfPath:'bartowski/Qwen2.5-14B-Instruct-GGUF/Qwen2.5-14B-Instruct-Q4_K_M.gguf',
    bestFor:'Advanced multilingual  /  reasoning  /  analysis',
    desc:"Best open 14B model. Beats many larger models on Asian language tasks.",
    params_preset:{temperature:0.7, max_tokens:1024, n_ctx:16384},
    downloads:1100000, releasedMs: Date.parse('2024-09-01') },
  { id:'qwen25-32b',  name:'Qwen 2.5 32B Instruct',        family:'Qwen',    params:'32B',     sizeGb:19.8,
    quant:'Q4_K_M', tags:['chat','reasoning','multilingual'],
    color:'#0d9488', textColor:'#ccfbf1',
    hfPath:'bartowski/Qwen2.5-32B-Instruct-GGUF/Qwen2.5-32B-Instruct-Q4_K_M.gguf',
    bestFor:'Research  /  complex analysis  /  multilingual  /  long docs',
    desc:"Alibaba's 32B sweet spot. Exceptional on Chinese and English. Strong all-round reasoning.",
    params_preset:{temperature:0.7, max_tokens:1024, n_ctx:32768},
    downloads:1500000, releasedMs: Date.parse('2024-09-18') },
  { id:'qwen25-72b',  name:'Qwen 2.5 72B Instruct',        family:'Qwen',    params:'72B',     sizeGb:44.0,
    quant:'Q4_K_M', tags:['chat','reasoning','multilingual','code'],
    color:'#0d9488', textColor:'#ccfbf1',
    hfPath:'bartowski/Qwen2.5-72B-Instruct-GGUF/Qwen2.5-72B-Instruct-Q4_K_M.gguf',
    bestFor:'SOTA open 72B  /  multilingual  /  complex coding  /  analysis',
    desc:"Alibaba's largest open model. Beats many closed models. Top choice for quality tasks.",
    params_preset:{temperature:0.7, max_tokens:1024, n_ctx:32768},
    downloads:2100000, releasedMs: Date.parse('2024-09-18') },
  { id:'qwq-32b',     name:'QwQ 32B Preview',               family:'Qwen',    params:'32B',     sizeGb:19.8,
    quant:'Q4_K_M', tags:['reasoning'],
    color:'#0d9488', textColor:'#ccfbf1',
    hfPath:'bartowski/QwQ-32B-GGUF/QwQ-32B-Q4_K_M.gguf',
    bestFor:'Math  /  science  /  step-by-step reasoning  /  hard problems',
    desc:"Qwen's o1-like thinker. Ponders before answering. Exceptional for hard science and math.",
    params_preset:{temperature:0.0, max_tokens:2048, n_ctx:32768},
    downloads:2900000, releasedMs: Date.parse('2024-11-27') },
  { id:'qwen25-coder', name:'Qwen 2.5 Coder 7B Instruct',  family:'Qwen',    params:'7B',      sizeGb:4.7,
    quant:'Q4_K_M', tags:['code'],
    color:'#0d9488', textColor:'#ccfbf1',
    hfPath:'bartowski/Qwen2.5-Coder-7B-Instruct-GGUF/Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf',
    bestFor:'Code generation  /  debugging  /  code review  /  92 languages',
    desc:"Best open-source coding model at 7B. Trained on 5.5T tokens of code.",
    params_preset:{temperature:0.1, max_tokens:1024, n_ctx:16384},
    downloads:1600000, releasedMs: Date.parse('2024-11-01') },
  { id:'qwen25-coder-32b', name:'Qwen 2.5 Coder 32B',      family:'Qwen',    params:'32B',     sizeGb:19.8,
    quant:'Q4_K_M', tags:['code'],
    color:'#0d9488', textColor:'#ccfbf1',
    hfPath:'bartowski/Qwen2.5-Coder-32B-Instruct-GGUF/Qwen2.5-Coder-32B-Instruct-Q4_K_M.gguf',
    bestFor:'Elite code generation  /  debugging  /  code review  /  92 languages',
    desc:"The best open-source coding model in 2025. Rivals GPT-4o for pure code tasks.",
    params_preset:{temperature:0.1, max_tokens:1024, n_ctx:16384},
    downloads:2100000, releasedMs: Date.parse('2024-11-12') },
  // == DeepSeek ===============================================================
  { id:'deepseek-r1-8b', name:'DeepSeek R1 8B',            family:'DeepSeek',params:'8B',      sizeGb:4.9,
    quant:'Q4_K_M', tags:['reasoning','chat'],
    color:'#4f46e5', textColor:'#e0e7ff',
    hfPath:'bartowski/DeepSeek-R1-Distill-Llama-8B-GGUF/DeepSeek-R1-Distill-Llama-8B-Q4_K_M.gguf',
    bestFor:'Math  /  science  /  logical reasoning  /  chain-of-thought',
    desc:"DeepSeek's reasoning model. Shows its thinking. Excellent for hard problems.",
    params_preset:{temperature:0.0, max_tokens:2048, n_ctx:16384},
    downloads:2800000, releasedMs: Date.parse('2025-01-20') },
  { id:'deepseek-r1-14b', name:'DeepSeek R1 14B',          family:'DeepSeek',params:'14B',     sizeGb:9.0,
    quant:'Q4_K_M', tags:['reasoning'],
    color:'#4f46e5', textColor:'#e0e7ff',
    hfPath:'bartowski/DeepSeek-R1-Distill-Qwen-14B-GGUF/DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf',
    bestFor:'Advanced reasoning  /  complex math  /  science problems',
    desc:"Stronger than R1-8B. Approaches GPT-4o on math benchmarks.",
    params_preset:{temperature:0.0, max_tokens:2048, n_ctx:16384},
    downloads:1800000, releasedMs: Date.parse('2025-01-20') },
  { id:'deepseek-r1-32b', name:'DeepSeek R1 32B',          family:'DeepSeek',params:'32B',     sizeGb:19.8,
    quant:'Q4_K_M', tags:['reasoning'],
    color:'#4f46e5', textColor:'#e0e7ff',
    hfPath:'bartowski/DeepSeek-R1-Distill-Qwen-32B-GGUF/DeepSeek-R1-Distill-Qwen-32B-Q4_K_M.gguf',
    bestFor:'Elite reasoning  /  hard math  /  competitive programming',
    desc:"R1 32B distill. Near full R1 reasoning quality. Remarkable open-source achievement.",
    params_preset:{temperature:0.0, max_tokens:2048, n_ctx:32768},
    downloads:2400000, releasedMs: Date.parse('2025-01-20') },
  { id:'deepseek-v3',  name:'DeepSeek V3',                  family:'DeepSeek',params:'671B MoE',sizeGb:420.0,
    quant:'Q2_K', tags:['chat','reasoning','code'],
    color:'#4f46e5', textColor:'#e0e7ff',
    hfPath:'bartowski/DeepSeek-V3-GGUF/DeepSeek-V3-Q2_K.gguf',
    bestFor:'GPT-4 class  /  coding  /  Chinese  /  long context  /  needs server',
    desc:"671B MoE, 37B active. The model that shocked the AI world. Near-GPT-4o at fraction of cost.",
    params_preset:{temperature:0.7, max_tokens:1024, n_ctx:32768},
    downloads:4200000, releasedMs: Date.parse('2024-12-26') },
  // == Code / Creative / Special ==============================================
  { id:'smollm2-1.7b', name:'SmolLM2 1.7B Instruct',       family:'Other',   params:'1.7B',    sizeGb:1.1,
    quant:'Q4_K_M', tags:['fast','chat'],
    color:'#d97706', textColor:'#fef3c7',
    hfPath:'bartowski/SmolLM2-1.7B-Instruct-GGUF/SmolLM2-1.7B-Instruct-Q4_K_M.gguf',
    bestFor:'Ultra-fast  /  on-device  /  edge browsers  /  simple tasks',
    desc:"HuggingFace's tiny champion. Runs in-browser or on RPi. Fastest local option.",
    params_preset:{temperature:0.7, max_tokens:256, n_ctx:4096},
    downloads:1600000, releasedMs: Date.parse('2024-11-01') },
  { id:'codellama-7b', name:'CodeLlama 7B Instruct',         family:'Llama',   params:'7B',      sizeGb:4.5,
    quant:'Q4_K_M', tags:['code'],
    color:'#7c3aed', textColor:'#ede9fe',
    hfPath:'TheBloke/CodeLlama-7B-Instruct-GGUF/codellama-7b-instruct.Q4_K_M.gguf',
    bestFor:'Code generation  /  completion  /  debugging  /  infill',
    desc:"Meta's code-specialized model. Great for programming assistance and completion.",
    params_preset:{temperature:0.1, max_tokens:1024, n_ctx:16384},
    downloads:1400000, releasedMs: Date.parse('2023-08-01') },
  { id:'starcoder2-7b', name:'StarCoder2 7B',                family:'Other',   params:'7B',      sizeGb:4.5,
    quant:'Q4_K_M', tags:['code'],
    color:'#d97706', textColor:'#fef3c7',
    hfPath:'bartowski/starcoder2-7b-GGUF/starcoder2-7b-Q4_K_M.gguf',
    bestFor:'Code completion  /  infill  /  600+ programming languages',
    desc:"BigCode project. Trained on 3.5T tokens from GitHub & 600+ languages.",
    params_preset:{temperature:0.1, max_tokens:1024, n_ctx:16384},
    downloads:490000, releasedMs: Date.parse('2024-02-01') },
  { id:'dolphin-7b',  name:'Dolphin 2.9 Mistral 7B',         family:'Mistral', params:'7B',      sizeGb:4.4,
    quant:'Q4_K_M', tags:['chat','fast'],
    color:'#ea580c', textColor:'#ffedd5',
    hfPath:'bartowski/dolphin-2.9.3-mistral-7B-32k-GGUF/dolphin-2.9.3-mistral-7B-32k-Q4_K_M.gguf',
    bestFor:'Creative writing  /  roleplay  /  task automation  /  32K context',
    desc:"Fine-tuned for helpfulness with extended 32K context window.",
    params_preset:{temperature:0.8, max_tokens:512, n_ctx:32768},
    downloads:870000, releasedMs: Date.parse('2024-05-01') },
  { id:'dolphin3-8b', name:'Dolphin 3.0 Llama 3.1 8B',       family:'Llama',   params:'8B',      sizeGb:4.9,
    quant:'Q4_K_M', tags:['chat','fast'],
    color:'#7c3aed', textColor:'#ede9fe',
    hfPath:'bartowski/dolphin3.0-llama3.1-8b-GGUF/dolphin3.0-llama3.1-8b-Q4_K_M.gguf',
    bestFor:'Creative writing  /  roleplay  /  assistant  /  no-filter tasks',
    desc:"Eric Hartford's Dolphin 3.0 fine-tune on Llama 3.1. Helpful, creative, uncensored.",
    params_preset:{temperature:0.8, max_tokens:512, n_ctx:8192},
    downloads:920000, releasedMs: Date.parse('2025-01-15') },
  { id:'command-r-7b', name:'Command R7B',                   family:'Other',   params:'7B',      sizeGb:4.7,
    quant:'Q4_K_M', tags:['chat','reasoning'],
    color:'#d97706', textColor:'#fef3c7',
    hfPath:'bartowski/c4ai-command-r7b-12-2024-GGUF/c4ai-command-r7b-12-2024-Q4_K_M.gguf',
    bestFor:'RAG  /  tool use  /  structured tasks  /  agentic workflows',
    desc:"Cohere's compact Command R. Optimized for retrieval-augmented generation and tool calling.",
    params_preset:{temperature:0.7, max_tokens:1024, n_ctx:16384},
    downloads:580000, releasedMs: Date.parse('2024-12-20') },
  { id:'aya-expanse-8b', name:'Aya Expanse 8B',              family:'Other',   params:'8B',      sizeGb:5.0,
    quant:'Q4_K_M', tags:['chat','multilingual'],
    color:'#d97706', textColor:'#fef3c7',
    hfPath:'bartowski/aya-expanse-8b-GGUF/aya-expanse-8b-Q4_K_M.gguf',
    bestFor:'23 languages  /  low-resource languages  /  multilingual NLP',
    desc:"Cohere For AI's multilingual champion. Best open-source model for non-English languages.",
    params_preset:{temperature:0.7, max_tokens:512, n_ctx:8192},
    downloads:460000, releasedMs: Date.parse('2024-10-08') },
  { id:'falcon3-10b',  name:'Falcon3 10B Instruct',          family:'Other',   params:'10B',     sizeGb:6.0,
    quant:'Q4_K_M', tags:['chat','reasoning'],
    color:'#d97706', textColor:'#fef3c7',
    hfPath:'bartowski/Falcon3-10B-Instruct-GGUF/Falcon3-10B-Instruct-Q4_K_M.gguf',
    bestFor:'Complex reasoning  /  strong math  /  efficient inference',
    desc:"TII's Falcon3. Trained with novel depth-upscaling. Punches above its weight on benchmarks.",
    params_preset:{temperature:0.7, max_tokens:512, n_ctx:8192},
    downloads:410000, releasedMs: Date.parse('2024-12-02') },
];"""

# ── New card footer stats (to replace the old muted-grey spans) ──
OLD_FOOTER = r"""  <div style="display:flex;align-items:center;justify-content:space-between;margin-top:8px;padding-top:6px;border-top:1px solid ${isDark?'#1e293b':'#e2e8f0'};">
    <div style="display:flex;gap:10px;align-items:center;">
      <span style="font-size:10px;color:${isDark?'#64748b':'#94a3b8'};" title="Approximate HuggingFace downloads">⬇ ${_fmtDl(m.downloads)}</span>
      <span style="font-size:10px;color:${isDark?'#64748b':'#94a3b8'};">🕐 ${_age(m.releasedMs)}</span>
    </div>
    <div style="display:inline-flex;align-items:center;padding:2px 9px;border-radius:999px;background:${suit.bg};" title="${suit.tip}">
      <span style="font-size:10px;font-weight:700;color:${suit.color};">${suit.label}</span>
    </div>
  </div>
</div>`;"""

NEW_FOOTER = r"""  <div style="display:flex;align-items:center;justify-content:space-between;margin-top:9px;padding-top:7px;border-top:1px solid ${isDark?'#1e293b':'#e2e8f0'};">
    <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;">
      <span style="display:inline-flex;align-items:center;gap:3px;padding:3px 8px;border-radius:999px;background:${isDark?'#1e3a5f55':'#dbeafe88'};" title="HuggingFace downloads">
        <svg style="width:11px;height:11px;flex-shrink:0;" viewBox="0 0 16 16" fill="none"><path d="M8 2v8m0 0L5 7m3 3 3-3M3 13h10" stroke="#2563eb" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
        <span style="font-size:12px;font-weight:800;color:#2563eb;">${_fmtDl(m.downloads)}</span>
      </span>
      <span style="display:inline-flex;align-items:center;gap:3px;padding:3px 8px;border-radius:999px;background:${_ageColor(m.releasedMs,isDark).bg};" title="Released ${new Date(m.releasedMs).toLocaleDateString('en-US',{month:'short',year:'numeric'})}">
        <svg style="width:10px;height:10px;flex-shrink:0;" viewBox="0 0 16 16" fill="none"><rect x="2" y="3" width="12" height="11" rx="2" stroke="${_ageColor(m.releasedMs,isDark).fg}" stroke-width="1.7"/><path d="M2 7h12M5 1v3m6-3v3" stroke="${_ageColor(m.releasedMs,isDark).fg}" stroke-width="1.7" stroke-linecap="round"/></svg>
        <span style="font-size:12px;font-weight:800;color:${_ageColor(m.releasedMs,isDark).fg};">${_age(m.releasedMs)}</span>
      </span>
    </div>
    <span style="display:inline-flex;align-items:center;padding:3px 10px;border-radius:999px;background:${suit.bg};font-size:11px;font-weight:800;color:${suit.color};white-space:nowrap;" title="${suit.tip}">${suit.label}</span>
  </div>
</div>`;"""

# ─── read ───────────────────────────────────────────────────────────────────
with open(HTML, encoding="utf-8") as f:
    src = f.read()

original_len = len(src.splitlines())

# ─── replace catalog ────────────────────────────────────────────────────────
# Find from "const _MODEL_CATALOG = [" to the matching "];"
cat_start = src.find("const _MODEL_CATALOG = [")
if cat_start == -1:
    print("ERROR: could not find const _MODEL_CATALOG")
    sys.exit(1)  # noqa: E702

# Walk forward to find the closing "];\"" on its own line
search_from = cat_start + len("const _MODEL_CATALOG = [")
# Find "];" that appears on a line by itself after the catalog start
cat_end_rel = src.find("\n];", search_from)
if cat_end_rel == -1:
    print("ERROR: could not find closing ];")
    sys.exit(1)  # noqa: E702
cat_end = cat_end_rel + len("\n];")  # include the ];

src = src[:cat_start] + NEW_CATALOG + src[cat_end:]
print(f"Catalog replaced. Lines before: {original_len}, after: {len(src.splitlines())}")

# ─── replace card footer ────────────────────────────────────────────────────
idx = src.find(OLD_FOOTER)
if idx == -1:
    # Try a shorter probe — the first unique line
    probe = "      <span style=\"font-size:10px;color:${isDark?'#64748b':'#94a3b8'};\" title=\"Approximate HuggingFace downloads\">"
    idx2 = src.find(probe)
    if idx2 != -1:
        print(f"Found footer probe at char {idx2} — will do partial replace")
        # find the full `  <div ...` block surrounding it
        block_start = src.rfind(
            '  <div style="display:flex;align-items:center;justify-content:space-between;margin-top:8px',
            0,
            idx2,
        )
        block_end = src.find("\n</div>`;", idx2)
        if block_start != -1 and block_end != -1:
            block_end_full = block_end + len("\n</div>`;")
            old_block = src[block_start:block_end_full]
            print("Old footer block (repr):\n", repr(old_block[:200]))
            src = src[:block_start] + NEW_FOOTER + src[block_end_full:]
            print("Card footer replaced via probe.")
        else:
            print("WARNING: could not find footer block boundaries via probe")
    else:
        print("WARNING: old footer not found (may already be updated)")
else:
    src = src[:idx] + NEW_FOOTER + src[idx + len(OLD_FOOTER) :]
    print("Card footer replaced.")

# ─── write ──────────────────────────────────────────────────────────────────
with open(HTML, "w", encoding="utf-8") as f:
    f.write(src)
print(f"Done. File is now {len(src.splitlines())} lines.")
