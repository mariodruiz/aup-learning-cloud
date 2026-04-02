# Large Language Model from Scratch

Ever wondered what actually happens inside ChatGPT? This toolkit takes you on a ground-up journey through every building block of a modern Large Language Model. Across 14 progressive labs you will go from tensors and gradients all the way to a fully working LLaMA-style decoder, implementing and understanding every component along the way on AMD GPUs.

:::{admonition} Goals
:class: tip
- Master PyTorch fundamentals: tensors, autograd, and training loops
- Implement core transformer components (tokenisation, positional encoding, attention, normalisation, FFN) from scratch
- Explore efficiency techniques including FlashAttention, Mixture of Experts, quantisation, and LoRA
- Build a complete data processing and training pipeline for language models
- Understand inference optimisation with KV-Cache, sparse attention, and PagedAttention
- Assemble a full LLaMA-style transformer from scratch and train it end to end
:::

## Foundations (LLM01 to LLM03)

::::{note} What this section covers
LLM inference, forward propagation (tensors, linear layers, activations), and backpropagation (autograd, computation graphs, training loops). These labs establish the PyTorch fundamentals needed for everything that follows.
::::

### LLM01 - LLM Introduction and Inference

Load pre-trained LLaMA and GPT-2 models, tokenise text, and run autoregressive text generation. This lab sets up the environment, introduces HuggingFace model loading, and lets you experiment with generation parameters like temperature and sampling strategies.

### LLM02 - Forward Propagation

Explore tensor operations and linear layers, the forward-pass building blocks of every neural network. You will work through tensor creation, shapes, device placement, matrix multiplication variants, `nn.Linear`, element-wise operations, `einsum`, and activation functions (ReLU, GELU, SiLU).

### LLM03 - Backpropagation and Autograd

Understand the backward pass and how gradients are computed. The lab covers the chain rule, dynamic computation graphs, manual gradient verification against autograd, gradient hooks for inspection, gradient accumulation, and a complete training loop from scratch.

## Transformer Components (LLM04 to LLM06)

::::{note} What this section covers
The core building blocks inside a Transformer block: tokenisation and positional encoding, normalisation and feed-forward networks, and attention mechanisms. After these labs you will understand every component that makes up a modern LLM.
::::

### LLM04 - Tokenisation, Input Embedding and Positional Encoding

Convert raw text into position-aware numerical representations. The lab covers HuggingFace tokenisers (encode, decode, batch), `nn.Embedding` lookup, sinusoidal positional encoding, and Rotary Position Embedding (RoPE) with distance-decay verification.

### LLM05 - Normalisation and FFN

Implement Layer Normalisation and RMS Normalisation from scratch and compare their effect on gradient flow and training stability. The lab also covers Pre-LN vs. Post-LN transformer architectures and builds a SwiGLU feed-forward network, the design used in LLaMA.

### LLM06 - Attention Mechanisms

Implement the core innovation behind transformers from mathematical foundations to working code. Build Q/K/V projections, scaled dot-product attention, causal masking, padding masking, Multi-Head Attention (MHA), and Grouped Query Attention (GQA), mapping each to LLaMA, Mistral, and GPT architectures.

## Efficiency and Adaptation (LLM07 to LLM09)

::::{note} What this section covers
FlashAttention, Mixture of Experts, numerical precision, and LoRA. These labs cover the key techniques that make LLMs practical at scale.
::::

### LLM07 - FlashAttention

Dive into GPU-efficient attention via memory hierarchy optimisation. The lab explains registers, SRAM, L2 cache, and HBM, then walks through tiled matrix multiplication, online softmax (numerically stable incremental computation), and FlashAttention V1 and V2 IO complexity analysis with benchmarks.

### LLM08 - Mixture of Experts and Numerical Precision

Explore two pillars of efficient LLM scaling. Build a Mixture of Experts layer with Top-K gating and load balancing from scratch, then study floating-point formats (FP32, FP16, BF16, FP8) and INT8/INT4 quantisation and their impact on model accuracy.

### LLM09 - LoRA Fine-Tuning

Master Low-Rank Adaptation (LoRA), the parameter-efficient fine-tuning technique that adapts billion-parameter models by training only a tiny fraction of weights. Implement `LoRALayer` and `LinearWithLoRA` from scratch, analyse rank/alpha selection trade-offs, and verify gradient flow through the adapted layers.

## Training and Data (LLM10 to LLM11)

::::{note} What this section covers
The complete data pipeline and training workflow for language models, from raw text preprocessing to a full training loop with mixed-precision and evaluation.
::::

### LLM10 - Data Processing and Model Packaging

Build the data pipeline for LLM training: tokeniser fundamentals (padding, truncation, batching), HuggingFace Datasets (load, filter, map), instruction-tuning data preprocessing with the Alpaca dataset, and model serialisation with `state_dict`, `safetensors`, and `from_pretrained`/`save_pretrained`.

### LLM11 - Model Training Pipeline

Assemble the complete end-to-end training workflow. The lab covers collate functions, autoregressive cross-entropy loss with label shifting and prompt masking, AdamW with weight decay groups, learning rate scheduling (warmup + decay), gradient accumulation, mixed-precision (AMP), evaluation with perplexity, and HuggingFace Trainer integration.

## Inference and Serving (LLM12 to LLM13)

::::{note} What this section covers
Decoding strategies, KV-Cache optimisation, sparse attention patterns, and PagedAttention for efficient generation and high-throughput serving.
::::

### LLM12 - Inference and KV-Cache

Optimise LLM inference by understanding the two-stage pipeline (Prefill vs. Decode) and implementing decoding strategies (greedy, temperature, top-k, top-p) with repetition penalties from scratch. Build a KV-Cache that stores projected K/V tensors across steps, then benchmark the speedup compared to recomputation.

### LLM13 - Sparse Attention and PagedAttention

Tackle the KV-Cache memory bottleneck for long sequences. The lab covers sliding window attention, attention sinks (StreamingLLM), dynamic sparse patterns (MInference, Quest), and PagedAttention for block-based KV memory management in serving scenarios.

## Capstone (LLM14)

::::{note} What this section covers
Everything comes together. Build a complete, self-contained LLaMA-style model from scratch.
::::

### LLM14 - Build a Tiny LLaMA from Scratch

Put all the pieces together and assemble a fully functional LLaMA-style decoder-only transformer: RMSNorm, RoPE, Multi-Head Attention with causal and padding masks via PyTorch SDPA, SwiGLU MLP, residual connections, and weight tying between embedding and LM head. Train it on a toy corpus with a byte-level tokeniser and generate text, all without the `transformers` library.

::::{seealso}
Explore the other learning toolkits: [Computer Vision](computer-vision.md), [Deep Learning](deep-learning.md), [Physics Simulation](physics-simulation.md).
::::
